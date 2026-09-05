from uuid import uuid4

import httpx
import pytest
from sqlalchemy import delete, select

from app.db.session import AsyncSessionLocal, engine
from app.core.enums import DeviceStatus, ProjectStatus, UserRole, UserStatus
from app.core.security import create_access_token, hash_password
from app.main import app
from app.models.audit import AuditLog
from app.models.device import Device
from app.models.project import Project, ProjectMember
from app.models.sensor import Sensor, SensorModel
from app.models.user import User


def auth_header(user_id: int, token_version: int, role: str) -> dict[str, str]:
    token = create_access_token(
        str(user_id),
        {"role": role, "token_version": token_version},
    )
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
async def visibility_data():
    suffix = uuid4().hex[:10].upper()
    async with AsyncSessionLocal() as db:
        admin = await db.scalar(
            select(User).where(
                User.system_role == UserRole.ADMIN,
                User.status == UserStatus.ACTIVE,
                User.is_deleted.is_(False),
                User.deleted_at.is_(None),
            ).order_by(User.id)
        )
        sensor_model = await db.scalar(
            select(SensorModel).where(SensorModel.is_deleted.is_(False))
        )
        if admin is None or sensor_model is None:
            pytest.skip("Cần một tài khoản ADMIN active và SensorModel để chạy integration test")

        assert admin.system_role == UserRole.ADMIN
        assert admin.status == UserStatus.ACTIVE
        assert admin.is_deleted is False
        assert admin.deleted_at is None

        owner = User(
            username=f"visibility-owner-{suffix.lower()}",
            password_hash=hash_password("Visibility@123"),
            full_name="Visibility Owner",
            email=f"visibility-owner-{suffix.lower()}@example.test",
            phone_number=f"07{suffix[:8]}",
            system_role=UserRole.OWNER,
            status=UserStatus.ACTIVE,
            must_change_password=False,
        )
        viewer = User(
            username=f"visibility-viewer-{suffix.lower()}",
            password_hash=hash_password("Visibility@123"),
            full_name="Visibility Viewer",
            email=f"visibility-viewer-{suffix.lower()}@example.test",
            phone_number=f"06{suffix[:8]}",
            system_role=UserRole.VIEWER,
            status=UserStatus.ACTIVE,
            must_change_password=False,
        )
        db.add_all([owner, viewer])
        await db.flush()

        active_project = Project(
            owner_user_id=owner.id,
            code=f"VIS-ACTIVE-{suffix}",
            name="Visibility Active Project",
            status=ProjectStatus.ACTIVE,
        )
        other_project = Project(
            owner_user_id=owner.id,
            code=f"VIS-OTHER-{suffix}",
            name="Visibility Other Project",
            status=ProjectStatus.ACTIVE,
        )
        disabled_project = Project(
            owner_user_id=owner.id,
            code=f"VIS-DISABLED-{suffix}",
            name="Visibility Disabled Project",
            status=ProjectStatus.DISABLED,
        )
        db.add_all([active_project, other_project, disabled_project])
        await db.flush()

        member = ProjectMember(
            project_id=active_project.id,
            user_id=viewer.id,
            role=UserRole.VIEWER.value,
            created_by=admin.id,
        )
        active_device = Device(
            project_id=active_project.id,
            code=f"VIS-DEVICE-A-{suffix}",
            name="Visibility Active Device",
            status=DeviceStatus.OFFLINE,
        )
        other_device = Device(
            project_id=other_project.id,
            code=f"VIS-DEVICE-B-{suffix}",
            name="Visibility Other Device",
            status=DeviceStatus.OFFLINE,
        )
        disabled_device = Device(
            project_id=disabled_project.id,
            code=f"VIS-DEVICE-D-{suffix}",
            name="Visibility Disabled Device",
            status=DeviceStatus.OFFLINE,
        )
        db.add_all([member, active_device, other_device, disabled_device])
        await db.flush()

        active_sensor = Sensor(
            device_id=active_device.id,
            sensor_model_id=sensor_model.id,
            code=f"VIS-SENSOR-A-{suffix}",
            name="Visibility Active Sensor",
        )
        other_sensor = Sensor(
            device_id=other_device.id,
            sensor_model_id=sensor_model.id,
            code=f"VIS-SENSOR-B-{suffix}",
            name="Visibility Other Sensor",
        )
        disabled_sensor = Sensor(
            device_id=disabled_device.id,
            sensor_model_id=sensor_model.id,
            code=f"VIS-SENSOR-D-{suffix}",
            name="Visibility Disabled Sensor",
        )
        db.add_all([active_sensor, other_sensor, disabled_sensor])
        await db.commit()

        data = {
            "admin_id": admin.id,
            "admin_version": admin.token_version,
            "owner_id": owner.id,
            "owner_version": owner.token_version,
            "viewer_id": viewer.id,
            "viewer_version": viewer.token_version,
            "user_ids": [owner.id, viewer.id],
            "project_ids": [active_project.id, other_project.id, disabled_project.id],
            "active_project": active_project.id,
            "disabled_project": disabled_project.id,
            "device_ids": [active_device.id, other_device.id, disabled_device.id],
            "active_device": active_device.id,
            "other_device": other_device.id,
            "disabled_device": disabled_device.id,
            "sensor_ids": [active_sensor.id, other_sensor.id, disabled_sensor.id],
            "active_sensor": active_sensor.id,
            "other_sensor": other_sensor.id,
            "disabled_sensor": disabled_sensor.id,
        }

    try:
        yield data
    finally:
        async with AsyncSessionLocal() as db:
            await db.execute(
                delete(AuditLog).where(
                    AuditLog.action.in_(
                        ["UPDATE_DEVICE_VISIBILITY", "UPDATE_SENSOR_VISIBILITY"]
                    ),
                    AuditLog.entity_id.in_(data["device_ids"] + data["sensor_ids"]),
                )
            )
            await db.execute(delete(Sensor).where(Sensor.id.in_(data["sensor_ids"])))
            await db.execute(delete(Device).where(Device.id.in_(data["device_ids"])))
            await db.execute(
                delete(ProjectMember).where(ProjectMember.project_id.in_(data["project_ids"]))
            )
            await db.execute(delete(Project).where(Project.id.in_(data["project_ids"])))
            await db.execute(delete(User).where(User.id.in_(data["user_ids"])))
            await db.commit()
        await engine.dispose()


@pytest.mark.asyncio
async def test_device_sensor_enabled_lifecycle_contract(visibility_data) -> None:
    data = visibility_data
    admin_headers = auth_header(data["admin_id"], data["admin_version"], "ADMIN")
    owner_headers = auth_header(data["owner_id"], data["owner_version"], "OWNER")
    viewer_headers = auth_header(data["viewer_id"], data["viewer_version"], "VIEWER")
    device_url = f"/api/v1/projects/{data['active_project']}/devices/{data['active_device']}"
    sensor_url = f"/api/v1/devices/{data['active_device']}/sensors/{data['active_sensor']}"

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        for headers, expected_role in ((owner_headers, "OWNER"), (viewer_headers, "VIEWER")):
            for url in (f"{device_url}/disable", f"{sensor_url}/disable"):
                forbidden = await client.post(url, headers=headers, json={"reason": "test"})
                assert forbidden.status_code == 403
                assert forbidden.json()["detail"] == {
                    "code": "ADMIN_REQUIRED",
                    "detail": "Chỉ Quản trị viên mới có quyền thực hiện thao tác này.",
                    "current_role": expected_role,
                }

        assert (await client.post(f"{device_url}/disable", headers=admin_headers, json={"reason": "bảo trì"})).status_code == 204
        assert (await client.post(f"{sensor_url}/disable", headers=admin_headers, json={"reason": "hiệu chuẩn"})).status_code == 204

        user_projects = await client.get(
            f"/api/v1/admin/users/{data['owner_id']}/projects",
            headers=admin_headers,
        )
        assert user_projects.status_code == 200
        user_projects_payload = user_projects.json()
        assert "devices" not in user_projects_payload
        project_summary = next(
            item
            for item in user_projects_payload["items"]
            if item["id"] == data["active_project"]
        )
        assert project_summary["device_count"] == 1

        project_devices = await client.get(
            f"/api/v1/projects/{data['active_project']}/devices",
            headers=admin_headers,
        )
        device_sensors = await client.get(
            f"/api/v1/devices/{data['active_device']}/sensors?include_disabled=true",
            headers=admin_headers,
        )
        assert data["active_device"] not in {
            item["id"] for item in project_devices.json()["items"]
        }
        assert data["active_sensor"] in {
            item["id"] for item in device_sensors.json()
        }

        admin_disabled_devices = await client.get(f"/api/v1/projects/{data['active_project']}/devices?include_disabled=true", headers=admin_headers)
        admin_disabled_sensors = await client.get(f"/api/v1/devices/{data['active_device']}/sensors?include_disabled=true", headers=admin_headers)
        assert data["active_device"] in {item["id"] for item in admin_disabled_devices.json()["items"]}
        assert data["active_sensor"] in {item["id"] for item in admin_disabled_sensors.json()}

        for headers in (owner_headers, viewer_headers):
            assert (await client.get(f"/api/v1/projects/{data['active_project']}/devices?include_disabled=true", headers=headers)).status_code == 403
            assert (await client.get(f"/api/v1/devices/{data['active_device']}/sensors?include_disabled=true", headers=headers)).status_code == 403

        disabled_device = await client.post(f"/api/v1/projects/{data['disabled_project']}/devices/{data['disabled_device']}/disable", headers=admin_headers, json={"reason": "x"})
        disabled_sensor = await client.post(f"/api/v1/devices/{data['disabled_device']}/sensors/{data['disabled_sensor']}/disable", headers=admin_headers, json={"reason": "x"})
        for response in (disabled_device, disabled_sensor):
            assert response.status_code == 409
            assert response.json()["detail"]["code"] == "PROJECT_NOT_ACTIVE"

        wrong_project = await client.post(f"/api/v1/projects/{data['active_project']}/devices/{data['other_device']}/disable", headers=admin_headers, json={"reason": "x"})
        assert wrong_project.status_code == 404

        wrong_device = await client.post(f"/api/v1/devices/{data['active_device']}/sensors/{data['other_sensor']}/disable", headers=admin_headers, json={"reason": "x"})
        assert wrong_device.status_code == 404

        restored_device = await client.post(f"{device_url}/activate", headers=admin_headers)
        restored_sensor = await client.post(f"{sensor_url}/activate", headers=admin_headers)
        assert restored_device.status_code == 204
        assert restored_sensor.status_code == 204

    async with AsyncSessionLocal() as db:
        assert (await db.get(Device, data["active_device"])).is_enabled is True
        assert (await db.get(Sensor, data["active_sensor"])).is_enabled is True


@pytest.mark.asyncio
async def test_user_overview_and_monitoring_are_project_scoped(visibility_data) -> None:
    data = visibility_data
    admin_headers = auth_header(data["admin_id"], data["admin_version"], "ADMIN")
    owner_headers = auth_header(data["owner_id"], data["owner_version"], "OWNER")
    viewer_headers = auth_header(data["viewer_id"], data["viewer_version"], "VIEWER")
    transport = httpx.ASGITransport(app=app)

    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        viewer_overview = await client.get("/api/v1/overview", headers=viewer_headers)
        assert viewer_overview.status_code == 200
        viewer_payload = viewer_overview.json()
        assert viewer_payload["summary"]["total_projects"] == 1
        assert {project["id"] for project in viewer_payload["projects"]} == {data["active_project"]}
        assert viewer_payload["projects"][0]["access_role"] == "VIEWER"

        viewer_monitoring = await client.get("/api/v1/monitoring/projects", headers=viewer_headers)
        assert viewer_monitoring.status_code == 200
        assert {project["id"] for project in viewer_monitoring.json()["items"]} == {data["active_project"]}

        owner_overview = await client.get("/api/v1/overview", headers=owner_headers)
        assert owner_overview.status_code == 200
        owner_ids = {project["id"] for project in owner_overview.json()["projects"]}
        assert data["active_project"] in owner_ids
        assert data["project_ids"][1] in owner_ids
        assert data["disabled_project"] not in owner_ids
        assert all(project["access_role"] == "OWNER" for project in owner_overview.json()["projects"])

@pytest.mark.asyncio
async def test_project_device_config_export_is_admin_only_and_project_scoped(
    visibility_data,
) -> None:
    data = visibility_data
    admin_headers = auth_header(data["admin_id"], data["admin_version"], "ADMIN")
    owner_headers = auth_header(data["owner_id"], data["owner_version"], "OWNER")
    viewer_headers = auth_header(data["viewer_id"], data["viewer_version"], "VIEWER")
    export_url = f"/api/v1/projects/{data['active_project']}/device-config"

    async with AsyncSessionLocal() as db:
        device = await db.get(Device, data["active_device"])
        sensor = await db.get(Sensor, data["active_sensor"])
        assert device is not None
        assert sensor is not None
        device.is_enabled = False
        sensor.is_enabled = False
        await db.commit()

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        for headers in (owner_headers, viewer_headers):
            assert (await client.get(export_url, headers=headers)).status_code == 403

        missing = await client.get(
            "/api/v1/projects/999999999/device-config",
            headers=admin_headers,
        )
        assert missing.status_code == 404

        response = await client.get(export_url, headers=admin_headers)
        assert response.status_code == 200
        payload = response.json()

    assert payload["project"]["id"] == data["active_project"]
    assert payload["mqtt"]["host"].lower() not in {
        "localhost",
        "127.0.0.1",
        "::1",
        "mqtt",
        "mosquitto",
    }
    assert payload["mqtt"] == {
        "host": payload["mqtt"]["host"],
        "port": 1883,
        "authentication": False,
        "tls": False,
    }

    exported_device_ids = {item["id"] for item in payload["devices"]}
    assert data["active_device"] in exported_device_ids
    assert data["other_device"] not in exported_device_ids
    exported_device = next(
        item for item in payload["devices"] if item["id"] == data["active_device"]
    )
    assert exported_device["is_enabled"] is False
    assert {item["id"] for item in exported_device["sensors"]} == {
        data["active_sensor"]
    }
    assert exported_device["sensors"][0]["is_enabled"] is False
    assert payload["summary"] == {
        "device_count": 1,
        "enabled_device_count": 0,
        "disabled_device_count": 1,
        "sensor_count": 1,
        "enabled_sensor_count": 0,
        "disabled_sensor_count": 1,
        "actuator_count": 0,
        "enabled_actuator_count": 0,
        "feedback_count": 0,
    }

    serialized = str(payload).lower()
    for secret_field in (
        "password",
        "password_hash",
        "jwt",
        "private_key",
        "certificate",
        "credential",
        "secret",
        "device_template_id",
        "sensor_model_id",
    ):
        assert secret_field not in serialized
