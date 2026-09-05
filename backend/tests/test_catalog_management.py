from uuid import uuid4

import httpx
from sqlalchemy import delete, select

from app.core.enums import UserRole, UserStatus
from app.core.security import create_access_token, hash_password
from app.db.session import AsyncSessionLocal, engine
from app.main import app
from app.models.actuator import Actuator
from app.models.actuator_model import ActuatorModel
from app.models.operational_alert import ActuatorFeedbackBinding
from app.models.device import Device
from app.models.device_template import (
    DeviceTemplate,
    DeviceTemplateActuator,
    DeviceTemplateSensor,
)
from app.models.sensor import Sensor, SensorModel
from app.models.project import Project
from app.models.user import User


def auth_header(user: User) -> dict[str, str]:
    token = create_access_token(
        str(user.id),
        {"role": user.system_role.value, "token_version": user.token_version},
    )
    return {"Authorization": f"Bearer {token}"}


async def test_admin_device_template_list_eager_loads_all_mappings() -> None:
    suffix = uuid4().hex[:10].upper()
    async with AsyncSessionLocal() as db:
        admin = await db.scalar(
            select(User).where(
                User.system_role == UserRole.ADMIN,
                User.is_deleted.is_(False),
            )
        )
        sensor_model = await db.scalar(
            select(SensorModel).where(SensorModel.is_deleted.is_(False))
        )
        actuator_model = ActuatorModel(
            code=f"ACTUATOR-{suffix}",
            name=f"Actuator regression {suffix}",
            description="Regression fixture",
        )
        db.add(actuator_model)
        await db.flush()
        assert admin is not None
        assert sensor_model is not None

        template = DeviceTemplate(
            code=f"CATALOG-{suffix}",
            name=f"Catalog regression {suffix}",
        )
        db.add(template)
        await db.flush()
        db.add_all(
            [
                DeviceTemplateSensor(
                    device_template_id=template.id,
                    sensor_model_id=sensor_model.id,
                    sort_order=0,
                ),
                DeviceTemplateActuator(
                    device_template_id=template.id,
                    actuator_model_id=actuator_model.id,
                    code=actuator_model.code,
                    sort_order=0,
                ),
            ]
        )
        await db.commit()
        template_id = template.id
        sensor_model_id = sensor_model.id
        actuator_model_id = actuator_model.id
        headers = auth_header(admin)

    try:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(
            transport=transport,
            base_url="http://test",
        ) as client:
            response = await client.get(
                "/api/v1/admin/device-templates",
                params={"q": suffix},
                headers=headers,
            )

        assert response.status_code == 200
        payload = response.json()
        assert payload["total"] == 1
        assert payload["items"][0]["sensors"][0]["sensor_model_id"] == sensor_model_id
        assert (
            payload["items"][0]["actuators"][0]["actuator_model_id"]
            == actuator_model_id
        )
    finally:
        async with AsyncSessionLocal() as db:
            await db.execute(
                delete(DeviceTemplateSensor).where(
                    DeviceTemplateSensor.device_template_id == template_id
                )
            )
            await db.execute(
                delete(DeviceTemplateActuator).where(
                    DeviceTemplateActuator.device_template_id == template_id
                )
            )
            await db.execute(
                delete(DeviceTemplate).where(DeviceTemplate.id == template_id)
            )
            await db.execute(
                delete(ActuatorModel).where(ActuatorModel.id == actuator_model_id)
            )
            await db.commit()
        await engine.dispose()


async def test_non_admin_cannot_load_admin_catalog() -> None:
    suffix = uuid4().hex[:10].lower()
    async with AsyncSessionLocal() as db:
        user = User(
            username=f"catalog-owner-{suffix}",
            password_hash=hash_password("CatalogOwner@123"),
            full_name="Catalog Owner",
            email=f"catalog-owner-{suffix}@example.test",
            phone_number=f"09{suffix[:8]}",
            system_role=UserRole.OWNER,
            status=UserStatus.ACTIVE,
            must_change_password=False,
        )
        db.add(user)
        await db.commit()
        user_id = user.id
        headers = auth_header(user)

    try:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(
            transport=transport,
            base_url="http://test",
        ) as client:
            response = await client.get(
                "/api/v1/admin/device-templates",
                headers=headers,
            )
        assert response.status_code == 403
    finally:
        async with AsyncSessionLocal() as db:
            await db.execute(delete(User).where(User.id == user_id))
            await db.commit()
        await engine.dispose()


async def test_admin_template_sensor_crud_rejects_duplicates_and_persists_required_order() -> None:
    suffix = uuid4().hex[:10].upper()
    async with AsyncSessionLocal() as db:
        admin = await db.scalar(select(User).where(User.system_role == UserRole.ADMIN, User.is_deleted.is_(False)))
        sensor_model = await db.scalar(select(SensorModel).where(SensorModel.is_deleted.is_(False), SensorModel.is_active.is_(True)))
        assert admin is not None
        assert sensor_model is not None
        template = DeviceTemplate(code=f"CRUD-{suffix}", name=f"CRUD {suffix}", is_active=True)
        db.add(template)
        await db.commit()
        template_id = template.id
        headers = auth_header(admin)
        sensor_model_id = sensor_model.id
    try:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            created = await client.post(
                f"/api/v1/admin/device-templates/{template_id}/sensors",
                headers=headers,
                json={"sensor_model_id": sensor_model_id, "sort_order": 4, "is_required": False},
            )
            assert created.status_code == 201
            mapping_id = created.json()["id"]
            duplicate = await client.post(
                f"/api/v1/admin/device-templates/{template_id}/sensors",
                headers=headers,
                json={"sensor_model_id": sensor_model_id, "sort_order": 5, "is_required": True},
            )
            assert duplicate.status_code == 409
            updated = await client.patch(
                f"/api/v1/admin/device-templates/{template_id}/sensors/{mapping_id}",
                headers=headers,
                json={"sort_order": 2, "is_required": True},
            )
            assert updated.status_code == 200
            assert updated.json()["sort_order"] == 2
            assert updated.json()["is_required"] is True
            removed = await client.delete(
                f"/api/v1/admin/device-templates/{template_id}/sensors/{mapping_id}", headers=headers
            )
            assert removed.status_code == 204
    finally:
        async with AsyncSessionLocal() as db:
            await db.execute(delete(DeviceTemplateSensor).where(DeviceTemplateSensor.device_template_id == template_id))
            await db.execute(delete(DeviceTemplate).where(DeviceTemplate.id == template_id))
            await db.commit()
        await engine.dispose()


async def test_default_actuator_catalog_is_seeded() -> None:
    expected = {
        "FISH_TANK_PUMP": ("Bơm hút bể cá", 1),
        "IRRIGATION_PUMP": ("Bơm tưới", 2),
        "MIST_SYSTEM": ("Phun sương", 3),
        "GROW_LIGHT": ("Đèn chiếu sáng", 4),
        "ALARM_SIREN": ("Còi cảnh báo", 5),
    }
    async with AsyncSessionLocal() as db:
        rows = (
            await db.scalars(
                select(ActuatorModel).where(
                    ActuatorModel.code.in_(expected),
                    ActuatorModel.is_deleted.is_(False),
                )
            )
        ).all()

    assert {row.code for row in rows} == set(expected)
    assert len(rows) == len(expected)
    for row in rows:
        name, sort_order = expected[row.code]
        assert row.name == name
        assert row.data_type == "BOOLEAN"
        assert row.default_state is False
        assert row.is_active is True
        assert row.sort_order == sort_order
        assert row.description


async def test_admin_template_actuator_crud_and_runtime_provisioning() -> None:
    suffix = uuid4().hex[:10].upper()
    async with AsyncSessionLocal() as db:
        admin = await db.scalar(select(User).where(User.system_role == UserRole.ADMIN, User.is_deleted.is_(False)))
        owner = await db.scalar(select(User).where(User.system_role == UserRole.OWNER, User.is_deleted.is_(False)))
        model = await db.scalar(select(ActuatorModel).where(ActuatorModel.is_deleted.is_(False), ActuatorModel.is_active.is_(True)))
        assert admin and owner and model
        template = DeviceTemplate(code=f"ACTCRUD-{suffix}", name=f"Actuator CRUD {suffix}", is_active=True)
        project = Project(owner_user_id=owner.id, code=f"ACTP-{suffix}", name=f"Provision {suffix}")
        db.add_all([template, project])
        await db.commit()
        template_id, project_id, model_id = template.id, project.id, model.id
        headers = auth_header(admin)

    mapping_id = device_id = actuator_id = None
    try:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            payload = {
                "actuator_model_id": model_id,
                "code": f"PUMP_{suffix}",
                "default_name": "Bơm tuần hoàn mẫu",
                "actuator_type": "PUMP",
                "default_state": True,
                "command_capability": "ON_OFF",
                "monitor_current": True,
                "electrical_profile_id": None,
                "sort_order": 3,
                "is_required": True,
                "is_enabled": True,
            }
            created = await client.post(f"/api/v1/admin/device-templates/{template_id}/actuators", headers=headers, json=payload)
            assert created.status_code == 201, created.text
            mapping_id = created.json()["id"]
            assert created.json()["code"] == f"PUMP_{suffix}"
            assert created.json()["monitor_current"] is True

            listed = await client.get(f"/api/v1/admin/device-templates/{template_id}/actuators", headers=headers)
            assert listed.status_code == 200
            assert [item["id"] for item in listed.json()] == [mapping_id]
            read = await client.get(f"/api/v1/admin/device-templates/{template_id}/actuators/{mapping_id}", headers=headers)
            assert read.status_code == 200

            duplicate = await client.post(f"/api/v1/admin/device-templates/{template_id}/actuators", headers=headers, json={**payload, "default_name": "Trùng mã"})
            assert duplicate.status_code == 409
            invalid_model = await client.post(f"/api/v1/admin/device-templates/{template_id}/actuators", headers=headers, json={**payload, "code": f"INVALID_{suffix}", "actuator_model_id": 999999999})
            assert invalid_model.status_code == 404

            updated = await client.patch(f"/api/v1/admin/device-templates/{template_id}/actuators/{mapping_id}", headers=headers, json={"default_name": "Bơm NFT", "default_state": False, "sort_order": 1, "is_enabled": True})
            assert updated.status_code == 200, updated.text
            assert updated.json()["default_name"] == "Bơm NFT"
            assert updated.json()["default_state"] is False

            provisioned = await client.post(f"/api/v1/projects/{project_id}/devices/from-template", headers=headers, json={"device_template_id": template_id, "name": "Bộ điều khiển NFT"})
            assert provisioned.status_code == 201, provisioned.text
            device_id = provisioned.json()["id"]
            async with AsyncSessionLocal() as db:
                actuator = await db.scalar(select(Actuator).where(Actuator.device_id == device_id, Actuator.name == "Bơm NFT"))
                assert actuator is not None
                actuator_id = actuator.id
                assert actuator.desired_state is False

            removed = await client.delete(f"/api/v1/admin/device-templates/{template_id}/actuators/{mapping_id}", headers=headers)
            assert removed.status_code == 204
            assert (await client.get(f"/api/v1/admin/device-templates/{template_id}/actuators", headers=headers)).json() == []
    finally:
        async with AsyncSessionLocal() as db:
            if actuator_id is not None:
                await db.execute(delete(ActuatorFeedbackBinding).where(ActuatorFeedbackBinding.actuator_id == actuator_id))
                await db.execute(delete(Actuator).where(Actuator.id == actuator_id))
            if device_id is not None:
                await db.execute(delete(Sensor).where(Sensor.device_id == device_id))
                await db.execute(delete(Device).where(Device.id == device_id))
            await db.execute(delete(DeviceTemplateActuator).where(DeviceTemplateActuator.device_template_id == template_id))
            await db.execute(delete(DeviceTemplate).where(DeviceTemplate.id == template_id))
            await db.execute(delete(Project).where(Project.id == project_id))
            await db.commit()
