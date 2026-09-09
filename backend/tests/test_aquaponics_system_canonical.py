from uuid import uuid4

import httpx
import pytest
from sqlalchemy import delete, select

from app.core.enums import UserRole
from app.core.security import create_access_token
from app.db.session import AsyncSessionLocal
from app.main import app
from app.models.actuator import Actuator
from app.models.actuator_model import ActuatorModel
from app.models.device import Device
from app.models.project import Project
from app.models.sensor import Sensor
from app.models.sensor_model import SensorModel
from app.models.user import User


@pytest.mark.asyncio
async def test_aquaponics_system_device_can_own_sensors_and_actuators() -> None:
    suffix = uuid4().hex[:10].upper()
    async with AsyncSessionLocal() as db:
        admin = await db.scalar(select(User).where(User.system_role == UserRole.ADMIN))
        sensor_model = await db.scalar(select(SensorModel).where(SensorModel.is_active.is_(True)))
        actuator_model = await db.scalar(select(ActuatorModel).where(ActuatorModel.is_active.is_(True)))
        assert admin and sensor_model and actuator_model
        token = create_access_token(str(admin.id), {"role": "ADMIN", "token_version": admin.token_version})
        headers = {"Authorization": f"Bearer {token}"}

    system_id = device_id = 0
    try:
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
            created = await client.post("/api/v1/aquaponics-systems", headers=headers, json={"code": f"AQUA-{suffix}", "name": "Hệ thống regression"})
            assert created.status_code == 201, created.text
            system_id = created.json()["id"]
            device = await client.post(f"/api/v1/aquaponics-systems/{system_id}/devices", headers=headers, json={"code": f"DEVICE-{suffix}", "name": "Aquaponics Controller"})
            assert device.status_code == 201, device.text
            device_id = device.json()["id"]
            for index in range(2):
                response = await client.post(f"/api/v1/aquaponics-systems/{system_id}/devices/{device_id}/sensors", headers=headers, json={"sensor_model_id": sensor_model.id, "code": f"SENSOR-{suffix}-{index}", "name": f"Sensor {index}"})
                assert response.status_code == 201, response.text
            for index in range(2):
                response = await client.post(f"/api/v1/aquaponics-systems/{system_id}/devices/{device_id}/actuators", headers=headers, json={"actuator_model_id": actuator_model.id, "code": f"ACTUATOR-{suffix}-{index}", "name": f"Actuator {index}"})
                assert response.status_code == 201, response.text
            detail = await client.get(f"/api/v1/aquaponics-systems/{system_id}/devices/{device_id}", headers=headers)
            assert detail.status_code == 200, detail.text
            assert len(detail.json()["sensors"]) == 2
            assert len(detail.json()["actuators"]) == 2
    finally:
        async with AsyncSessionLocal() as db:
            if device_id:
                await db.execute(delete(Actuator).where(Actuator.device_id == device_id))
                await db.execute(delete(Sensor).where(Sensor.device_id == device_id))
                await db.execute(delete(Device).where(Device.id == device_id))
            if system_id:
                await db.execute(delete(Project).where(Project.id == system_id))
            await db.commit()
