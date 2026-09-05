from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import delete, func, select
from test_visibility_authorization import visibility_data  # noqa: F401

from app.core.enums import AlertType
from app.db.session import AsyncSessionLocal
from app.models.alert import SensorAlert
from app.models.device import Device
from app.models.sensor import Sensor
from app.models.telemetry import TelemetryReading
from app.schemas.telemetry import DeviceTelemetryInput
from app.services.telemetry_service import ingest_telemetry


def telemetry_payload(sensor_code: str, values: list[float], started_at: datetime) -> DeviceTelemetryInput:
    return DeviceTelemetryInput.model_validate(
        {
            "sent_at": started_at + timedelta(seconds=len(values)),
            "readings": [
                {
                    "sensor_code": sensor_code,
                    "value": value,
                    "recorded_at": started_at + timedelta(seconds=index),
                }
                for index, value in enumerate(values)
            ],
        }
    )


@pytest.mark.asyncio
@pytest.mark.parametrize("values", [[8.6, 8.7, 8.8, 8.9], [8.9, 8.8, 8.7]])
async def test_each_distinct_abnormal_reading_notifies_once_and_updates_one_incident(
    visibility_data, monkeypatch, values
) -> None:
    data = visibility_data
    events: list[dict] = []

    async def capture_dispatch(_db, **event) -> None:
        events.append(event)

    monkeypatch.setattr(
        "app.services.telemetry_service.dispatch_alert_transition", capture_dispatch
    )
    async with AsyncSessionLocal() as db:
        sensor = await db.get(Sensor, data["active_sensor"])
        device = await db.get(Device, sensor.device_id)
        assert sensor is not None and device is not None
        original = (
            sensor.warning_enabled,
            sensor.lower_threshold,
            sensor.upper_threshold,
            sensor.alert_delay_seconds,
        )
        sensor.warning_enabled = True
        sensor.lower_threshold = 6.0
        sensor.upper_threshold = 8.5
        sensor.alert_delay_seconds = 0
        started_at = datetime.now(UTC) - timedelta(minutes=1)
        payload = telemetry_payload(sensor.code, values, started_at)

        response = await ingest_telemetry(
            db, device=device, payload=payload, received_at=datetime.now(UTC)
        )
        assert response.accepted == len(values)
        assert [event["observed_value"] for event in events] == values
        assert [event["occurrence_count"] for event in events] == list(
            range(1, len(values) + 1)
        )

        duplicate = await ingest_telemetry(
            db, device=device, payload=payload, received_at=datetime.now(UTC)
        )
        assert duplicate.duplicates == len(values)
        assert len(events) == len(values)

        alerts = list(
            (
                await db.scalars(
                    select(SensorAlert).where(
                        SensorAlert.sensor_id == sensor.id,
                        SensorAlert.alert_type == AlertType.ABOVE_UPPER_THRESHOLD,
                    )
                )
            ).all()
        )
        assert len(alerts) == 1
        assert alerts[0].occurrence_count == len(values)
        assert alerts[0].trigger_value == values[-1]
        assert alerts[0].last_triggered_at == started_at + timedelta(seconds=len(values) - 1)

        await db.execute(
            delete(TelemetryReading).where(
                TelemetryReading.sensor_id == sensor.id,
                TelemetryReading.recorded_at >= started_at,
                TelemetryReading.recorded_at <= started_at + timedelta(seconds=len(values) - 1),
            )
        )
        await db.execute(delete(SensorAlert).where(SensorAlert.sensor_id == sensor.id))
        (
            sensor.warning_enabled,
            sensor.lower_threshold,
            sensor.upper_threshold,
            sensor.alert_delay_seconds,
        ) = original
        await db.commit()


@pytest.mark.asyncio
async def test_normalization_does_not_notify_or_end_incident_then_abnormal_reuses_it(
    visibility_data, monkeypatch
) -> None:
    data = visibility_data
    events: list[dict] = []

    async def capture_dispatch(_db, **event) -> None:
        events.append(event)

    monkeypatch.setattr(
        "app.services.telemetry_service.dispatch_alert_transition", capture_dispatch
    )
    async with AsyncSessionLocal() as db:
        sensor = await db.get(Sensor, data["active_sensor"])
        device = await db.get(Device, sensor.device_id)
        assert sensor is not None and device is not None
        original = (
            sensor.warning_enabled,
            sensor.lower_threshold,
            sensor.upper_threshold,
            sensor.alert_delay_seconds,
        )
        sensor.warning_enabled = True
        sensor.lower_threshold = 6.0
        sensor.upper_threshold = 8.5
        sensor.alert_delay_seconds = 0
        started_at = datetime.now(UTC) - timedelta(minutes=1)

        await ingest_telemetry(
            db,
            device=device,
            payload=telemetry_payload(sensor.code, [8.6, 8.7, 8.3], started_at),
            received_at=datetime.now(UTC),
        )
        assert [event["observed_value"] for event in events] == [8.6, 8.7]
        assert [event["occurrence_count"] for event in events] == [1, 2]
        assert await db.scalar(
            select(func.count(SensorAlert.id)).where(
                SensorAlert.sensor_id == sensor.id,
                SensorAlert.alert_type == AlertType.ABOVE_UPPER_THRESHOLD,
            )
        ) == 1
        alert = await db.scalar(
            select(SensorAlert).where(
                SensorAlert.sensor_id == sensor.id,
                SensorAlert.alert_type == AlertType.ABOVE_UPPER_THRESHOLD,
            )
        )
        assert alert is not None
        assert alert.condition_active is False
        assert alert.resolved_at is None
        assert alert.occurrence_count == 2

        await ingest_telemetry(
            db,
            device=device,
            payload=telemetry_payload(sensor.code, [8.8], started_at + timedelta(seconds=3)),
            received_at=datetime.now(UTC),
        )
        assert [event["observed_value"] for event in events] == [8.6, 8.7, 8.8]
        assert [event["occurrence_count"] for event in events] == [1, 2, 3]
        await db.refresh(alert)
        assert alert.condition_active is True
        assert alert.occurrence_count == 3

        await db.execute(
            delete(TelemetryReading).where(
                TelemetryReading.sensor_id == sensor.id,
                TelemetryReading.recorded_at >= started_at,
                TelemetryReading.recorded_at <= started_at + timedelta(seconds=3),
            )
        )
        await db.execute(delete(SensorAlert).where(SensorAlert.sensor_id == sensor.id))
        (
            sensor.warning_enabled,
            sensor.lower_threshold,
            sensor.upper_threshold,
            sensor.alert_delay_seconds,
        ) = original
        await db.commit()
