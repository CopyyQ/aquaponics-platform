from datetime import UTC, datetime, timedelta
from uuid import uuid4

import httpx
import pytest
from sqlalchemy import delete, select

from app.core.security import create_access_token
from app.db.session import AsyncSessionLocal
from app.main import app
from app.models.actuator import Actuator
from app.models.actuator_model import ActuatorModel
from app.models.device import Device
from app.models.operational_alert import AlertRule, NotificationOutbox, OperationalIncident
from app.models.project import Project
from app.models.sensor import Sensor
from app.models.sensor_model import SensorModel
from app.models.threshold_alert_config import ThresholdAlertConfig
from app.models.user import User
from app.services.alert_evaluators import EVALUATOR_REGISTRY
from app.services.legacy_threshold_conversion import convert_legacy_threshold_configs
from app.services.operational_incident_service import evaluate_alert_scenarios_for_actuator, evaluate_operational_rules_for_sensor


def headers(user: User) -> dict[str, str]:
    token = create_access_token(str(user.id), {"role": user.system_role.value, "token_version": user.token_version})
    return {"Authorization": f"Bearer {token}"}


async def runtime():
    async with AsyncSessionLocal() as db:
        project = await db.scalar(select(Project).where(Project.code == "CODEX-TEST-RUNTIME"))
        assert project is not None
        device = await db.scalar(select(Device).where(Device.project_id == project.id))
        owner = await db.get(User, project.owner_user_id)
        admin = await db.scalar(select(User).where(User.username == "admin"))
        assert device is not None and owner is not None and admin is not None
        return project, device, owner, admin


@pytest.mark.asyncio
async def test_legacy_conversion_is_directional_strict_idempotent_and_auditable() -> None:
    project, device, _, _ = await runtime(); suffix = uuid4().hex[:8].upper()
    async with AsyncSessionLocal() as db:
        sensor_model = await db.scalar(select(SensorModel).where(SensorModel.code == "PH"))
        actuator_model = await db.scalar(select(ActuatorModel).limit(1))
        assert sensor_model is not None and actuator_model is not None
        sensor = Sensor(device_id=device.id, sensor_model_id=sensor_model.id, code=f"CONV-{suffix}", name="Conversion sensor", is_enabled=True)
        actuator = Actuator(device_id=device.id, actuator_model_id=actuator_model.id, sequence_number=991,
                            code=f"CONV-A-{suffix}", name="Conversion actuator", is_enabled=True)
        db.add_all([sensor, actuator]); await db.flush()
        sensor_config = ThresholdAlertConfig(sensor_id=sensor.id, metric_type="SENSOR_VALUE", enabled=False,
            lower_threshold=0, upper_threshold=0, below_risk_level="HIGH", above_risk_level="MEDIUM",
            below_message="below distinct", above_message="above distinct", delay_seconds=3)
        voltage_config = ThresholdAlertConfig(actuator_id=actuator.id, metric_type="VOLTAGE", enabled=True,
            lower_threshold=11, upper_threshold=None, below_risk_level="VERY_HIGH", delay_seconds=0)
        current_config = ThresholdAlertConfig(actuator_id=actuator.id, metric_type="CURRENT", enabled=True,
            lower_threshold=None, upper_threshold=0, above_risk_level="LOW_MEDIUM", delay_seconds=0)
        db.add_all([sensor_config, voltage_config, current_config]); await db.commit()
        ids = [sensor_config.id, voltage_config.id, current_config.id]
        connection = await db.connection()
        first = await connection.run_sync(convert_legacy_threshold_configs); await db.commit()
        connection = await db.connection()
        second = await connection.run_sync(convert_legacy_threshold_configs); await db.commit()
        assert first.created_scenarios == 4
        assert second.created_scenarios == 0 and second.existing_scenarios >= 4
        rows = list((await db.scalars(select(AlertRule).where(AlertRule.code.in_([
            f"LEGACY_THRESHOLD_{ids[0]}_BELOW", f"LEGACY_THRESHOLD_{ids[0]}_ABOVE",
            f"LEGACY_THRESHOLD_{ids[1]}_BELOW", f"LEGACY_THRESHOLD_{ids[2]}_ABOVE"])))) .all())
        assert len(rows) == 4
        by_code = {row.code: row for row in rows}
        below = by_code[f"LEGACY_THRESHOLD_{ids[0]}_BELOW"]
        above = by_code[f"LEGACY_THRESHOLD_{ids[0]}_ABOVE"]
        await db.refresh(below, attribute_names=["current_revision"]); await db.refresh(above, attribute_names=["current_revision"])
        assert not below.is_enabled and not above.is_enabled
        assert below.current_revision.business_risk_level == "HIGH" and below.current_revision.message_template == "below distinct"
        assert above.current_revision.business_risk_level == "MEDIUM" and above.current_revision.message_template == "above distinct"
        assert below.current_revision.condition_config["operator"] == "LT"
        assert above.current_revision.condition_config["operator"] == "GT"
        assert not EVALUATOR_REGISTRY["THRESHOLD_DURATION"].evaluate(below.current_revision.condition_config, {"value": 0, "quality": "VALID", "freshness": "FRESH"}).active
        voltage = by_code[f"LEGACY_THRESHOLD_{ids[1]}_BELOW"]
        current = by_code[f"LEGACY_THRESHOLD_{ids[2]}_ABOVE"]
        await db.refresh(voltage, attribute_names=["current_revision"]); await db.refresh(current, attribute_names=["current_revision"])
        assert voltage.current_revision.condition_config["reported_state"] is None
        assert voltage.current_revision.condition_config["voltage"] == {"operator": "LT", "value": 11.0}
        assert current.current_revision.condition_config["current"] == {"operator": "GT", "value": 0.0}
        assert EVALUATOR_REGISTRY["MULTI_CONDITION"].evaluate(voltage.current_revision.condition_config, {"reported_state": False, "voltage_v": 10, "current_a": 5}).active
        assert not EVALUATOR_REGISTRY["MULTI_CONDITION"].evaluate(voltage.current_revision.condition_config, {"reported_state": True, "voltage_v": 11, "current_a": 5}).active
        await db.execute(delete(AlertRule).where(AlertRule.code.in_(by_code))); await db.delete(sensor_config); await db.delete(voltage_config); await db.delete(current_config); await db.delete(sensor); await db.delete(actuator); await db.commit()


@pytest.mark.asyncio
async def test_scenario_crud_containment_and_sensor_actuator_lifecycle() -> None:
    project, device, owner, admin = await runtime(); suffix = uuid4().hex[:8].upper(); now = datetime.now(UTC)
    async with AsyncSessionLocal() as db:
        sensor_model = await db.scalar(select(SensorModel).where(SensorModel.code == "PH")); actuator_model = await db.scalar(select(ActuatorModel).limit(1))
        assert sensor_model is not None and actuator_model is not None
        sensor = Sensor(device_id=device.id, sensor_model_id=sensor_model.id, code=f"SCN-S-{suffix}", name="Scenario sensor", is_enabled=True)
        actuator = Actuator(device_id=device.id, actuator_model_id=actuator_model.id, sequence_number=992,
            code=f"SCN-A-{suffix}", name="Đèn chiếu sáng", is_enabled=True, desired_state=True,
            reported_state=True, voltage_v=12, current_a=0)
        db.add_all([sensor, actuator]); await db.commit()
        sensor_public, actuator_public = sensor.public_id, actuator.public_id
        sensor_internal, actuator_internal = sensor.id, actuator.id
    base = f"/api/v1/aquaponics-systems/{project.public_id}/devices/{device.public_id}"
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        sensor_create = await client.post(f"{base}/sensors/{sensor_public}/alert-scenarios", headers=headers(owner), json={
            "name": "pH ngoài khoảng", "risk_level": "HIGH", "duration_seconds": 0,
            "range_mode": "OUTSIDE_RANGE", "range": {"min": 6.5, "max": 8.0}})
        assert sensor_create.status_code == 201, sensor_create.text
        sensor_scenario_id = sensor_create.json()["id"]; assert isinstance(sensor_scenario_id, str)
        actuator_create = await client.post(f"{base}/actuators/{actuator_public}/alert-scenarios", headers=headers(admin), json={
            "name": "Đèn bật nhưng không có tải", "risk_level": "VERY_HIGH", "duration_seconds": 0,
            "reported_state": True, "voltage": {"min": 11, "max": 13}, "current": {"min": 0, "max": 0}})
        assert actuator_create.status_code == 201, actuator_create.text
        actuator_scenario_id = actuator_create.json()["id"]
        assert (await client.get(f"{base}/actuators/{actuator_public}/alert-scenarios", headers=headers(admin))).status_code == 200
        wrong = await client.get(f"/api/v1/aquaponics-systems/{project.public_id}/devices/{uuid4()}/actuators/{actuator_public}/alert-scenarios/{actuator_scenario_id}", headers=headers(admin))
        assert wrong.status_code == 404
    async with AsyncSessionLocal() as db:
        sensor = await db.get(Sensor, sensor_internal); actuator = await db.get(Actuator, actuator_internal); device_row = await db.get(Device, device.id)
        assert sensor is not None and actuator is not None and device_row is not None
        await evaluate_operational_rules_for_sensor(db, sensor=sensor, value=6.0, quality="VALID", recorded_at=now, received_at=now)
        await evaluate_alert_scenarios_for_actuator(db, device=device_row, actuator=actuator, recorded_at=now, received_at=now)
        await db.commit()
        sensor_incident = await db.scalar(select(OperationalIncident).where(OperationalIncident.sensor_id == sensor.id, OperationalIncident.status == "OPEN"))
        actuator_incident = await db.scalar(select(OperationalIncident).where(OperationalIncident.actuator_id == actuator.id, OperationalIncident.status == "OPEN"))
        assert sensor_incident is not None and actuator_incident is not None
        assert actuator_incident.trigger_snapshot["reported_state"] is True
        await evaluate_operational_rules_for_sensor(db, sensor=sensor, value=7.0, quality="VALID", recorded_at=now + timedelta(seconds=1), received_at=now + timedelta(seconds=1))
        await evaluate_operational_rules_for_sensor(db, sensor=sensor, value=6.0, quality="VALID", recorded_at=now + timedelta(seconds=2), received_at=now + timedelta(seconds=2))
        await db.commit(); assert sensor_incident.status == "RESOLVED"
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        assert (await client.patch(f"{base}/actuators/{actuator_public}/alert-scenarios/{actuator_scenario_id}", headers=headers(admin), json={"is_enabled": False})).status_code == 200
        assert (await client.delete(f"{base}/sensors/{sensor_public}/alert-scenarios/{sensor_scenario_id}", headers=headers(owner))).status_code == 204
    async with AsyncSessionLocal() as db:
        assert await db.scalar(select(OperationalIncident.id).where(OperationalIncident.actuator_id == actuator_internal, OperationalIncident.status == "NORMALIZED"))
        assert await db.scalar(select(OperationalIncident.id).where(OperationalIncident.sensor_id == sensor_internal, OperationalIncident.status == "NORMALIZED"))
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        assert (await client.patch(f"{base}/actuators/{actuator_public}/alert-scenarios/{actuator_scenario_id}", headers=headers(admin), json={"is_enabled": True})).status_code == 200
    async with AsyncSessionLocal() as db:
        actuator = await db.get(Actuator, actuator_internal); device_row = await db.get(Device, device.id)
        assert actuator is not None and device_row is not None
        actuator.reported_state = True
        await evaluate_alert_scenarios_for_actuator(db, device=device_row, actuator=actuator, recorded_at=now + timedelta(seconds=3), received_at=now + timedelta(seconds=3))
        reopened = await db.scalar(select(OperationalIncident).where(OperationalIncident.actuator_id == actuator.id, OperationalIncident.status == "OPEN"))
        assert reopened is not None
        actuator.reported_state = False
        await evaluate_alert_scenarios_for_actuator(db, device=device_row, actuator=actuator, recorded_at=now + timedelta(seconds=4), received_at=now + timedelta(seconds=4))
        await db.commit(); assert reopened.status == "NORMALIZED"
    async with AsyncSessionLocal() as db:
        incident_ids = select(OperationalIncident.id).where((OperationalIncident.sensor_id == sensor_internal) | (OperationalIncident.actuator_id == actuator_internal))
        await db.execute(delete(NotificationOutbox).where(NotificationOutbox.incident_id.in_(incident_ids)))
        await db.execute(delete(OperationalIncident).where(OperationalIncident.id.in_(incident_ids)))
        await db.execute(delete(Sensor).where(Sensor.id == sensor_internal)); await db.execute(delete(Actuator).where(Actuator.id == actuator_internal))
        await db.execute(delete(AlertRule).where(AlertRule.public_id.in_([sensor_scenario_id, actuator_scenario_id]))); await db.commit()
