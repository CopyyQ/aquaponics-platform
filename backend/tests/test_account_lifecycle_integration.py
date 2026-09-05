import json
from datetime import UTC, datetime
from uuid import uuid4

import httpx
import pytest
from sqlalchemy import delete, select

from app.db.session import AsyncSessionLocal, engine
from app.core.enums import AlertSeverity, AlertStatus, AlertType, DeviceStatus, UserRole, UserStatus
from app.core.security import create_access_token, hash_password
from app.main import app
from app.models.alert import SensorAlert
from app.models.device import Device
from app.models.project import Project
from app.models.project import ProjectMember
from app.models.sensor import Sensor, SensorModel
from app.models.telemetry import TelemetryReading
from app.models.user import User
from app.mqtt.handlers import handle_telemetry


@pytest.fixture
async def lifecycle_data():
    suffix = uuid4().hex[:10].upper()
    async with AsyncSessionLocal() as db:
        admin = await db.scalar(select(User).where(User.system_role == UserRole.ADMIN, User.status == UserStatus.ACTIVE))
        model = await db.scalar(select(SensorModel).where(SensorModel.is_deleted.is_(False)))
        if admin is None or model is None:
            pytest.skip("Cần seed Admin và SensorModel để chạy integration test")
        owner = User(
            username=f"it-owner-{suffix.lower()}",
            password_hash=hash_password("Integration@123"),
            full_name="Integration Owner",
            email=f"it-owner-{suffix.lower()}@example.test",
            phone_number=f"09{suffix[:8]}",
            system_role=UserRole.OWNER,
            status=UserStatus.ACTIVE,
            must_change_password=False,
        )
        viewer = User(
            username=f"it-viewer-{suffix.lower()}",
            password_hash=hash_password("Integration@123"),
            full_name="Integration Viewer",
            email=f"it-viewer-{suffix.lower()}@example.test",
            phone_number=f"08{suffix[:8]}",
            system_role=UserRole.VIEWER,
            status=UserStatus.ACTIVE,
            must_change_password=False,
        )
        db.add_all([owner, viewer])
        await db.flush()
        project = Project(owner_user_id=owner.id, code=f"IT-{suffix}", name="Integration Project", status="ACTIVE")
        db.add(project)
        await db.flush()
        member = ProjectMember(project_id=project.id, user_id=viewer.id, role="VIEWER", created_by=admin.id)
        device = Device(project_id=project.id, code=f"IT-DEVICE-{suffix}", name="Integration Device", status=DeviceStatus.WAITING_CONNECTION)
        db.add_all([member, device])
        await db.flush()
        sensor = Sensor(device_id=device.id, sensor_model_id=model.id, code=f"IT-SENSOR-{suffix}", name="Integration Sensor", lower_threshold=6.5, upper_threshold=8.5)
        db.add(sensor)
        await db.flush()
        alert = SensorAlert(
            sensor_id=sensor.id, alert_type=AlertType.ABOVE_UPPER_THRESHOLD,
            severity=AlertSeverity.CRITICAL, status=AlertStatus.OPEN,
            message="Integration alert", trigger_value=9.1, started_at=datetime.now(UTC),
        )
        db.add(alert)
        await db.commit()
        ids = {"admin": admin.id, "admin_version": admin.token_version, "owner": owner.id, "owner_username": owner.username, "viewer": viewer.id, "project": project.id, "device": device.id, "sensor": sensor.id, "alert": alert.id, "device_code": device.code}
    try:
        yield ids
    finally:
        async with AsyncSessionLocal() as db:
            await db.execute(delete(SensorAlert).where(SensorAlert.id == ids["alert"]))
            await db.execute(delete(TelemetryReading).where(TelemetryReading.sensor_id == ids["sensor"]))
            await db.execute(delete(Sensor).where(Sensor.id == ids["sensor"]))
            await db.execute(delete(Device).where(Device.id == ids["device"]))
            await db.execute(delete(ProjectMember).where(ProjectMember.project_id == ids["project"]))
            await db.execute(delete(Project).where(Project.id == ids["project"]))
            await db.execute(delete(User).where(User.id.in_([ids["owner"], ids["viewer"]])))
            await db.commit()
        await engine.dispose()


def token(user_id: int, version: int = 0, role: str = "OWNER") -> str:
    return create_access_token(str(user_id), {"role": role, "token_version": version})


@pytest.mark.asyncio
async def test_owner_disable_hides_operational_data_and_restore_reveals_it(lifecycle_data):
    data = lifecycle_data
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        owner_headers = {"Authorization": f"Bearer {token(data['owner'])}"}
        admin_headers = {"Authorization": f"Bearer {token(data['admin'], data['admin_version'], 'ADMIN')}"}
        assert (await client.get("/api/v1/projects", headers=owner_headers)).status_code == 200
        assert (await client.get(f"/api/v1/projects/{data['project']}", headers=owner_headers)).status_code == 200
        assert (await client.post(f"/api/v1/admin/users/{data['owner']}/disable", headers=admin_headers, json={"reason": "Tạm ngừng dịch vụ"})).status_code == 200
        login_blocked = await client.post("/api/v1/auth/login", json={"username": data["owner_username"], "password": "Integration@123"})
        assert login_blocked.status_code == 401
        assert login_blocked.json()["code"] == "ACCOUNT_DISABLED"
        inactive = await client.get("/api/v1/projects", headers=owner_headers)
        assert inactive.status_code == 401
        assert inactive.json()["code"] == "ACCOUNT_DISABLED"
        assert (await client.get(f"/api/v1/devices/{data['device']}", headers=owner_headers)).status_code == 401
        overview = await client.get("/api/v1/admin/overview", headers=admin_headers)
        assert data["project"] not in {item.get("project_id") for item in overview.json()["critical_issues"]}
        monitoring = await client.get("/api/v1/admin/monitoring/projects", headers=admin_headers)
        assert data["project"] not in {item["id"] for item in monitoring.json()["items"]}
        alerts = await client.get("/api/v1/admin/alerts", headers=admin_headers)
        assert data["alert"] not in {item["id"] for item in alerts.json()["items"]}
        async with AsyncSessionLocal() as db:
            before = await db.scalar(select(TelemetryReading.id).where(TelemetryReading.sensor_id == data["sensor"]))
            device = await db.get(Device, data["device"])
            previous_seen = device.last_seen_at
        await handle_telemetry(data["device_code"], json.dumps({"sent_at": "2026-07-21T03:00:00Z", "readings": [{"sensor_code": "missing", "value": 9.0, "recorded_at": "2026-07-21T03:00:00Z"}]}).encode())
        async with AsyncSessionLocal() as db:
            assert await db.scalar(select(TelemetryReading.id).where(TelemetryReading.sensor_id == data["sensor"])) == before
            assert (await db.get(Device, data["device"])).last_seen_at == previous_seen
        assert (await client.post(f"/api/v1/admin/users/{data['owner']}/restore", headers=admin_headers)).status_code == 200
        restored = await client.get("/api/v1/projects", headers={"Authorization": f"Bearer {token(data['owner'], version=2)}"})
        assert restored.status_code == 200


@pytest.mark.asyncio
async def test_viewer_scope_and_last_admin_guard(lifecycle_data):
    data = lifecycle_data
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        admin_headers = {"Authorization": f"Bearer {token(data['admin'], data['admin_version'], 'ADMIN')}"}
        viewer_headers = {"Authorization": f"Bearer {token(data['viewer'], role='VIEWER')}"}
        assert (await client.get(f"/api/v1/projects/{data['project']}", headers=viewer_headers)).status_code == 200
        await client.post(f"/api/v1/admin/users/{data['owner']}/disable", headers=admin_headers, json={"reason": "khóa kiểm thử"})
        assert (await client.get(f"/api/v1/projects/{data['project']}", headers=viewer_headers)).status_code == 404
        async with AsyncSessionLocal() as db:
            other_admin_ids = list((await db.scalars(select(User.id).where(User.system_role == UserRole.ADMIN, User.status == UserStatus.ACTIVE, User.id != data["admin"]))).all())
        try:
            for other_admin_id in other_admin_ids:
                assert (await client.post(f"/api/v1/admin/users/{other_admin_id}/disable", headers=admin_headers, json={"reason": "kiểm thử Admin cuối"})).status_code == 200
            last_admin = await client.post(f"/api/v1/admin/users/{data['admin']}/disable", headers=admin_headers, json={"reason": "không được phép"})
            assert last_admin.status_code == 409
        finally:
            for other_admin_id in other_admin_ids:
                await client.post(f"/api/v1/admin/users/{other_admin_id}/activate", headers=admin_headers, json={"reason": "khôi phục sau kiểm thử"})
