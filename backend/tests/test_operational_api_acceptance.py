from uuid import uuid4

import httpx
import pytest
from sqlalchemy import delete, func, select

from app.db.session import AsyncSessionLocal
from app.main import app
from app.models.actuator import Actuator
from app.models.actuator_model import ActuatorModel
from app.models.operational_alert import AlertRule, AlertRuleProfile, AlertRuleSensorModelProfile, ActuatorFeedbackBinding
from app.models.sensor import Sensor
from app.models.sensor_model import SensorModel
from test_visibility_authorization import auth_header, visibility_data


@pytest.mark.asyncio
async def test_operational_api_contract_and_role_matrix(visibility_data) -> None:
    data = visibility_data
    suffix = uuid4().hex[:8].upper()
    created: dict[str, int] = {}
    async with AsyncSessionLocal() as db:
        current_model = await db.scalar(select(SensorModel).where(SensorModel.code == "LOAD_CURRENT_A"))
        canonical_model = await db.scalar(select(SensorModel).where(SensorModel.code == "PH"))
        actuator_model = await db.scalar(select(ActuatorModel).where(ActuatorModel.is_active.is_(True)))
        rule = await db.scalar(select(AlertRule).where(AlertRule.code == "WATER_PH_OUT_OF_RANGE"))
        assert current_model and canonical_model and actuator_model and rule
        actuator = Actuator(device_id=data["active_device"], actuator_model_id=actuator_model.id, sequence_number=970, code=f"API-ACT-{suffix}", name="Bơm API", is_enabled=True)
        sensor_a = Sensor(device_id=data["active_device"], sensor_model_id=current_model.id, code=f"API-CUR-A-{suffix}", name="Dòng A", is_enabled=True)
        sensor_b = Sensor(device_id=data["other_device"], sensor_model_id=current_model.id, code=f"API-CUR-B-{suffix}", name="Dòng B", is_enabled=True)
        db.add_all([actuator, sensor_a, sensor_b])
        await db.commit()
        created = {"actuator": actuator.id, "sensor_a": sensor_a.id, "sensor_b": sensor_b.id, "rule": rule.id, "canonical_model": canonical_model.id}

    admin = auth_header(data["admin_id"], data["admin_version"], "ADMIN")
    owner = auth_header(data["owner_id"], data["owner_version"], "OWNER")
    viewer = auth_header(data["viewer_id"], data["viewer_version"], "VIEWER")
    base = f"/api/v1/projects/{data['active_project']}"
    binding_url = f"{base}/devices/{data['active_device']}/actuators/{created['actuator']}/feedback-binding"
    profile_code = f"API_PROFILE_{suffix}"
    transport = httpx.ASGITransport(app=app)
    try:
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            rules = await client.get("/api/v1/admin/alert-rules", headers=admin)
            assert rules.status_code == 200 and len(rules.json()) == 19
            assert (await client.get(f"/api/v1/admin/alert-rules/{created['rule']}", headers=admin)).status_code == 200
            assert (await client.get("/api/v1/admin/alert-rules", headers=owner)).status_code == 403

            created_profile = await client.post(f"/api/v1/admin/alert-rules/{created['rule']}/profiles", headers=admin, json={"code": profile_code, "name": "Hồ sơ API", "config": {}, "sensor_model_ids": [created["canonical_model"]], "actuator_model_ids": []})
            assert created_profile.status_code == 201, created_profile.text
            created["profile"] = created_profile.json()["id"]
            assert (await client.get(f"/api/v1/admin/alert-rules/{created['rule']}/profiles", headers=admin)).status_code == 200
            assert (await client.post(f"/api/v1/admin/alert-rules/{created['rule']}/profiles", headers=owner, json={"code": f"DENIED_{suffix}", "name": "Không được phép", "config": {}, "sensor_model_ids": [], "actuator_model_ids": []})).status_code == 403

            assert (await client.put(binding_url, headers=owner, json={"sensor_id": created["sensor_a"]})).status_code == 403
            first_binding = await client.put(binding_url, headers=admin, json={"sensor_id": created["sensor_a"]})
            assert first_binding.status_code == 200, first_binding.text
            second_binding = await client.put(binding_url, headers=admin, json={"sensor_id": created["sensor_a"]})
            assert second_binding.status_code == 200 and second_binding.json()["id"] == first_binding.json()["id"]
            assert (await client.put(binding_url, headers=admin, json={"sensor_id": created["sensor_b"]})).status_code == 409
            assert (await client.get(binding_url, headers=viewer)).status_code == 403

            assert (await client.get(f"{base}/operational-incidents", headers=viewer)).status_code == 200
            assert (await client.get(f"/api/v1/projects/{data['project_ids'][1]}/operational-incidents", headers=viewer)).status_code == 404
            assert (await client.get(f"{base}/notification-settings", headers=owner)).status_code == 200
            assert (await client.get(f"{base}/notification-settings", headers=viewer)).status_code == 403
            assert (await client.get(f"{base}/notification-history", headers=owner)).status_code == 200
            assert (await client.get(f"{base}/notification-history", headers=viewer)).status_code == 403
            assert (await client.delete(binding_url, headers=admin)).status_code == 204

        async with AsyncSessionLocal() as db:
            assert await db.scalar(select(func.count(ActuatorFeedbackBinding.id)).where(ActuatorFeedbackBinding.actuator_id == created["actuator"])) == 0
    finally:
        async with AsyncSessionLocal() as db:
            await db.execute(delete(ActuatorFeedbackBinding).where(ActuatorFeedbackBinding.actuator_id == created["actuator"]))
            if "profile" in created:
                await db.execute(delete(AlertRuleSensorModelProfile).where(AlertRuleSensorModelProfile.profile_id == created["profile"]))
                await db.execute(delete(AlertRuleProfile).where(AlertRuleProfile.id == created["profile"]))
            await db.execute(delete(Actuator).where(Actuator.id == created["actuator"]))
            await db.execute(delete(Sensor).where(Sensor.id.in_([created["sensor_a"], created["sensor_b"]])))
            await db.commit()
