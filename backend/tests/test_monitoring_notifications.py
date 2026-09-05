import httpx
import pytest
from sqlalchemy import delete
from test_visibility_authorization import visibility_data  # noqa: F401

from app.core.security import create_access_token
from app.db.session import AsyncSessionLocal
from app.main import app
from app.models.alert import SensorAlert
from app.models.project_settings import (
    ProjectNotificationRecipient,
    ProjectNotificationRiskPolicy,
    ProjectNotificationSettings,
    ProjectPublicSettings,
)
from app.services.project_notification_service import dispatch_alert_transition
from app.services.telegram_notifier import TelegramDeliveryResult


def auth_header(user_id: int, token_version: int, role: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {create_access_token(str(user_id), {'role': role, 'token_version': token_version})}"}


@pytest.mark.asyncio
async def test_public_monitoring_disabled_then_enabled_is_sanitized_and_accepts_12h(visibility_data, monkeypatch) -> None:
    from app.core.config import settings

    data = visibility_data
    monkeypatch.setattr(settings, "public_monitoring_project_id", data["active_project"])
    owner_headers = auth_header(data["owner_id"], data["owner_version"], "OWNER")
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        public_url = "/api/v1/public-monitoring/overview"
        assert (await client.get(public_url)).status_code == 404
        saved = await client.put(
            f"/api/v1/projects/{data['active_project']}/public-settings",
            headers=owner_headers,
            json={"enabled": True},
        )
        assert saved.status_code == 200
        assert saved.json() == {"enabled": True, "remote_monitoring_available": True}
        response = await client.get(public_url)
        assert response.status_code == 200
        payload = response.json()
        serialized = str(payload).lower()
        assert "mqtt" not in serialized
        assert "telegram_chat_id" not in serialized
        assert "owner_user_id" not in serialized
        series = await client.get("/api/v1/public-monitoring/telemetry-series", params={"range": "12h"})
        assert series.status_code == 200
        assert series.json()["resolution"] == "10m"
        assert (await client.get("/api/v1/public/projects/obsolete/overview")).status_code == 404
        await client.put(
            f"/api/v1/projects/{data['active_project']}/public-settings",
            headers=owner_headers,
            json={"enabled": False},
        )
        assert (await client.get(public_url)).status_code == 404


@pytest.mark.asyncio
async def test_notification_recipient_crud_duplicate_and_project_scope(visibility_data) -> None:
    data = visibility_data
    owner_headers = auth_header(data["owner_id"], data["owner_version"], "OWNER")
    viewer_headers = auth_header(data["viewer_id"], data["viewer_version"], "VIEWER")
    base = f"/api/v1/projects/{data['active_project']}"
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        settings = await client.get(f"{base}/notification-settings", headers=owner_headers)
        assert settings.status_code == 200
        assert "telegram_bot_token" not in settings.text
        assert (await client.get(f"{base}/notification-settings", headers=viewer_headers)).status_code == 403
        policy_payload = {
            "telegram_enabled": True,
            "notify_alert_opened": True,
            "notify_alert_escalated": True,
            "notify_alert_reminder": False,
            "reminder_interval_minutes": None,
            "notify_alert_recovered": True,
            "notify_alert_resolved": True,
            "minimum_business_risk_level": "LOW",
            "risk_extreme_enabled": True,
            "risk_very_high_enabled": False,
            "risk_high_enabled": True,
            "risk_medium_enabled": False,
            "risk_low_medium_enabled": False,
            "risk_low_enabled": True,
            "risk_policies": [
                {"risk_level": level, "telegram_enabled": index < 4, "notify_on_open": True, "notify_on_escalation": True, "notify_on_recovery": True, "notify_on_resolved": True, "reminder_enabled": index < 3, "initial_reminder_seconds": 300, "repeat_interval_seconds": 600, "max_reminders": 4 if index < 3 else 0, "stop_reminders_on_ack": True}
                for index, level in enumerate(("EXTREME", "VERY_HIGH", "HIGH", "MEDIUM", "LOW_MEDIUM", "LOW"))
            ],
        }
        saved_policy = await client.put(f"{base}/notification-settings", headers=owner_headers, json=policy_payload)
        assert saved_policy.status_code == 200, saved_policy.text
        assert {field: saved_policy.json()[field] for field in policy_payload} == policy_payload
        reloaded_policy = await client.get(f"{base}/notification-settings", headers=owner_headers)
        assert {field: reloaded_policy.json()[field] for field in policy_payload} == policy_payload
        assert (await client.put(f"{base}/notification-settings", headers=viewer_headers, json=policy_payload)).status_code == 403
        created = await client.post(f"{base}/notification-recipients", headers=owner_headers, json={"name": "Nhóm vận hành", "telegram_chat_id": "-1001234567890"})
        assert created.status_code == 201
        recipient_id = created.json()["id"]
        duplicate = await client.post(f"{base}/notification-recipients", headers=owner_headers, json={"name": "Trùng", "telegram_chat_id": " -1001234567890 "})
        assert duplicate.status_code == 409
        changed = await client.patch(f"{base}/notification-recipients/{recipient_id}", headers=owner_headers, json={"enabled": False})
        assert changed.status_code == 200 and changed.json()["enabled"] is False
        wrong_project = await client.patch(f"/api/v1/projects/{data['project_ids'][1]}/notification-recipients/{recipient_id}", headers=owner_headers, json={"enabled": True})
        assert wrong_project.status_code == 404
        assert (await client.delete(f"{base}/notification-recipients/{recipient_id}", headers=owner_headers)).status_code == 204
    async with AsyncSessionLocal() as db:
        await db.execute(delete(ProjectNotificationRiskPolicy).where(ProjectNotificationRiskPolicy.project_id == data["active_project"]))
        await db.execute(delete(ProjectNotificationSettings).where(ProjectNotificationSettings.project_id == data["active_project"]))
        await db.commit()


class FakeNotifier:
    configured = True

    def __init__(self) -> None:
        self.calls: list[str] = []

    async def send_message(self, chat_id: str, text: str) -> TelegramDeliveryResult:
        self.calls.append(chat_id)
        if chat_id == "B":
            return TelegramDeliveryResult(False, 400, "BAD_REQUEST")
        return TelegramDeliveryResult(True, 200)


@pytest.mark.asyncio
async def test_alert_delivery_calls_all_enabled_recipients_and_isolates_failure(visibility_data) -> None:
    data = visibility_data
    notifier = FakeNotifier()
    async with AsyncSessionLocal() as db:
        settings = ProjectNotificationSettings(project_id=data["active_project"], telegram_enabled=True)
        recipients = [ProjectNotificationRecipient(project_id=data["active_project"], name=name, telegram_chat_id=name, enabled=name != "DISABLED") for name in ("A", "B", "C", "DISABLED")]
        db.add_all([settings, *recipients])
        alert = await db.get(SensorAlert, -1)
        assert alert is None
        from datetime import UTC, datetime

        from app.core.enums import AlertSeverity, AlertStatus, AlertType
        alert = SensorAlert(sensor_id=data["active_sensor"], alert_type=AlertType.ABOVE_UPPER_THRESHOLD, severity=AlertSeverity.WARNING, status=AlertStatus.OPEN, message="pH vượt ngưỡng", trigger_value=9.1, started_at=datetime.now(UTC))
        db.add(alert)
        await db.commit()
        await dispatch_alert_transition(db, alert_id=alert.id, transition="OPENED", notifier=notifier)
        assert notifier.calls == ["A", "B", "C"]
        await db.delete(alert)
        await db.execute(delete(ProjectNotificationRecipient).where(ProjectNotificationRecipient.project_id == data["active_project"]))
        await db.execute(delete(ProjectNotificationSettings).where(ProjectNotificationSettings.project_id == data["active_project"]))
        await db.execute(delete(ProjectPublicSettings).where(ProjectPublicSettings.project_id == data["active_project"]))
        await db.commit()


@pytest.mark.asyncio
async def test_threshold_alert_normalization_does_not_resolve_or_emit_transition(visibility_data) -> None:
    from datetime import UTC, datetime

    from app.models.sensor import Sensor
    from app.services.alert_service import evaluate_threshold

    data = visibility_data
    async with AsyncSessionLocal() as db:
        sensor = await db.get(Sensor, data["active_sensor"])
        assert sensor is not None
        sensor.warning_enabled = True
        sensor.lower_threshold = 6.0
        sensor.upper_threshold = 8.0
        sensor.alert_delay_seconds = 0
        first = await evaluate_threshold(db, sensor, 9.0, datetime.now(UTC))
        repeated = await evaluate_threshold(db, sensor, 9.2, datetime.now(UTC))
        normalized = await evaluate_threshold(db, sensor, 7.0, datetime.now(UTC))
        repeated_normal = await evaluate_threshold(db, sensor, 7.1, datetime.now(UTC))
        assert [transition for _, transition in first] == ["OPENED"]
        assert [transition for _, transition in repeated] == ["ABNORMAL_READING"]
        assert normalized == []
        assert repeated_normal == []
        alert = first[0][0]
        assert alert.status == "OPEN"
        assert alert.condition_active is False
        assert alert.normalized_at is not None
        assert alert.resolved_at is None
        assert alert.resolved_by_user_id is None
        assert alert.occurrence_count == 2
        await db.rollback()
