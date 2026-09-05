from datetime import UTC, datetime
from uuid import uuid4

import httpx
from sqlalchemy import delete, select

from app.core.enums import SensorPurpose, UserRole
from app.core.security import create_access_token
from app.db.session import AsyncSessionLocal, engine
from app.main import app
from app.models.actuator import Actuator
from app.models.actuator_model import ActuatorModel, ActuatorModelFeedbackDefinition
from app.models.device import Device
from app.models.device_template import DeviceTemplate, DeviceTemplateActuator
from app.models.operational_alert import ActuatorFeedbackBinding
from app.models.project import Project
from app.models.sensor import Sensor, SensorModel
from app.models.telemetry import TelemetryReading
from app.models.user import User
from app.mqtt.schemas import MqttTelemetryPayload
from app.services.monitoring_service import get_project_monitoring_latest
from app.services.telemetry_ingest_service import ingest_mqtt_telemetry


def _auth(user: User) -> dict[str, str]:
    return {"Authorization": f"Bearer {create_access_token(str(user.id), {'role': user.system_role.value, 'token_version': user.token_version})}"}


async def test_actuator_model_supports_voltage_current_threshold_crud() -> None:
    suffix = uuid4().hex[:8].upper()
    model_id: int | None = None
    async with AsyncSessionLocal() as db:
        admin = await db.scalar(select(User).where(User.system_role == UserRole.ADMIN, User.is_deleted.is_(False)))
        voltage = await db.scalar(select(SensorModel).where(SensorModel.code == "OUTPUT_VOLTAGE_V", SensorModel.is_active.is_(True)))
        current = await db.scalar(select(SensorModel).where(SensorModel.code == "LOAD_CURRENT_A", SensorModel.is_active.is_(True)))
        assert admin and voltage and current
        headers = _auth(admin)
    transport = httpx.ASGITransport(app=app)
    try:
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            payload = {
                "code": f"ELECTRICAL_{suffix}", "name": f"Mẫu điện {suffix}",
                "feedbacks": [
                    {"feedback_role": "SUPPLY_VOLTAGE", "sensor_model_id": voltage.id, "value_key": "voltage_v", "unit": "V", "data_type": "FLOAT", "default_lower_threshold": 11, "default_upper_threshold": 13, "display_order": 0},
                    {"feedback_role": "RUNNING_CURRENT", "sensor_model_id": current.id, "value_key": "current_a", "unit": "A", "data_type": "FLOAT", "default_lower_threshold": None, "default_upper_threshold": None, "display_order": 1},
                ],
            }
            created = await client.post("/api/v1/admin/actuator-models", headers=headers, json=payload)
            assert created.status_code == 201, created.text
            model_id = created.json()["id"]
            assert [item["feedback_role"] for item in created.json()["feedbacks"]] == ["SUPPLY_VOLTAGE", "RUNNING_CURRENT"]
            assert created.json()["feedbacks"][0]["default_lower_threshold"] == 11

            invalid_unit = {**payload, "feedbacks": [{**payload["feedbacks"][0], "unit": "°C"}]}
            assert (await client.patch(f"/api/v1/admin/actuator-models/{model_id}", headers=headers, json={"feedbacks": invalid_unit["feedbacks"]})).status_code == 422
            invalid_order = {**payload["feedbacks"][0], "default_lower_threshold": 13, "default_upper_threshold": 11}
            assert (await client.patch(f"/api/v1/admin/actuator-models/{model_id}", headers=headers, json={"feedbacks": [invalid_order]})).status_code == 422

            edited = await client.patch(f"/api/v1/admin/actuator-models/{model_id}", headers=headers, json={"feedbacks": payload["feedbacks"]})
            assert edited.status_code == 200, edited.text
            assert len(edited.json()["feedbacks"]) == 2
    finally:
        if model_id is not None:
            async with AsyncSessionLocal() as db:
                await db.execute(delete(ActuatorModelFeedbackDefinition).where(ActuatorModelFeedbackDefinition.actuator_model_id == model_id))
                await db.execute(delete(ActuatorModel).where(ActuatorModel.id == model_id))
                await db.commit()


async def test_actuator_model_feedback_provisions_exports_and_ingests_canonical_mqtt() -> None:
    suffix = uuid4().hex[:8].upper()
    ids: dict[str, int] = {}
    async with AsyncSessionLocal() as db:
        admin = await db.scalar(select(User).where(User.system_role == UserRole.ADMIN, User.is_deleted.is_(False)))
        owner = await db.scalar(select(User).where(User.system_role == UserRole.OWNER, User.is_deleted.is_(False)))
        current_model = await db.scalar(select(SensorModel).where(SensorModel.code == "LOAD_CURRENT_A", SensorModel.is_active.is_(True)))
        voltage_model = await db.scalar(select(SensorModel).where(SensorModel.code == "OUTPUT_VOLTAGE_V", SensorModel.is_active.is_(True)))
        assert admin and owner and current_model and voltage_model
        template = DeviceTemplate(code=f"FB-{suffix}", name=f"Feedback {suffix}", is_active=True)
        project = Project(owner_user_id=owner.id, code=f"FBP-{suffix}", name=f"Feedback project {suffix}")
        db.add_all([template, project])
        await db.commit()
        ids.update(template=template.id, project=project.id)
        headers = _auth(admin)
        current_model_id = current_model.id
        voltage_model_id = voltage_model.id

    try:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            created_model = await client.post("/api/v1/admin/actuator-models", headers=headers, json={
                "code": f"PUMP_{suffix}", "name": f"Bơm {suffix}", "data_type": "BOOLEAN", "default_state": False, "is_active": True,
                "feedbacks": [
                    {"feedback_role": "SUPPLY_VOLTAGE", "sensor_model_id": voltage_model_id, "value_key": "voltage_v", "unit": "V", "data_type": "FLOAT", "default_lower_threshold": 11.0, "default_upper_threshold": 13.0, "is_required": True, "is_enabled": True, "display_order": 0},
                    {"feedback_role": "RUNNING_CURRENT", "sensor_model_id": current_model_id, "value_key": "current_a", "unit": "A", "data_type": "FLOAT", "is_required": True, "is_enabled": True, "display_order": 1},
                ],
            })
            assert created_model.status_code == 201, created_model.text
            model_payload = created_model.json()
            ids["model"] = model_payload["id"]
            definitions = {item["feedback_role"]: item for item in model_payload["feedbacks"]}
            assert definitions["SUPPLY_VOLTAGE"]["value_key"] == "voltage_v"
            assert definitions["RUNNING_CURRENT"]["unit"] == "A"

            invalid = await client.patch(f"/api/v1/admin/actuator-models/{ids['model']}", headers=headers, json={"feedbacks": [{"feedback_role": "RUNNING_CURRENT", "sensor_model_id": current_model_id, "value_key": "current_a", "unit": "°C", "data_type": "FLOAT"}]})
            assert invalid.status_code == 422

            mapping = await client.post(f"/api/v1/admin/device-templates/{ids['template']}/actuators", headers=headers, json={"actuator_model_id": ids["model"], "code": f"PUMP_{suffix}", "default_name": "Bơm kiểm thử", "actuator_type": "PUMP", "monitor_current": True, "sort_order": 0, "is_enabled": True})
            assert mapping.status_code == 201, mapping.text
            ids["mapping"] = mapping.json()["id"]
            provisioned = await client.post(f"/api/v1/projects/{ids['project']}/devices/from-template", headers=headers, json={"device_template_id": ids["template"], "name": "Bộ điều khiển feedback"})
            assert provisioned.status_code == 201, provisioned.text
            ids["device"] = provisioned.json()["id"]

            async with AsyncSessionLocal() as db:
                actuator = await db.scalar(select(Actuator).where(Actuator.device_id == ids["device"]))
                assert actuator
                bindings = list((await db.scalars(select(ActuatorFeedbackBinding).where(ActuatorFeedbackBinding.actuator_id == actuator.id))).all())
                assert {item.feedback_role for item in bindings} == {"SUPPLY_VOLTAGE", "RUNNING_CURRENT"}
                sensors_by_role = {item.feedback_role: await db.get(Sensor, item.sensor_id) for item in bindings}
                assert sensors_by_role["SUPPLY_VOLTAGE"] and sensors_by_role["SUPPLY_VOLTAGE"].sensor_model_id == voltage_model_id
                assert sensors_by_role["RUNNING_CURRENT"] and sensors_by_role["RUNNING_CURRENT"].sensor_model_id == current_model_id
                assert {sensor.purpose for sensor in sensors_by_role.values() if sensor is not None} == {SensorPurpose.ACTUATOR_FEEDBACK}
                ids.update(actuator=actuator.id)
                sensor_ids = [item.sensor_id for item in bindings]
                sensor_ids_by_role = {item.feedback_role: item.sensor_id for item in bindings}
                device = await db.get(Device, ids["device"])
                assert device
                device_code = device.code
                sensor_codes = {role: sensor.code for role, sensor in sensors_by_role.items() if sensor is not None}

            export = await client.get(f"/api/v1/projects/{ids['project']}/device-config/export", headers=headers)
            assert export.status_code == 200, export.text
            exported_feedbacks = {item["role"]: item for item in export.json()["devices"][0]["actuators"][0]["feedbacks"]}
            assert set(exported_feedbacks) == {"SUPPLY_VOLTAGE", "RUNNING_CURRENT"}
            assert exported_feedbacks["RUNNING_CURRENT"]["sensor_code"] == sensor_codes["RUNNING_CURRENT"]
            assert exported_feedbacks["RUNNING_CURRENT"]["sensor_model_code"] == "LOAD_CURRENT_A"
            assert exported_feedbacks["SUPPLY_VOLTAGE"]["lower_threshold"] == 11.0
            assert exported_feedbacks["SUPPLY_VOLTAGE"]["upper_threshold"] == 13.0
            assert exported_feedbacks["SUPPLY_VOLTAGE"]["mqtt"]["topic"] == f"aquaponics/{device_code}/telemetry"
            assert set(exported_feedbacks["SUPPLY_VOLTAGE"]["mqtt"]["payload"]) == {"sent_at", "readings"}

            download = await client.get(f"/api/v1/projects/{ids['project']}/devices/{ids['device']}/mqtt-connection-config", headers=headers)
            assert download.status_code == 200
            assert download.headers["content-type"].startswith("application/json")
            assert "attachment; filename=" in download.headers["content-disposition"]
            assert {item["role"] for item in download.json()["actuators"][0]["feedbacks"]} == {"SUPPLY_VOLTAGE", "RUNNING_CURRENT"}

            binding_url = f"/api/v1/projects/{ids['project']}/devices/{ids['device']}/actuators/{ids['actuator']}/feedback-binding"
            overridden = await client.put(binding_url, headers=headers, json={"feedback_role": "SUPPLY_VOLTAGE", "sensor_id": sensor_ids_by_role["SUPPLY_VOLTAGE"], "value_key": "voltage_v", "lower_threshold": 11.5, "upper_threshold": 12.5})
            assert overridden.status_code == 200, overridden.text
            assert overridden.json()["threshold_source"] == "ACTUATOR_OVERRIDE"
            assert overridden.json()["default_lower_threshold"] == 11.0
            invalid_threshold = await client.put(binding_url, headers=headers, json={"feedback_role": "SUPPLY_VOLTAGE", "sensor_id": sensor_ids_by_role["SUPPLY_VOLTAGE"], "value_key": "voltage_v", "lower_threshold": 13, "upper_threshold": 11})
            assert invalid_threshold.status_code == 422
            reset = await client.put(binding_url, headers=headers, json={"feedback_role": "SUPPLY_VOLTAGE", "sensor_id": sensor_ids_by_role["SUPPLY_VOLTAGE"], "value_key": "voltage_v", "lower_threshold": None, "upper_threshold": None})
            assert reset.status_code == 200, reset.text
            assert reset.json()["threshold_source"] == "MODEL_DEFAULT"
            assert reset.json()["effective_lower_threshold"] == 11.0

        now = datetime.now(UTC)
        async with AsyncSessionLocal() as db:
            result = await ingest_mqtt_telemetry(db, device_code=device_code, payload=MqttTelemetryPayload.model_validate({"sent_at": now, "readings": [{"sensor_code": sensor_codes["SUPPLY_VOLTAGE"], "value": 12.1, "recorded_at": now}, {"sensor_code": sensor_codes["RUNNING_CURRENT"], "value": 0, "recorded_at": now}]}), received_at=now)
            assert result and result.accepted == 2
            readings = list((await db.scalars(select(TelemetryReading).where(TelemetryReading.sensor_id.in_(sensor_ids)))).all())
            assert sorted(item.value for item in readings) == [0, 12.1]
            monitoring = await get_project_monitoring_latest(db, ids["project"])
            monitored = monitoring["devices"][0]["actuators"][0]
            assert monitored["electrical"]["configured"] is True
            assert monitored["electrical"]["voltage"]["value"] == 12.1
            assert monitored["electrical"]["current"]["value"] == 0
            assert monitored["electrical"]["voltage"]["threshold_source"] == "MODEL_DEFAULT"
            assert monitored["electrical"]["voltage"]["threshold_status"] == "IN_RANGE"
            assert monitored["electrical"]["current"]["threshold_status"] == "IN_RANGE"
            monitored_device = next(item for item in monitoring["devices"] if item["id"] == ids["device"])
            assert {item["code"] for item in monitored_device["sensors"]}.isdisjoint(set(sensor_codes.values()))

        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            actuator_list = await client.get(f"/api/v1/projects/{ids['project']}/devices/{ids['device']}/actuators", headers=headers)
            assert actuator_list.status_code == 200, actuator_list.text
            electrical = actuator_list.json()[0]["electrical_feedbacks"]
            assert electrical["voltage"]["sensor_code"] == sensor_codes["SUPPLY_VOLTAGE"]
            assert electrical["voltage"]["value"] == 12.1
            assert electrical["current"]["value"] == 0
    finally:
        async with AsyncSessionLocal() as db:
            if "sensor_ids" in locals():
                await db.execute(delete(TelemetryReading).where(TelemetryReading.sensor_id.in_(sensor_ids)))
            if "actuator" in ids:
                await db.execute(delete(ActuatorFeedbackBinding).where(ActuatorFeedbackBinding.actuator_id == ids["actuator"]))
                await db.execute(delete(Actuator).where(Actuator.id == ids["actuator"]))
            if "sensor_ids" in locals():
                await db.execute(delete(Sensor).where(Sensor.id.in_(sensor_ids)))
            if "device" in ids:
                await db.execute(delete(Device).where(Device.id == ids["device"]))
            if "mapping" in ids:
                await db.execute(delete(DeviceTemplateActuator).where(DeviceTemplateActuator.id == ids["mapping"]))
            await db.execute(delete(DeviceTemplate).where(DeviceTemplate.id == ids["template"]))
            await db.execute(delete(Project).where(Project.id == ids["project"]))
            if "model" in ids:
                await db.execute(delete(ActuatorModelFeedbackDefinition).where(ActuatorModelFeedbackDefinition.actuator_model_id == ids["model"]))
                await db.execute(delete(ActuatorModel).where(ActuatorModel.id == ids["model"]))
            await db.commit()
        await engine.dispose()
