import asyncio
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
import httpx
from sqlalchemy import delete, func, select
from sqlalchemy.exc import IntegrityError

from app.core.enums import DeviceStatus, ProjectStatus, UserRole, UserStatus
from app.core.security import create_access_token, hash_password
from app.db.session import AsyncSessionLocal
from app.main import app
from app.models.actuator import Actuator
from app.models.actuator_model import ActuatorModel
from app.models.device import Device
from app.models.operational_alert import AlertRule, AlertRuleActuatorModelProfile, AlertRuleProfile, AlertRuleRevision, ActuatorFeedbackBinding, NotificationDelivery, NotificationOutbox, OperationalIncident
from app.models.project import Project
from app.models.project_settings import ProjectNotificationRecipient, ProjectNotificationSettings
from app.models.sensor import Sensor
from app.models.sensor_model import SensorModel
from app.models.telemetry import TelemetryReading
from app.models.user import User
from app.schemas.telemetry import DeviceReadingInput, DeviceTelemetryInput
from app.services.notification_outbox_service import process_notification_outbox
from app.services.telegram_notifier import TelegramDeliveryResult
from app.services.telemetry_service import ingest_telemetry


class RecordingNotifier:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str]] = []

    async def send_message(self, chat_id: str, text: str) -> TelegramDeliveryResult:
        self.calls.append((chat_id, text))
        return TelegramDeliveryResult(True, status_code=200)


class FailOnceNotifier(RecordingNotifier):
    async def send_message(self, chat_id: str, text: str) -> TelegramDeliveryResult:
        self.calls.append((chat_id, text))
        return TelegramDeliveryResult(len(self.calls) > 1, error_category="TIMEOUT" if len(self.calls) == 1 else None)


@pytest.mark.asyncio
async def test_active_incident_partial_unique_index_handles_concurrent_writers() -> None:
    context_key = f"concurrency:{uuid4().hex}"
    now = datetime.now(UTC)
    async with AsyncSessionLocal() as db:
        project = await db.scalar(select(Project).where(Project.code == "CODEX-TEST-RUNTIME"))
        assert project is not None
        rule = await db.scalar(select(AlertRule).where(AlertRule.code == "TDS_LOW"))
        assert rule and rule.current_revision_id
        rule_id, revision_id, project_id = rule.id, rule.current_revision_id, project.id

    ready = asyncio.Event()
    waiting = 0
    lock = asyncio.Lock()

    async def create_incident() -> str:
        nonlocal waiting
        async with AsyncSessionLocal() as db:
            db.add(OperationalIncident(project_id=project_id, rule_id=rule_id, rule_revision_id=revision_id, context_key=context_key, status="OPEN", technical_severity="WARNING", business_risk_level_snapshot="MEDIUM", started_at=now, opened_at=now, last_triggered_at=now, occurrence_count=1, trigger_snapshot={}))
            async with lock:
                waiting += 1
                if waiting == 2:
                    ready.set()
            await ready.wait()
            try:
                await db.commit()
                return "CREATED"
            except IntegrityError:
                await db.rollback()
                return "CONFLICT"

    assert sorted(await asyncio.gather(create_incident(), create_incident())) == ["CONFLICT", "CREATED"]
    async with AsyncSessionLocal() as db:
        assert await db.scalar(select(func.count(OperationalIncident.id)).where(OperationalIncident.rule_id == rule_id, OperationalIncident.context_key == context_key)) == 1
        await db.execute(delete(OperationalIncident).where(OperationalIncident.rule_id == rule_id, OperationalIncident.context_key == context_key))
        await db.commit()


@pytest.mark.asyncio
async def test_current_telemetry_at_1hz_creates_one_incident_and_one_open_delivery() -> None:
    suffix = uuid4().hex[:8].upper()
    ids: dict[str, int] = {}
    base = datetime.now(UTC) - timedelta(minutes=2)
    async with AsyncSessionLocal() as db:
        project = await db.scalar(select(Project).where(Project.code == "CODEX-TEST-RUNTIME"))
        assert project is not None
        device = await db.scalar(select(Device).where(Device.project_id == project.id))
        model = await db.scalar(select(SensorModel).where(SensorModel.code == "LOAD_CURRENT_A"))
        actuator_model = await db.scalar(select(ActuatorModel).where(ActuatorModel.is_active.is_(True)))
        assert device and model and actuator_model
        sensor = Sensor(device_id=device.id, sensor_model_id=model.id, code=f"HZ-CURRENT-{suffix}", name="Dòng điện 1 Hz", is_enabled=True)
        actuator = Actuator(device_id=device.id, actuator_model_id=actuator_model.id, sequence_number=980, code=f"HZ-ACT-{suffix}", name="Bơm 1 Hz", is_enabled=True, desired_state=True, reported_state=True)
        rule = AlertRule(code=f"HZ_RULE_{suffix}", name="Bơm mất dòng 1 Hz", target_type="ACTUATOR", evaluator_type="ACTUATOR_FEEDBACK", is_enabled=True)
        db.add_all([sensor, actuator, rule])
        await db.flush()
        config = {"feedback_role": "RUNNING_CURRENT", "min_running_current_a": 0.3, "max_running_current_a": 2.0, "startup_grace_seconds": 0, "debounce_seconds": 1, "recovery_current_a": 0.4, "recovery_duration_seconds": 2}
        revision = AlertRuleRevision(rule_id=rule.id, revision=1, business_risk_level="EXTREME", condition_config=config, source_order=980, status="PUBLISHED", message_template="Bơm không có dòng", consequence="Mất tuần hoàn", recommended_action="Kiểm tra bơm")
        db.add(revision)
        await db.flush()
        rule.current_revision_id = revision.id
        profile = AlertRuleProfile(rule_id=rule.id, code=f"HZ_PROFILE_{suffix}", name="Hồ sơ bơm 1 Hz", config={}, is_enabled=True)
        db.add(profile)
        await db.flush()
        db.add_all([AlertRuleActuatorModelProfile(profile_id=profile.id, actuator_model_id=actuator_model.id), ActuatorFeedbackBinding(actuator_id=actuator.id, sensor_id=sensor.id, feedback_role="RUNNING_CURRENT", is_enabled=True)])
        settings = ProjectNotificationSettings(project_id=project.id, telegram_enabled=True, notify_alert_opened=True, minimum_business_risk_level="LOW")
        recipient = ProjectNotificationRecipient(project_id=project.id, name="Trực vận hành", telegram_chat_id=f"hz-{suffix}", enabled=True)
        db.add_all([settings, recipient])
        await db.commit()
        ids = {"project": project.id, "device": device.id, "sensor": sensor.id, "actuator": actuator.id, "rule": rule.id, "revision": revision.id, "profile": profile.id, "settings": settings.id, "recipient": recipient.id}

    try:
        for second in range(60):
            observed_at = base + timedelta(seconds=second)
            async with AsyncSessionLocal() as db:
                device = await db.get(Device, ids["device"])
                assert device is not None
                response = await ingest_telemetry(db, device=device, payload=DeviceTelemetryInput(sent_at=observed_at, readings=[DeviceReadingInput(sensor_code=f"HZ-CURRENT-{suffix}", value=0.0, recorded_at=observed_at)]), received_at=observed_at)
                assert response.accepted == 1

        async with AsyncSessionLocal() as db:
            incident = await db.scalar(select(OperationalIncident).where(OperationalIncident.rule_id == ids["rule"]))
            assert incident is not None
            assert incident.status == "OPEN"
            assert incident.occurrence_count == 60
            assert await db.scalar(select(func.count(NotificationOutbox.id)).where(NotificationOutbox.incident_id == incident.id)) == 1
            assert list((await db.scalars(select(NotificationOutbox.event_type).where(NotificationOutbox.incident_id == incident.id))).all()) == ["OPEN"]
            notifier = RecordingNotifier()
            assert await process_notification_outbox(db, notifier=notifier) == 1
            assert [chat_id for chat_id, _ in notifier.calls] == [f"hz-{suffix}"]
            assert await db.scalar(select(func.count(NotificationDelivery.id)).where(NotificationDelivery.incident_id == incident.id)) == 1
    finally:
        async with AsyncSessionLocal() as db:
            incident_ids = select(OperationalIncident.id).where(OperationalIncident.rule_id == ids["rule"])
            await db.execute(delete(NotificationDelivery).where(NotificationDelivery.incident_id.in_(incident_ids)))
            await db.execute(delete(NotificationOutbox).where(NotificationOutbox.incident_id.in_(incident_ids)))
            await db.execute(delete(OperationalIncident).where(OperationalIncident.rule_id == ids["rule"]))
            await db.execute(delete(ProjectNotificationRecipient).where(ProjectNotificationRecipient.id == ids["recipient"]))
            await db.execute(delete(ProjectNotificationSettings).where(ProjectNotificationSettings.id == ids["settings"]))
            await db.execute(delete(ActuatorFeedbackBinding).where(ActuatorFeedbackBinding.actuator_id == ids["actuator"]))
            await db.execute(delete(TelemetryReading).where(TelemetryReading.sensor_id == ids["sensor"]))
            await db.execute(delete(AlertRuleActuatorModelProfile).where(AlertRuleActuatorModelProfile.profile_id == ids["profile"]))
            await db.execute(delete(AlertRuleProfile).where(AlertRuleProfile.id == ids["profile"]))
            await db.execute(delete(Actuator).where(Actuator.id == ids["actuator"]))
            await db.execute(delete(Sensor).where(Sensor.id == ids["sensor"]))
            await db.execute(delete(AlertRuleRevision).where(AlertRuleRevision.id == ids["revision"]))
            await db.execute(delete(AlertRule).where(AlertRule.id == ids["rule"]))
            await db.commit()


@pytest.mark.asyncio
async def test_notification_delivery_and_history_are_isolated_between_projects() -> None:
    suffix = uuid4().hex[:8].lower()
    ids: dict[str, int] = {}
    now = datetime.now(UTC)
    async with AsyncSessionLocal() as db:
        owner_a = User(username=f"isolation-a-{suffix}", password_hash=hash_password("Isolation@123"), full_name="Quản lý A", email=f"isolation-a-{suffix}@example.test", phone_number=f"081{suffix[:7]}", system_role=UserRole.OWNER, status=UserStatus.ACTIVE, must_change_password=False)
        owner_b = User(username=f"isolation-b-{suffix}", password_hash=hash_password("Isolation@123"), full_name="Quản lý B", email=f"isolation-b-{suffix}@example.test", phone_number=f"082{suffix[:7]}", system_role=UserRole.OWNER, status=UserStatus.ACTIVE, must_change_password=False)
        db.add_all([owner_a, owner_b])
        await db.flush()
        project_a = Project(owner_user_id=owner_a.id, code=f"ISO-A-{suffix}", name="Dự án A", status=ProjectStatus.ACTIVE)
        project_b = Project(owner_user_id=owner_b.id, code=f"ISO-B-{suffix}", name="Dự án B", status=ProjectStatus.ACTIVE)
        db.add_all([project_a, project_b])
        await db.flush()
        device_a = Device(project_id=project_a.id, code=f"ISO-DEV-A-{suffix}", name="Thiết bị A", status=DeviceStatus.ONLINE, is_enabled=True)
        device_b = Device(project_id=project_b.id, code=f"ISO-DEV-B-{suffix}", name="Thiết bị B", status=DeviceStatus.ONLINE, is_enabled=True)
        db.add_all([device_a, device_b])
        await db.flush()
        rule = await db.scalar(select(AlertRule).where(AlertRule.code == "TDS_LOW"))
        assert rule and rule.current_revision_id
        revision = await db.get(AlertRuleRevision, rule.current_revision_id)
        assert revision and revision.status == "PUBLISHED"
        incident = OperationalIncident(project_id=project_a.id, rule_id=rule.id, rule_revision_id=revision.id, device_id=device_a.id, context_key=f"device:{device_a.id}", status="OPEN", technical_severity="WARNING", business_risk_level_snapshot=revision.business_risk_level, started_at=now, opened_at=now, last_triggered_at=now, occurrence_count=1, trigger_snapshot={"project_name": project_a.name, "project_code": project_a.code, "device_name": device_a.name, "sensor_name": "TDS", "rule_name": rule.name, "value": 80, "unit": "ppm", "operator": "LT", "threshold": 100, "quality": "VALID", "freshness": "FRESH", "recorded_at": now.isoformat(), "received_at": now.isoformat()})
        db.add(incident)
        await db.flush()
        outbox = NotificationOutbox(incident_id=incident.id, event_type="OPEN", idempotency_key=f"iso:{incident.id}:OPEN", payload_snapshot={**incident.trigger_snapshot, "incident_id": incident.id, "event_type": "OPEN", "business_risk_level": revision.business_risk_level, "technical_severity": "WARNING", "started_at": now.isoformat(), "duration_seconds": 0}, status="PENDING", available_at=now, attempt_count=0)
        settings_a = ProjectNotificationSettings(project_id=project_a.id, telegram_enabled=True, notify_alert_opened=True, minimum_business_risk_level="LOW")
        settings_b = ProjectNotificationSettings(project_id=project_b.id, telegram_enabled=True, notify_alert_opened=True, minimum_business_risk_level="LOW")
        recipient_a = ProjectNotificationRecipient(project_id=project_a.id, name="Người nhận A", telegram_chat_id=f"chat-a-{suffix}", enabled=True)
        recipient_b = ProjectNotificationRecipient(project_id=project_b.id, name="Người nhận B", telegram_chat_id=f"chat-b-{suffix}", enabled=True)
        db.add_all([outbox, settings_a, settings_b, recipient_a, recipient_b])
        await db.commit()
        ids = {"owner_a": owner_a.id, "owner_b": owner_b.id, "owner_b_version": owner_b.token_version, "project_a": project_a.id, "project_b": project_b.id, "device_a": device_a.id, "device_b": device_b.id, "incident": incident.id, "outbox": outbox.id, "recipient_a": recipient_a.id, "recipient_b": recipient_b.id, "settings_a": settings_a.id, "settings_b": settings_b.id}

    try:
        notifier = FailOnceNotifier()
        async with AsyncSessionLocal() as db:
            assert await process_notification_outbox(db, notifier=notifier) == 0
            outbox = await db.get(NotificationOutbox, ids["outbox"])
            assert outbox and outbox.status == "RETRYING"
            outbox.available_at = datetime.now(UTC) - timedelta(seconds=1)
            await db.commit()
            assert await process_notification_outbox(db, notifier=notifier) == 1
            deliveries = list((await db.scalars(select(NotificationDelivery).where(NotificationDelivery.outbox_id == ids["outbox"]))).all())
            assert len(deliveries) == 1
            assert deliveries[0].recipient_id == ids["recipient_a"]
        assert [chat_id for chat_id, _ in notifier.calls] == [f"chat-a-{suffix}", f"chat-a-{suffix}"]

        owner_b_token = create_access_token(str(ids["owner_b"]), {"role": "OWNER", "token_version": ids["owner_b_version"]})
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            headers = {"Authorization": f"Bearer {owner_b_token}"}
            assert (await client.get(f"/api/v1/projects/{ids['project_a']}/notification-history", headers=headers)).status_code == 404
            assert (await client.get(f"/api/v1/projects/{ids['project_a']}/operational-incidents", headers=headers)).status_code == 404
    finally:
        async with AsyncSessionLocal() as db:
            await db.execute(delete(NotificationDelivery).where(NotificationDelivery.outbox_id == ids["outbox"]))
            await db.execute(delete(NotificationOutbox).where(NotificationOutbox.id == ids["outbox"]))
            await db.execute(delete(OperationalIncident).where(OperationalIncident.id == ids["incident"]))
            await db.execute(delete(ProjectNotificationRecipient).where(ProjectNotificationRecipient.id.in_([ids["recipient_a"], ids["recipient_b"]])))
            await db.execute(delete(ProjectNotificationSettings).where(ProjectNotificationSettings.id.in_([ids["settings_a"], ids["settings_b"]])))
            await db.execute(delete(Device).where(Device.id.in_([ids["device_a"], ids["device_b"]])))
            await db.execute(delete(Project).where(Project.id.in_([ids["project_a"], ids["project_b"]])))
            await db.execute(delete(User).where(User.id.in_([ids["owner_a"], ids["owner_b"]])))
            await db.commit()


@pytest.mark.asyncio
async def test_medium_risk_project_policy_suppresses_telegram_without_suppressing_incident() -> None:
    suffix = uuid4().hex[:8].upper()
    now = datetime.now(UTC)
    async with AsyncSessionLocal() as db:
        owner = await db.scalar(select(User).where(User.system_role == UserRole.OWNER, User.is_deleted.is_(False)))
        rule = await db.scalar(select(AlertRule).where(AlertRule.code == "TDS_LOW"))
        assert owner and rule and rule.current_revision_id
        projects = [Project(owner_user_id=owner.id, code=f"RISK-{label}-{suffix}", name=f"Risk {label}", status=ProjectStatus.ACTIVE) for label in ("A", "B")]
        db.add_all(projects)
        await db.flush()
        devices = [Device(project_id=project.id, code=f"RISK-DEV-{index}-{suffix}", name=f"Thiết bị {index}", status=DeviceStatus.ONLINE, is_enabled=True) for index, project in enumerate(projects)]
        db.add_all(devices)
        await db.flush()
        incidents = [OperationalIncident(project_id=project.id, rule_id=rule.id, rule_revision_id=rule.current_revision_id, device_id=device.id, context_key=f"risk:{project.id}:{suffix}", status="OPEN", technical_severity="WARNING", business_risk_level_snapshot="MEDIUM", started_at=now, opened_at=now, last_triggered_at=now, occurrence_count=1, trigger_snapshot={"project_name": project.name, "project_code": project.code, "device_name": device.name, "rule_name": rule.name}) for project, device in zip(projects, devices, strict=True)]
        db.add_all(incidents)
        await db.flush()
        outboxes = [NotificationOutbox(incident_id=incident.id, event_type="OPEN", idempotency_key=f"risk:{incident.id}:OPEN", payload_snapshot={**incident.trigger_snapshot, "incident_id": incident.id, "event_type": "OPEN", "business_risk_level": "MEDIUM", "technical_severity": "WARNING", "started_at": now.isoformat()}, status="PENDING", available_at=now, attempt_count=0) for incident in incidents]
        settings_rows = [
            ProjectNotificationSettings(project_id=projects[0].id, telegram_enabled=True, notify_alert_opened=True, minimum_business_risk_level="LOW", risk_medium_enabled=False),
            ProjectNotificationSettings(project_id=projects[1].id, telegram_enabled=True, notify_alert_opened=True, minimum_business_risk_level="LOW", risk_medium_enabled=True),
        ]
        recipients = [ProjectNotificationRecipient(project_id=project.id, name=f"Người nhận {index}", telegram_chat_id=f"risk-chat-{index}-{suffix}", enabled=True) for index, project in enumerate(projects)]
        db.add_all([*outboxes, *settings_rows, *recipients])
        await db.commit()
        ids = {"projects": [item.id for item in projects], "devices": [item.id for item in devices], "incidents": [item.id for item in incidents], "outboxes": [item.id for item in outboxes], "settings": [item.id for item in settings_rows], "recipients": [item.id for item in recipients]}

    try:
        notifier = RecordingNotifier()
        async with AsyncSessionLocal() as db:
            assert await process_notification_outbox(db, notifier=notifier) == 2
            stored_incidents = list((await db.scalars(select(OperationalIncident).where(OperationalIncident.id.in_(ids["incidents"])))).all())
            assert {item.status for item in stored_incidents} == {"OPEN"}
            statuses = dict((await db.execute(select(NotificationOutbox.id, NotificationOutbox.status).where(NotificationOutbox.id.in_(ids["outboxes"])))).all())
            assert statuses[ids["outboxes"][0]] == "SKIPPED"
            assert statuses[ids["outboxes"][1]] == "PROCESSED"
            deliveries = list((await db.scalars(select(NotificationDelivery).where(NotificationDelivery.incident_id.in_(ids["incidents"])))).all())
            assert len(deliveries) == 2
            by_incident = {delivery.incident_id: delivery for delivery in deliveries}
            assert by_incident[ids["incidents"][0]].status == "SKIPPED"
            assert by_incident[ids["incidents"][0]].error_category == "POLICY_DISABLED"
            assert by_incident[ids["incidents"][1]].status == "SENT"
        assert [chat_id for chat_id, _ in notifier.calls] == [f"risk-chat-1-{suffix}"]
    finally:
        async with AsyncSessionLocal() as db:
            await db.execute(delete(NotificationDelivery).where(NotificationDelivery.incident_id.in_(ids["incidents"])))
            await db.execute(delete(NotificationOutbox).where(NotificationOutbox.id.in_(ids["outboxes"])))
            await db.execute(delete(OperationalIncident).where(OperationalIncident.id.in_(ids["incidents"])))
            await db.execute(delete(ProjectNotificationRecipient).where(ProjectNotificationRecipient.id.in_(ids["recipients"])))
            await db.execute(delete(ProjectNotificationSettings).where(ProjectNotificationSettings.id.in_(ids["settings"])))
            await db.execute(delete(Device).where(Device.id.in_(ids["devices"])))
            await db.execute(delete(Project).where(Project.id.in_(ids["projects"])))
            await db.commit()
