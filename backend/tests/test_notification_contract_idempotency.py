from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from pydantic import ValidationError
from sqlalchemy import delete, func, select

from app.db.session import AsyncSessionLocal
from app.models.device import Device
from app.models.operational_alert import (
    AlertRule,
    AlertRuleRevision,
    NotificationDelivery,
    NotificationOutbox,
    OperationalIncident,
)
from app.models.project import Project
from app.models.project_settings import (
    ProjectNotificationRecipient,
    ProjectNotificationRiskPolicy,
    ProjectNotificationSettings,
)
from app.models.sensor import Sensor
from app.models.sensor_model import SensorModel
from app.schemas.notifications import NotificationSettingsUpdate
from app.services.notification_outbox_service import (
    _payload_at_delivery,
    format_operational_message,
    process_notification_outbox,
)
from app.services.operational_incident_service import (
    _transition_sensor_incident,
    enqueue_incident_notification,
)
from app.services.telegram_notifier import TelegramDeliveryResult


def _settings_payload() -> dict:
    levels = ("EXTREME", "VERY_HIGH", "HIGH", "MEDIUM", "LOW_MEDIUM", "LOW")
    return {
        "telegram_enabled": True, "notify_alert_opened": True, "notify_alert_resolved": True,
        "risk_policies": [{
            "risk_level": level, "telegram_enabled": True, "notify_on_open": True,
            "notify_on_escalation": True, "notify_on_recovery": True, "notify_on_resolved": True,
            "reminder_enabled": False, "initial_reminder_seconds": 300,
            "repeat_interval_seconds": 600, "max_reminders": 0, "stop_reminders_on_ack": True,
        } for level in levels],
    }


def test_notification_settings_contract_accepts_six_risks_and_rejects_invalid_values() -> None:
    assert len(NotificationSettingsUpdate.model_validate(_settings_payload()).risk_policies) == 6
    invalid_risk = _settings_payload()
    invalid_risk["risk_policies"][0]["risk_level"] = "CRITICAL"
    with pytest.raises(ValidationError):
        NotificationSettingsUpdate.model_validate(invalid_risk)
    invalid_integer = _settings_payload()
    invalid_integer["risk_policies"][0]["initial_reminder_seconds"] = "abc"
    with pytest.raises(ValidationError):
        NotificationSettingsUpdate.model_validate(invalid_integer)


def test_operational_payload_uses_business_threshold_and_live_incident_duration() -> None:
    started = datetime.now(UTC) - timedelta(days=1, hours=20)
    incident = OperationalIncident(id=6, project_id=1, rule_id=1, rule_revision_id=1, context_key="sensor:1", status="OPEN", technical_severity="CRITICAL", business_risk_level_snapshot="VERY_HIGH", started_at=started, opened_at=started, last_triggered_at=started, occurrence_count=120, trigger_snapshot={})
    outbox = NotificationOutbox(id=10, incident_id=6, event_type="OPEN", idempotency_key="incident:6:OPEN", payload_snapshot={"project_name": "Dự án cá trê", "project_code": "TB-0015", "device_name": "Thiết bị môi trường", "device_code": "ENV-01", "sensor_name": "Cảm biến pH", "sensor_code": "ENV-01-PH", "rule_name": "pH nước", "value": 2, "unit": "pH", "operator": "OUTSIDE", "lower": 6.0, "upper": 8.0, "quality": "VALID", "freshness": "FRESH", "message": "pH bất thường"})
    payload = _payload_at_delivery(outbox, incident, datetime.now(UTC))
    message = format_operational_message(payload)
    assert "Ngưỡng cảnh báo: < 6 hoặc > 8 pH" in message
    assert "Mã cảm biến: ENV-01-PH" in message
    assert "Bắt đầu: —" not in message and "Đã kéo dài: 1 ngày 20 giờ" in message
    assert "CRITICAL" not in message and "WARNING" not in message


@pytest.mark.asyncio
async def test_120_abnormal_samples_create_one_incident_and_one_open_outbox() -> None:
    suffix = uuid4().hex[:8].upper()
    now = datetime.now(UTC)
    async with AsyncSessionLocal() as db:
        project = await db.scalar(select(Project).where(Project.code == "CODEX-TEST-RUNTIME"))
        assert project is not None
        device = await db.scalar(select(Device).where(Device.project_id == project.id))
        assert device
        model = SensorModel(code=f"PH-{suffix}", name="pH test", unit="pH", is_active=True)
        db.add(model)
        await db.flush()
        sensor = Sensor(device_id=device.id, sensor_model_id=model.id, code=f"PH-{suffix}", name="pH test", is_enabled=True)
        rule = AlertRule(code=f"PH_REPEAT_{suffix}", name="pH nước", target_type="SENSOR", evaluator_type="RANGE_BANDS", is_enabled=True)
        db.add_all([sensor, rule])
        await db.flush()
        revision = AlertRuleRevision(rule_id=rule.id, revision=1, business_risk_level="VERY_HIGH", condition_config={"bands": [{"lower": 6.0, "upper": 8.0, "outside": True}]}, source_order=999, status="PUBLISHED")
        db.add(revision)
        await db.flush()
        rule.current_revision_id = revision.id
        snapshot = {"rule_name": "pH nước", "value": 2, "unit": "pH", "operator": "OUTSIDE", "lower": 6.0, "upper": 8.0}
        incident = None
        for index in range(120):
            incident = await _transition_sensor_incident(db, project=project, device=device, sensor=sensor, rule=rule, revision=revision, config={}, active=True, severity="CRITICAL" if index else "WARNING", observed_at=now + timedelta(seconds=index), snapshot=snapshot)
        assert incident is not None
        await db.commit()
        assert incident.occurrence_count == 120
        assert int(await db.scalar(select(func.count(OperationalIncident.id)).where(OperationalIncident.rule_id == rule.id)) or 0) == 1
        assert int(await db.scalar(select(func.count(NotificationOutbox.id)).where(NotificationOutbox.incident_id == incident.id, NotificationOutbox.event_type == "OPEN")) or 0) == 1
        settings = await db.scalar(select(ProjectNotificationSettings).where(ProjectNotificationSettings.project_id == project.id))
        if settings is None:
            settings = ProjectNotificationSettings(project_id=project.id)
        settings.enabled = True
        settings.telegram_enabled = True
        settings.notify_alert_opened = True
        policy = ProjectNotificationRiskPolicy(project_id=project.id, risk_level="VERY_HIGH", telegram_enabled=True, notify_on_open=True, notify_on_escalation=True, notify_on_recovery=True, notify_on_resolved=True, reminder_enabled=False, initial_reminder_seconds=900, repeat_interval_seconds=1800, max_reminders=0, stop_reminders_on_ack=True)
        recipient = ProjectNotificationRecipient(project_id=project.id, name="Kiểm thử", telegram_chat_id=f"chat-{suffix}", enabled=True)
        db.add_all([settings, policy, recipient])
        await db.commit()

        class CountingNotifier:
            def __init__(self) -> None:
                self.calls = 0

            async def send_message(self, chat_id: str, text: str) -> TelegramDeliveryResult:
                self.calls += 1
                assert "CẢNH BÁO RẤT CAO" in text
                return TelegramDeliveryResult(True, 200)

        notifier = CountingNotifier()
        assert await process_notification_outbox(db, notifier=notifier) == 1
        assert notifier.calls == 1
        await enqueue_incident_notification(db, incident, "OPEN")
        await db.commit()
        assert int(await db.scalar(select(func.count(NotificationOutbox.id)).where(NotificationOutbox.incident_id == incident.id, NotificationOutbox.event_type == "OPEN")) or 0) == 1
        assert await process_notification_outbox(db, notifier=notifier) == 0
        assert notifier.calls == 1
        incident_id, sensor_id, model_id, rule_id = incident.id, sensor.id, model.id, rule.id
    async with AsyncSessionLocal() as db:
        await db.execute(delete(NotificationDelivery).where(NotificationDelivery.incident_id == incident_id))
        await db.execute(delete(NotificationOutbox).where(NotificationOutbox.incident_id == incident_id))
        await db.execute(delete(OperationalIncident).where(OperationalIncident.id == incident_id))
        await db.execute(delete(ProjectNotificationRecipient).where(ProjectNotificationRecipient.project_id == project.id))
        await db.execute(delete(ProjectNotificationRiskPolicy).where(ProjectNotificationRiskPolicy.project_id == project.id))
        await db.execute(delete(ProjectNotificationSettings).where(ProjectNotificationSettings.project_id == project.id))
        await db.execute(delete(Sensor).where(Sensor.id == sensor_id))
        await db.execute(delete(SensorModel).where(SensorModel.id == model_id))
        await db.execute(delete(AlertRuleRevision).where(AlertRuleRevision.rule_id == rule_id))
        await db.execute(delete(AlertRule).where(AlertRule.id == rule_id))
        await db.commit()
