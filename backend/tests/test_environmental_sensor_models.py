from collections.abc import Mapping
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import httpx
import pytest
from sqlalchemy import delete, func, select

from app.core.config import settings
from app.core.security import create_access_token
from app.db.session import AsyncSessionLocal, engine
from app.main import app
from app.models.device import Device
from app.models.device_template import DeviceTemplateSensor
from app.models.sensor import Sensor, SensorModel
from app.models.telemetry import TelemetryReading
from app.models.user import User
from app.schemas.telemetry import DeviceTelemetryInput
from app.services.sensor_value_validation import validate_sensor_value
from app.services.telemetry_service import ingest_telemetry
from scripts.seed import (
    ENVIRONMENTAL_SENSOR_MODEL_CODES,
    SENSOR_MODELS,
    seed_sensor_models,
)

EXPECTED_MODELS: Mapping[str, tuple[str, str]] = {
    "AIR_HUMIDITY": ("Cảm biến độ ẩm môi trường", "%RH"),
    "AIR_TEMPERATURE": ("Cảm biến nhiệt độ môi trường", "°C"),
    "AIR_PRESSURE": ("Cảm biến áp suất không khí", "hPa"),
    "ILLUMINANCE": ("Cảm biến ánh sáng", "lux"),
}


def test_environmental_sensor_seed_contract() -> None:
    configured = {
        str(item["code"]): item
        for item in SENSOR_MODELS
        if item["code"] in ENVIRONMENTAL_SENSOR_MODEL_CODES
    }

    assert set(configured) == set(EXPECTED_MODELS)
    for code, (name, unit) in EXPECTED_MODELS.items():
        item = configured[code]
        assert item["name"] == name
        assert item["unit"] == unit
        assert item["value_type"] == "NUMBER"
        assert item["chart_type"] == "LINE"
        assert item["default_lower_threshold"] is None
        assert item["default_upper_threshold"] is None


async def test_environmental_sensor_seed_is_idempotent_and_catalog_only() -> None:
    async with AsyncSessionLocal() as db:
        sensor_count_before = await db.scalar(select(func.count(Sensor.id)))
        mapping_count_before = await db.scalar(select(func.count(DeviceTemplateSensor.id)))

        await seed_sensor_models(db)
        await seed_sensor_models(db)

        rows = list(
            (
                await db.scalars(
                    select(SensorModel).where(
                        SensorModel.code.in_(ENVIRONMENTAL_SENSOR_MODEL_CODES)
                    )
                )
            ).all()
        )
        sensor_count_after = await db.scalar(select(func.count(Sensor.id)))
        mapping_count_after = await db.scalar(select(func.count(DeviceTemplateSensor.id)))
        actual_models = {
            row.code: {
                "name": row.name,
                "unit": row.unit,
                "value_type": row.value_type,
                "is_active": row.is_active,
                "default_lower_threshold": row.default_lower_threshold,
                "default_upper_threshold": row.default_upper_threshold,
            }
            for row in rows
        }
        await db.rollback()
    await engine.dispose()

    assert len(rows) == 4
    assert len(actual_models) == 4
    assert sensor_count_after == sensor_count_before
    assert mapping_count_after == mapping_count_before
    for code, item in actual_models.items():
        expected_name, expected_unit = EXPECTED_MODELS[code]
        assert item["name"] == expected_name
        assert item["unit"] == expected_unit
        assert item["value_type"] == "NUMBER"
        assert item["is_active"] is True
        assert item["default_lower_threshold"] is None
        assert item["default_upper_threshold"] is None


@pytest.mark.parametrize(
    ("model_code", "accepted_value", "rejected_value"),
    [
        ("AIR_HUMIDITY", 65.4, 100.1),
        ("AIR_TEMPERATURE", 28.5, -50.1),
        ("AIR_PRESSURE", 1_013.2, 1_200.1),
        ("ILLUMINANCE", 50_000.0, -0.1),
    ],
)
def test_environmental_sensor_technical_ranges(
    model_code: str,
    accepted_value: float,
    rejected_value: float,
) -> None:
    assert validate_sensor_value(model_code, accepted_value) is None
    assert validate_sensor_value(model_code, rejected_value) is not None


async def test_admin_catalog_api_returns_environmental_sensor_models() -> None:
    async with AsyncSessionLocal() as db:
        await seed_sensor_models(db)
        await db.commit()
        admin = await db.scalar(
            select(User).where(User.username == settings.default_admin_username)
        )
        assert admin is not None
        access_token = create_access_token(
            str(admin.id),
            extra={"token_version": admin.token_version},
        )

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(
            "/api/v1/admin/sensor-models",
            headers={"Authorization": f"Bearer {access_token}"},
        )
    await engine.dispose()

    assert response.status_code == 200
    returned = {
        item["code"]: item
        for item in response.json()
        if item["code"] in ENVIRONMENTAL_SENSOR_MODEL_CODES
    }
    assert set(returned) == set(EXPECTED_MODELS)
    for code, (name, unit) in EXPECTED_MODELS.items():
        assert returned[code]["name"] == name
        assert returned[code]["unit"] == unit
        assert returned[code]["value_type"] == "NUMBER"


async def test_sensor_instances_can_reference_each_environmental_model() -> None:
    async with AsyncSessionLocal() as db:
        await seed_sensor_models(db)
        device_id = await db.scalar(
            select(Device.id).where(Device.is_deleted.is_(False)).limit(1)
        )
        assert device_id is not None
        models = list(
            (
                await db.scalars(
                    select(SensorModel).where(
                        SensorModel.code.in_(ENVIRONMENTAL_SENSOR_MODEL_CODES)
                    )
                )
            ).all()
        )
        assert len(models) == 4

        sensors = [
            Sensor(
                device_id=device_id,
                sensor_model_id=model.id,
                code=f"TEST-{model.code}",
                name=f"Kiểm thử {model.name}",
            )
            for model in models
        ]
        db.add_all(sensors)
        await db.flush()
        assert {sensor.sensor_model_id for sensor in sensors} == {
            model.id for model in models
        }
        await db.rollback()
    await engine.dispose()


async def test_environmental_telemetry_is_ingested_and_out_of_range_is_classified() -> None:
    async with AsyncSessionLocal() as db:
        await seed_sensor_models(db)
        device = await db.scalar(
            select(Device)
            .where(Device.is_deleted.is_(False), Device.is_enabled.is_(True))
            .limit(1)
        )
        assert device is not None
        models = {
            model.code: model
            for model in (
                await db.scalars(
                    select(SensorModel).where(
                        SensorModel.code.in_({"AIR_HUMIDITY", "ILLUMINANCE"})
                    )
                )
            ).all()
        }
        assert set(models) == {"AIR_HUMIDITY", "ILLUMINANCE"}

        test_suffix = uuid4().hex[:12].upper()
        humidity = Sensor(
            device_id=device.id,
            sensor_model_id=models["AIR_HUMIDITY"].id,
            code=f"TEST-HUM-{test_suffix}",
            name="Kiểm thử độ ẩm môi trường",
        )
        illuminance = Sensor(
            device_id=device.id,
            sensor_model_id=models["ILLUMINANCE"].id,
            code=f"TEST-LUX-{test_suffix}",
            name="Kiểm thử ánh sáng",
        )
        db.add_all([humidity, illuminance])
        original_status = device.status
        original_last_seen_at = device.last_seen_at
        await db.commit()

        recorded_at = datetime.now(UTC)
        valid_response = await ingest_telemetry(
            db,
            device=device,
            payload=DeviceTelemetryInput.model_validate(
                {
                    "sent_at": recorded_at,
                    "readings": [
                        {
                            "sensor_code": humidity.code,
                            "value": 65.4,
                            "recorded_at": recorded_at,
                        },
                        {
                            "sensor_code": illuminance.code,
                            "value": 50_000.0,
                            "recorded_at": recorded_at,
                        },
                    ],
                }
            ),
            received_at=recorded_at,
        )
        invalid_response = await ingest_telemetry(
            db,
            device=device,
            payload=DeviceTelemetryInput.model_validate(
                {
                    "sent_at": recorded_at + timedelta(seconds=1),
                    "readings": [
                        {
                            "sensor_code": humidity.code,
                            "value": 100.1,
                            "recorded_at": recorded_at + timedelta(seconds=1),
                        },
                        {
                            "sensor_code": illuminance.code,
                            "value": -0.1,
                            "recorded_at": recorded_at + timedelta(seconds=1),
                        },
                    ],
                }
            ),
            received_at=recorded_at + timedelta(seconds=1),
        )

        assert valid_response.accepted == 2
        assert valid_response.rejected == 0
        # Numeric readings are persisted even when outside engineering bounds.
        # Presence/freshness is independent from measurement quality.
        assert invalid_response.accepted == 2
        assert invalid_response.rejected == 0

        out_of_range = list(
            (
                await db.scalars(
                    select(TelemetryReading).where(
                        TelemetryReading.sensor_id.in_([humidity.id, illuminance.id]),
                        TelemetryReading.recorded_at == recorded_at + timedelta(seconds=1),
                    )
                )
            ).all()
        )
        assert sorted(reading.value for reading in out_of_range) == [-0.1, 100.1]

        sensor_ids = [humidity.id, illuminance.id]
        await db.execute(
            delete(TelemetryReading).where(TelemetryReading.sensor_id.in_(sensor_ids))
        )
        await db.execute(delete(Sensor).where(Sensor.id.in_(sensor_ids)))
        device.status = original_status
        device.last_seen_at = original_last_seen_at
        await db.commit()
    await engine.dispose()
