from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.enums import AlertType, DeviceStatus, SensorStatus
from app.models.device import Device
from app.models.sensor import Sensor, SensorModel
from app.models.telemetry import TelemetryReading
from app.schemas.telemetry import (
    DeviceTelemetryInput,
    TelemetryIngestError,
    TelemetryIngestResponse,
)
from app.services.alert_service import normalize_active_alert
from app.services.measurement_quality import classify_measurement_quality
from app.services.operational_incident_service import (
    evaluate_operational_rules_for_sensor,
    evaluate_sensor_threshold_incident,
)
from app.services.project_notification_service import (
    dispatch_device_connectivity_transition,
)


async def ingest_telemetry(
    db: AsyncSession,
    *,
    device: Device,
    payload: DeviceTelemetryInput,
    received_at: datetime | None = None,
) -> TelemetryIngestResponse:
    now = received_at or datetime.now(UTC)
    if not device.is_enabled:
        return TelemetryIngestResponse(
            device_code=device.code, accepted=0, duplicates=0, rejected=len(payload.readings),
            server_time=now,
            errors=[TelemetryIngestError(sensor_code=item.sensor_code, error="Thiết bị đã tắt") for item in payload.readings],
        )
    sensor_rows = list(
        (
            await db.execute(
                select(Sensor, SensorModel)
                .join(SensorModel, SensorModel.id == Sensor.sensor_model_id)
                .where(Sensor.device_id == device.id, Sensor.is_deleted.is_(False))
            )
        ).all()
    )
    by_code = {sensor.code: (sensor, model) for sensor, model in sensor_rows}
    accepted = 0
    duplicates = 0
    errors: list[TelemetryIngestError] = []
    device_was_offline = device.status == DeviceStatus.OFFLINE
    disconnected_at = device.disconnected_at

    for reading in payload.readings:
        sensor_context = by_code.get(reading.sensor_code)
        if sensor_context is None:
            errors.append(
                TelemetryIngestError(sensor_code=reading.sensor_code, error="Không tìm thấy cảm biến")
            )
            continue
        sensor, model = sensor_context
        if not sensor.is_enabled:
            errors.append(
                TelemetryIngestError(sensor_code=reading.sensor_code, error="Cảm biến đã tắt")
            )
            continue
        if reading.recorded_at > now + timedelta(seconds=settings.mqtt_max_future_skew_seconds):
            errors.append(
                TelemetryIngestError(sensor_code=reading.sensor_code, error="recorded_at ở quá xa tương lai")
            )
            continue
        statement = (
            insert(TelemetryReading)
            .values(
                sensor_id=sensor.id,
                recorded_at=reading.recorded_at,
                received_at=now,
                value=reading.value,
            )
            .on_conflict_do_nothing(index_elements=["sensor_id", "recorded_at"])
            .returning(TelemetryReading.id)
        )
        inserted = await db.scalar(statement)
        if inserted is None:
            duplicates += 1
            continue

        accepted += 1
        sensor.status = SensorStatus.ONLINE
        sensor.last_seen_at = now
        await normalize_active_alert(db, sensor.id, AlertType.SENSOR_OFFLINE, now)
        quality = classify_measurement_quality(model.code, reading.value)[0]
        await evaluate_sensor_threshold_incident(
            db,
            device=device,
            sensor=sensor,
            sensor_model=model,
            value=reading.value,
            quality=quality,
            recorded_at=reading.recorded_at,
            received_at=now,
        )
        await evaluate_operational_rules_for_sensor(
            db,
            sensor=sensor,
            value=reading.value,
            quality=quality,
            recorded_at=reading.recorded_at,
            received_at=now,
            model_code=model.code,
        )

    if accepted + duplicates > 0:
        device.status = DeviceStatus.ONLINE
        device.last_seen_at = now
        device.disconnected_at = None
    await db.commit()
    if device_was_offline and accepted + duplicates > 0:
        await dispatch_device_connectivity_transition(
            db,
            device_id=device.id,
            transition="RECONNECTED",
            disconnected_at=disconnected_at,
            occurred_at=now,
        )
    return TelemetryIngestResponse(
        device_code=device.code,
        accepted=accepted,
        duplicates=duplicates,
        rejected=len(errors),
        server_time=now,
        errors=errors,
    )
