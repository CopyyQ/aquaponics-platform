import httpx
import pytest
from sqlalchemy import delete, func, select

from app.core.enums import DeviceStatus, ProjectStatus
from app.db.session import AsyncSessionLocal
from app.main import app
from app.models.audit import AuditLog
from app.models.device import Device
from app.models.project import Project
from app.models.project_settings import ProjectNotificationRecipient, ProjectNotificationSettings
from app.models.sensor import Sensor
from app.models.user import User
from app.services.project_activity_service import dispatch_project_activity, record_project_activity
from app.services.telegram_notifier import TelegramDeliveryResult
from test_visibility_authorization import auth_header, visibility_data  # noqa: F401


@pytest.mark.asyncio
async def test_admin_list_and_detail_include_disabled_project(visibility_data) -> None:
    data = visibility_data
    admin_headers = auth_header(data["admin_id"], data["admin_version"], "ADMIN")
    owner_headers = auth_header(data["owner_id"], data["owner_version"], "OWNER")
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        admin_projects = await client.get("/api/v1/projects", headers=admin_headers)
        assert admin_projects.status_code == 200
        assert data["disabled_project"] in {item["id"] for item in admin_projects.json()}
        owner_projects = await client.get("/api/v1/projects", headers=owner_headers)
        assert data["disabled_project"] not in {item["id"] for item in owner_projects.json()}
        assert (await client.get(f"/api/v1/projects/{data['disabled_project']}", headers=admin_headers)).status_code == 200
        assert (await client.get(f"/api/v1/projects/{data['disabled_project']}/overview", headers=admin_headers)).status_code == 200


@pytest.mark.asyncio
async def test_disable_persists_once_preserves_children_and_reactivate_does_not_fake_online(visibility_data) -> None:
    data = visibility_data
    headers = auth_header(data["admin_id"], data["admin_version"], "ADMIN")
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        disabled = await client.post(f"/api/v1/projects/{data['active_project']}/disable", headers=headers, json={"reason": "Bảo trì hotfix"})
        assert disabled.status_code == 200
        assert disabled.json()["status"] == "DISABLED"
        assert (await client.get(f"/api/v1/projects/{data['active_project']}", headers=headers)).status_code == 200
        listed = await client.get(f"/api/v1/admin/users/{data['owner_id']}/projects", headers=headers)
        item = next(project for project in listed.json()["items"] if project["id"] == data["active_project"])
        assert item["status"] == "DISABLED"
        activated = await client.post(f"/api/v1/projects/{data['active_project']}/activate", headers=headers)
        assert activated.status_code == 200
        assert activated.json()["status"] == "ACTIVE"

    async with AsyncSessionLocal() as db:
        assert await db.scalar(select(func.count(Device.id)).where(Device.project_id == data["active_project"])) == 1
        assert await db.scalar(select(func.count(Sensor.id)).join(Device).where(Device.project_id == data["active_project"])) == 1
        actions = list((await db.scalars(select(AuditLog.action).where(AuditLog.project_id == data["active_project"], AuditLog.action.in_(["PROJECT_DISABLED", "PROJECT_ENABLED"])))).all())
        assert actions.count("PROJECT_DISABLED") == 1
        assert actions.count("PROJECT_ENABLED") == 1
        project = await db.get(Project, data["active_project"])
        device = await db.get(Device, data["active_device"])
        assert project is not None and project.status == ProjectStatus.ACTIVE
        assert device is not None and device.status == DeviceStatus.OFFLINE


class FakeActivityNotifier:
    configured = True

    def __init__(self) -> None:
        self.calls: list[tuple[str, str]] = []

    async def send_message(self, chat_id: str, text: str) -> TelegramDeliveryResult:
        self.calls.append((chat_id, text))
        if chat_id == "B":
            return TelegramDeliveryResult(False, 400, "BAD_REQUEST")
        return TelegramDeliveryResult(True, 200)


@pytest.mark.asyncio
async def test_project_activity_dispatches_all_enabled_recipients_with_actor_and_no_secret(visibility_data) -> None:
    data = visibility_data
    notifier = FakeActivityNotifier()
    async with AsyncSessionLocal() as db:
        actor = await db.get(User, data["admin_id"])
        assert actor is not None
        db.add(ProjectNotificationSettings(project_id=data["disabled_project"], telegram_enabled=True))
        db.add_all([
            ProjectNotificationRecipient(project_id=data["disabled_project"], name="A", telegram_chat_id="A", enabled=True),
            ProjectNotificationRecipient(project_id=data["disabled_project"], name="B", telegram_chat_id="B", enabled=True),
            ProjectNotificationRecipient(project_id=data["disabled_project"], name="C", telegram_chat_id="C", enabled=False),
        ])
        activity = await record_project_activity(db, project_id=data["disabled_project"], actor=actor, action="PROJECT_DISABLED", entity_type="PROJECT", entity_id=data["disabled_project"], entity_name="Visibility Disabled Project", changes={"status": {"before": "ACTIVE", "after": "DISABLED"}, "telegram_bot_token": "must-not-leak"})
        await db.commit()
        await dispatch_project_activity(db, activity_id=activity.id, notifier=notifier)  # type: ignore[arg-type]
        assert [chat_id for chat_id, _ in notifier.calls] == ["A", "B"]
        assert all(actor.full_name in message for _, message in notifier.calls)
        assert all("must-not-leak" not in message and "telegram_bot_token" not in message for _, message in notifier.calls)
        await db.execute(delete(ProjectNotificationRecipient).where(ProjectNotificationRecipient.project_id == data["disabled_project"]))
        await db.execute(delete(ProjectNotificationSettings).where(ProjectNotificationSettings.project_id == data["disabled_project"]))
        await db.execute(delete(AuditLog).where(AuditLog.id == activity.id))
        await db.commit()


@pytest.mark.asyncio
async def test_project_reads_do_not_create_activity(visibility_data) -> None:
    data = visibility_data
    headers = auth_header(data["admin_id"], data["admin_version"], "ADMIN")
    async with AsyncSessionLocal() as db:
        before = int(await db.scalar(select(func.count(AuditLog.id)).where(AuditLog.project_id == data["active_project"])) or 0)
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        assert (await client.get(f"/api/v1/projects/{data['active_project']}", headers=headers)).status_code == 200
        assert (await client.get(f"/api/v1/projects/{data['active_project']}/monitoring/latest", headers=headers)).status_code == 200
        assert (await client.get(f"/api/v1/projects/{data['active_project']}/activities", headers=headers)).status_code == 200
    async with AsyncSessionLocal() as db:
        after = int(await db.scalar(select(func.count(AuditLog.id)).where(AuditLog.project_id == data["active_project"])) or 0)
    assert after == before


@pytest.mark.asyncio
async def test_device_update_creates_exactly_one_project_activity(visibility_data) -> None:
    data = visibility_data
    headers = auth_header(data["admin_id"], data["admin_version"], "ADMIN")
    async with AsyncSessionLocal() as db:
        device = await db.get(Device, data["active_device"])
        assert device is not None
        original_name = device.name
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.patch(
            f"/api/v1/projects/{data['active_project']}/devices/{data['active_device']}",
            headers=headers,
            json={"name": f"{original_name} updated"},
        )
        assert response.status_code == 200
    async with AsyncSessionLocal() as db:
        activities = list((await db.scalars(select(AuditLog).where(AuditLog.project_id == data["active_project"], AuditLog.action == "DEVICE_UPDATED", AuditLog.entity_id == data["active_device"]))).all())
        assert len(activities) == 1
        assert activities[0].user_id == data["admin_id"]
        assert "password" not in str(activities[0].new_data).lower()
        device = await db.get(Device, data["active_device"])
        assert device is not None
        device.name = original_name
        await db.delete(activities[0])
        await db.commit()
