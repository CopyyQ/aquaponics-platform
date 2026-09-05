from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import delete, select

from app.db.session import AsyncSessionLocal, engine
from app.models.device import Device
from app.models.sensor import Sensor, SensorModel
from app.models.telemetry import TelemetryReading
from app.mqtt.schemas import MqttTelemetryPayload
from app.services.measurement_quality import classify_measurement_quality
from app.services.monitoring_service import get_project_monitoring_latest, get_project_monitoring_summary
from app.services.telemetry_ingest_service import ingest_mqtt_telemetry


async def test_mqtt_air_pressure_zero_is_fresh_out_of_range_not_missing_data() -> None:
    """A numeric zero is a received reading, never a missing-reading sentinel."""
    created: dict[str, int] = {}
    now = datetime.now(UTC)
    async with AsyncSessionLocal() as db:
        device = await db.scalar(
            select(Device).where(
                Device.is_enabled.is_(True), Device.is_deleted.is_(False)
            ).limit(1)
        )
        model = await db.scalar(
            select(SensorModel).where(
                SensorModel.code == "AIR_PRESSURE", SensorModel.is_active.is_(True)
            )
        )
        assert device is not None and model is not None
        sensor = Sensor(
            device_id=device.id,
            sensor_model_id=model.id,
            code=f"AIR-PRESSURE-ZERO-{uuid4().hex[:12].upper()}",
            name="Áp suất không khí kiểm thử zero",
            is_enabled=True,
        )
        db.add(sensor)
        await db.commit()
        created.update(sensor=sensor.id, project=device.project_id)

        result = await ingest_mqtt_telemetry(
            db,
            device_code=device.code,
            payload=MqttTelemetryPayload.model_validate(
                {
                    "sent_at": now,
                    "readings": [
                        {
                            "sensor_code": sensor.code,
                            "value": 0,
                            "recorded_at": now,
                        }
                    ],
                }
            ),
            received_at=now,
        )
        assert result is not None
        assert result.accepted == 1
        assert result.rejected == 0

        stored = await db.scalar(
            select(TelemetryReading).where(TelemetryReading.sensor_id == sensor.id)
        )
        assert stored is not None
        assert stored.value == 0
        assert stored.recorded_at == now
        assert stored.received_at == now
        assert classify_measurement_quality("AIR_PRESSURE", stored.value)[0] == "OUT_OF_RANGE"

        latest = await get_project_monitoring_latest(db, device.project_id)
        device_payload = next(item for item in latest["devices"] if item["id"] == device.id)
        detail = next(item for item in device_payload["sensors"] if item["id"] == sensor.id)
        assert detail["latest"]["value"] == 0
        assert detail["latest"]["quality"] == "OUT_OF_RANGE"
        assert detail["connection_status"] != "OFFLINE"
        assert detail["data_status"] != "WAITING_CONNECTION"

        summary = await get_project_monitoring_summary(db, device.project_id)
        assert summary["inventory"]["sensors_reporting"] >= 1

    async with AsyncSessionLocal() as db:
        await db.execute(delete(TelemetryReading).where(TelemetryReading.sensor_id == created["sensor"]))
        await db.execute(delete(Sensor).where(Sensor.id == created["sensor"]))
        await db.commit()
    await engine.dispose()
