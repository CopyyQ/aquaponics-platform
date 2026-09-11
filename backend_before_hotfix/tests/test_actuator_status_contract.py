import json
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import pytest
from sqlalchemy import delete, select

from app.db.session import AsyncSessionLocal
from app.models.actuator import Actuator, ActuatorReading, ActuatorStateHistory
from app.models.actuator_model import ActuatorModel
from app.models.device import Device
from app.models.project import Project
from app.mqtt.handlers import handle_status
from app.services.actuator_identity_service import (
    generate_actuator_identity,
    validate_local_actuator_code,
)
from app.services.monitoring_service import get_project_monitoring_latest
from app.services.mqtt_connection_config_service import build_mqtt_connection_config


@pytest.mark.asyncio
async def test_generated_actuator_identity_is_local_to_device() -> None:
    class FakeDb:
        bind = None

        async def scalar(self, _statement):
            return 1

    identity = await generate_actuator_identity(
        FakeDb(),
        project=SimpleNamespace(id=81, code="TB-0015"),
        device=SimpleNamespace(id=86, code="TB-0015-MT-3022-01"),
        actuator_model=SimpleNamespace(id=4, code="IRRIGATION_PUMP", name="Bơm tưới"),
    )

    assert identity.code == "IRRIGATION_PUMP-02"
    assert "TB-0015-TB-0015" not in identity.code


def test_device_qualified_actuator_code_is_rejected_at_creation_source() -> None:
    with pytest.raises(ValueError, match="device-local"):
        validate_local_actuator_code(
            "TB-0015-TB-0015-MT-3022-01-IRRIGATION_PUMP-02",
            project_code="TB-0015",
            device_code="TB-0015-MT-3022-01",
        )

    assert validate_local_actuator_code(
        "IRRIGATION_PUMP-02",
        project_code="TB-0015",
        device_code="TB-0015-MT-3022-01",
    ) == "IRRIGATION_PUMP-02"


@pytest.mark.asyncio
async def test_mqtt_status_contract_and_monitoring_use_canonical_actuator_fields(monkeypatch) -> None:
    async def ignore_alert_evaluation(*_args, **_kwargs) -> None:
        return None

    monkeypatch.setattr(
        "app.mqtt.handlers.evaluate_alert_scenarios_for_actuator",
        ignore_alert_evaluation,
    )
    recorded_at = datetime.now(UTC) - timedelta(seconds=2)
    last_reported_at = recorded_at + timedelta(milliseconds=500)
    db_updated_at = recorded_at + timedelta(seconds=1)
    actuator_id = None

    async with AsyncSessionLocal() as db:
        project = await db.scalar(select(Project).where(Project.code == "CODEX-TEST-RUNTIME"))
        device = await db.scalar(select(Device).where(Device.code == "CODEX-TEST-DEVICE"))
        model = await db.scalar(select(ActuatorModel).where(ActuatorModel.is_active.is_(True)))
        assert project and device and model
        device.device_type = "CONTROLLER"
        actuator = Actuator(
            device_id=device.id,
            actuator_model_id=model.id,
            sequence_number=902,
            code="IRRIGATION_PUMP-02",
            name="Bơm tưới regression",
            desired_state=False,
            reported_state=False,
            last_reported_at=last_reported_at,
            updated_at=db_updated_at,
        )
        db.add(actuator)
        await db.commit()
        await db.refresh(actuator)
        actuator_id = actuator.id

        config, _, _ = await build_mqtt_connection_config(
            db, project_id=project.id, device_id=device.id
        )
        status_actuator = next(
            item
            for item in config["payload_contracts"]["status"]["payload"]["actuators"]
            if item["actuator_code"] == "IRRIGATION_PUMP-02"
        )
        assert set(status_actuator) == {
            "actuator_code",
            "state",
            "voltage_v",
            "current_a",
            "recorded_at",
        }
        assert isinstance(status_actuator["voltage_v"], float)
        assert isinstance(status_actuator["current_a"], float)

        latest = await get_project_monitoring_latest(db, project.id)
        monitored = next(
            item
            for item in latest["devices"][0]["actuators"]
            if item["code"] == "IRRIGATION_PUMP-02"
        )
        assert monitored["last_db_updated_at"] == actuator.updated_at
        assert monitored["last_db_updated_at"] != monitored["last_reported_at"]

    sent_at = datetime.now(UTC)
    await handle_status(
        "CODEX-TEST-DEVICE",
        json.dumps(
            {
                "status": "ONLINE",
                "sent_at": sent_at.isoformat(),
                "actuators": [
                    {
                        "actuator_code": "IRRIGATION_PUMP-02",
                        "state": True,
                        "voltage_v": 12.41,
                        "current_a": 1.65,
                        "recorded_at": recorded_at.isoformat(),
                    }
                ],
            }
        ).encode(),
    )

    async with AsyncSessionLocal() as db:
        actuator = await db.get(Actuator, actuator_id)
        reading = await db.scalar(
            select(ActuatorReading)
            .where(ActuatorReading.actuator_id == actuator_id)
            .order_by(ActuatorReading.id.desc())
        )
        assert actuator is not None
        assert actuator.code == "IRRIGATION_PUMP-02"
        assert actuator.voltage_v == 12.41
        assert actuator.current_a == 1.65
        assert reading is not None
        assert reading.actuator_id == actuator_id
        assert reading.voltage_v == 12.41
        assert reading.current_a == 1.65
        assert reading.recorded_at == recorded_at

        await db.execute(delete(ActuatorReading).where(ActuatorReading.actuator_id == actuator_id))
        await db.execute(delete(ActuatorStateHistory).where(ActuatorStateHistory.actuator_id == actuator_id))
        await db.execute(delete(Actuator).where(Actuator.id == actuator_id))
        await db.commit()
