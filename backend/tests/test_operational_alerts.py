from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
import httpx
from fastapi import HTTPException
from sqlalchemy import delete, func, select

from app.api.v1.actuators import set_feedback_binding
from app.core.enums import DeviceStatus, ProjectStatus, UserRole
from app.core.security import create_access_token
from app.db.session import AsyncSessionLocal
from app.main import app
from app.models.actuator import Actuator
from app.models.actuator_model import ActuatorModel, ActuatorModelFeedbackDefinition
from app.models.device import Device
from app.models.operational_alert import ActuatorFeedbackBinding, AlertRule, AlertRuleRevision, NotificationDelivery, NotificationOutbox, OperationalIncident
from app.models.project import Project
from app.models.project_settings import ProjectNotificationRecipient, ProjectNotificationRiskPolicy, ProjectNotificationSettings
from app.models.sensor import Sensor
from app.models.sensor_model import SensorModel
from app.models.user import User
from app.schemas.operational_alert import FeedbackBindingCreate
from app.services.alert_evaluators import EVALUATOR_REGISTRY, validate_condition_config
from app.services.monitoring_service import _actuator_operational_conclusion, _actuator_sync, _electrical_threshold_status
from app.services.notification_outbox_service import enqueue_due_reminders, format_operational_message, process_notification_outbox
from app.services.operational_incident_service import _transition_incident, evaluate_operational_rules_for_sensor
from app.services.telegram_notifier import TelegramDeliveryResult


async def test_seed_contains_19_unique_global_rules() -> None:
    async with AsyncSessionLocal() as db:
        count = await db.scalar(select(func.count(AlertRule.id)))
        distinct_codes = await db.scalar(select(func.count(func.distinct(AlertRule.code))))
        revisions = await db.scalar(select(func.count(AlertRuleRevision.id)))
        canonical_feedback = await db.scalar(
            select(ActuatorModelFeedbackDefinition)
            .join(ActuatorModel, ActuatorModel.id == ActuatorModelFeedbackDefinition.actuator_model_id)
            .join(SensorModel, SensorModel.id == ActuatorModelFeedbackDefinition.sensor_model_id)
            .where(
                ActuatorModel.code == "FISH_TANK_PUMP",
                SensorModel.code == "LOAD_CURRENT_A",
                ActuatorModelFeedbackDefinition.feedback_role == "RUNNING_CURRENT",
                ActuatorModelFeedbackDefinition.value_key == "current_a",
                ActuatorModelFeedbackDefinition.unit == "A",
                ActuatorModelFeedbackDefinition.data_type == "FLOAT",
            )
        )
    assert count == 19
    assert distinct_codes == 19
    assert revisions == 19
    assert canonical_feedback is not None


@pytest.mark.asyncio
async def test_global_rule_revision_publish_retire_and_admin_authorization() -> None:
    suffix = uuid4().hex[:8].upper()
    async with AsyncSessionLocal() as db:
        admin = await db.scalar(select(User).where(User.system_role == UserRole.ADMIN, User.is_deleted.is_(False)))
        owner = await db.scalar(select(User).where(User.system_role == UserRole.OWNER, User.is_deleted.is_(False)))
        sensor_model = await db.scalar(select(SensorModel).where(SensorModel.is_active.is_(True), SensorModel.is_deleted.is_(False)))
        actuator_model = await db.scalar(select(ActuatorModel).where(ActuatorModel.is_active.is_(True), ActuatorModel.is_deleted.is_(False)))
        assert admin and owner and sensor_model and actuator_model
        sensor_model_id, actuator_model_id = sensor_model.id, actuator_model.id
        admin_header = {"Authorization": f"Bearer {create_access_token(str(admin.id), {'role': 'ADMIN', 'token_version': admin.token_version})}"}
        owner_header = {"Authorization": f"Bearer {create_access_token(str(owner.id), {'role': 'OWNER', 'token_version': owner.token_version})}"}
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        assert (await client.get("/api/v1/admin/alert-rules", headers=owner_header)).status_code == 403
        created = await client.post("/api/v1/admin/alert-rules", headers=admin_header, json={"code": f"VERSION_TEST_{suffix}", "name": "Quy tắc phiên bản", "target_type": "SENSOR", "evaluator_type": "THRESHOLD", "revision": {"business_risk_level": "MEDIUM", "condition_config": {"operator": "GT", "value": 10, "severity": "WARNING"}, "message_template": "Giá trị cao", "consequence": "Kiểm thử", "recommended_action": "Kiểm tra"}})
        assert created.status_code == 201, created.text
        rule_id = created.json()["id"]
        assert created.json()["current_revision"]["status"] == "DRAFT"
        wrong_target = await client.post(f"/api/v1/admin/alert-rules/{rule_id}/profiles", headers=admin_header, json={"code": f"WRONG_{suffix}", "name": "Sai loại", "config": {}, "actuator_model_ids": [actuator_model_id], "sensor_model_ids": []})
        assert wrong_target.status_code == 422
        profile = await client.post(f"/api/v1/admin/alert-rules/{rule_id}/profiles", headers=admin_header, json={"code": f"SENSOR_{suffix}", "name": "Mẫu cảm biến tương thích", "config": {}, "actuator_model_ids": [], "sensor_model_ids": [sensor_model_id]})
        assert profile.status_code == 201, profile.text
        profiles = await client.get(f"/api/v1/admin/alert-rules/{rule_id}/profiles", headers=admin_header)
        assert profiles.json()[0]["sensor_model_ids"] == [sensor_model_id]
        validated = await client.post(f"/api/v1/admin/alert-rules/{rule_id}/validate", headers=admin_header)
        assert validated.json() == {"valid": True, "missing_fields": []}
        published = await client.post(f"/api/v1/admin/alert-rules/{rule_id}/publish", headers=admin_header)
        assert published.json()["current_revision"]["status"] == "PUBLISHED"
        second = await client.post(f"/api/v1/admin/alert-rules/{rule_id}/revisions", headers=admin_header, json={"business_risk_level": "HIGH", "condition_config": {"operator": "GT", "value": 12, "severity": "CRITICAL"}, "message_template": "Giá trị rất cao", "consequence": "Kiểm thử", "recommended_action": "Kiểm tra ngay"})
        assert second.status_code == 201, second.text
        assert second.json()["current_revision"]["revision"] == 2
        assert second.json()["current_revision"]["status"] == "DRAFT"
        statuses = {item["revision"]: item["status"] for item in second.json()["revisions"]}
        assert statuses == {1: "PUBLISHED", 2: "DRAFT"}
        await client.post(f"/api/v1/admin/alert-rules/{rule_id}/validate", headers=admin_header)
        published_second = await client.post(f"/api/v1/admin/alert-rules/{rule_id}/publish", headers=admin_header)
        assert {item["revision"]: item["status"] for item in published_second.json()["revisions"]} == {1: "RETIRED", 2: "PUBLISHED"}
        retired = await client.post(f"/api/v1/admin/alert-rules/{rule_id}/retire", headers=admin_header)
        assert retired.status_code == 200
        assert retired.json()["is_enabled"] is False
        assert retired.json()["current_revision"]["status"] == "RETIRED"

    async with AsyncSessionLocal() as db:
        await db.execute(delete(AlertRuleRevision).where(AlertRuleRevision.rule_id == rule_id))
        await db.execute(delete(AlertRule).where(AlertRule.id == rule_id))
        await db.commit()


@pytest.mark.asyncio
async def test_current_binding_accepts_same_project_and_rejects_cross_project_and_wrong_model() -> None:
    suffix = uuid4().hex[:8].upper()
    ids: dict[str, list[int] | int] = {"projects": [], "devices": [], "sensors": []}
    async with AsyncSessionLocal() as db:
        admin = await db.scalar(select(User).where(User.system_role == UserRole.ADMIN, User.is_deleted.is_(False)))
        owner = await db.scalar(select(User).where(User.system_role == UserRole.OWNER, User.is_deleted.is_(False)))
        actuator_model = await db.scalar(select(ActuatorModel).where(ActuatorModel.is_active.is_(True)))
        current_model = await db.scalar(select(SensorModel).where(SensorModel.code == "LOAD_CURRENT_A"))
        wrong_model = await db.scalar(select(SensorModel).where(SensorModel.code.not_in(("LOAD_CURRENT_A", "INPUT_CURRENT_A")), SensorModel.is_active.is_(True)))
        assert admin and owner and actuator_model and current_model and wrong_model
        project_a = Project(owner_user_id=owner.id, code=f"BIND-A-{suffix}", name="Dự án A", status=ProjectStatus.ACTIVE)
        project_b = Project(owner_user_id=owner.id, code=f"BIND-B-{suffix}", name="Dự án B", status=ProjectStatus.ACTIVE)
        db.add_all([project_a, project_b])
        await db.flush()
        devices = [
            Device(project_id=project_a.id, code=f"BA1-{suffix}", name="A1", status=DeviceStatus.ONLINE, is_enabled=True),
            Device(project_id=project_a.id, code=f"BA2-{suffix}", name="A2", status=DeviceStatus.ONLINE, is_enabled=True),
            Device(project_id=project_b.id, code=f"BB1-{suffix}", name="B1", status=DeviceStatus.ONLINE, is_enabled=True),
        ]
        db.add_all(devices)
        await db.flush()
        actuator = Actuator(device_id=devices[0].id, actuator_model_id=actuator_model.id, sequence_number=1, code=f"ACT-{suffix}", name="Bơm", is_enabled=True)
        sensors = [
            Sensor(device_id=devices[1].id, sensor_model_id=current_model.id, code=f"CUR-A-{suffix}", name="Dòng A", is_enabled=True),
            Sensor(device_id=devices[2].id, sensor_model_id=current_model.id, code=f"CUR-B-{suffix}", name="Dòng B", is_enabled=True),
            Sensor(device_id=devices[1].id, sensor_model_id=wrong_model.id, code=f"WRONG-{suffix}", name="Sai loại", is_enabled=True),
        ]
        db.add_all([actuator, *sensors])
        await db.commit()
        ids = {"projects": [project_a.id, project_b.id], "devices": [item.id for item in devices], "sensors": [item.id for item in sensors], "actuator": actuator.id}

        binding = await set_feedback_binding(project_a.id, devices[0].id, actuator.id, FeedbackBindingCreate(sensor_id=sensors[0].id), db, admin)
        assert binding.sensor_id == sensors[0].id
        assert int(await db.scalar(select(func.count(ActuatorFeedbackBinding.id)).where(ActuatorFeedbackBinding.actuator_id == actuator.id)) or 0) == 1
        observed_at = datetime.now(UTC)
        assert await evaluate_operational_rules_for_sensor(db, sensor=sensors[0], value=0.5, quality="VALID", recorded_at=observed_at, received_at=observed_at) == []
        with pytest.raises(HTTPException) as cross_project:
            await set_feedback_binding(project_a.id, devices[0].id, actuator.id, FeedbackBindingCreate(sensor_id=sensors[1].id), db, admin)
        assert cross_project.value.status_code == 409
        with pytest.raises(HTTPException) as wrong_type:
            await set_feedback_binding(project_a.id, devices[0].id, actuator.id, FeedbackBindingCreate(sensor_id=sensors[2].id), db, admin)
        assert wrong_type.value.status_code == 409

    async with AsyncSessionLocal() as db:
        await db.execute(delete(ActuatorFeedbackBinding).where(ActuatorFeedbackBinding.actuator_id == ids["actuator"]))
        await db.execute(delete(Actuator).where(Actuator.id == ids["actuator"]))
        await db.execute(delete(Sensor).where(Sensor.id.in_(ids["sensors"])))
        await db.execute(delete(Device).where(Device.id.in_(ids["devices"])))
        await db.execute(delete(Project).where(Project.id.in_(ids["projects"])))
        await db.commit()


def test_actuator_feedback_requires_all_hardware_values() -> None:
    config = {
        "feedback_role": "RUNNING_CURRENT",
        "min_running_current_a": None,
        "max_running_current_a": None,
        "startup_grace_seconds": None,
        "debounce_seconds": None,
        "recovery_current_a": None,
        "recovery_duration_seconds": None,
    }
    assert validate_condition_config("ACTUATOR_FEEDBACK", config) == [
        "min_running_current_a",
        "max_running_current_a",
        "startup_grace_seconds",
        "debounce_seconds",
        "recovery_current_a",
        "recovery_duration_seconds",
    ]


def test_current_evaluator_distinguishes_zero_stale_and_invalid() -> None:
    config = {
        "feedback_role": "RUNNING_CURRENT",
        "min_running_current_a": 0.3,
        "max_running_current_a": 2.0,
        "startup_grace_seconds": 5,
        "debounce_seconds": 10,
        "recovery_current_a": 0.4,
        "recovery_duration_seconds": 10,
    }
    evaluator = EVALUATOR_REGISTRY["ACTUATOR_FEEDBACK"]
    assert evaluator.evaluate(config, {"expected_on": True, "current_a": 0.0, "quality": "VALID", "freshness": "FRESH"}).active
    assert not evaluator.evaluate(config, {"expected_on": True, "current_a": None, "quality": "VALID", "freshness": "NO_DATA"}).active
    assert not evaluator.evaluate(config, {"expected_on": True, "current_a": 0.0, "quality": "VALID", "freshness": "STALE"}).active
    assert not evaluator.evaluate(config, {"expected_on": True, "current_a": 9999, "quality": "OUT_OF_RANGE", "freshness": "FRESH"}).active


def test_generic_electrical_evaluator_supports_voltage_low_high_and_current_high() -> None:
    evaluator = EVALUATOR_REGISTRY["ACTUATOR_FEEDBACK"]
    base = {"startup_grace_seconds": 0, "debounce_seconds": 1, "recovery_duration_seconds": 1, "severity": "WARNING"}
    low_voltage = {**base, "feedback_role": "SUPPLY_VOLTAGE", "operator": "LT", "threshold": 11.0, "recovery_threshold": 11.5}
    high_voltage = {**base, "feedback_role": "SUPPLY_VOLTAGE", "operator": "GT", "threshold": 13.0, "recovery_threshold": 12.5}
    high_current = {**base, "feedback_role": "RUNNING_CURRENT", "operator": "GT", "threshold": 2.0, "recovery_threshold": 1.8}
    assert not validate_condition_config("ACTUATOR_FEEDBACK", low_voltage)
    assert evaluator.evaluate(low_voltage, {"voltage_v": 10.9, "feedback_value": 10.9, "quality": "VALID", "freshness": "FRESH"}).active
    assert evaluator.evaluate(high_voltage, {"voltage_v": 13.1, "feedback_value": 13.1, "quality": "VALID", "freshness": "FRESH"}).active
    assert evaluator.evaluate(high_current, {"expected_on": True, "current_a": 2.1, "feedback_value": 2.1, "quality": "VALID", "freshness": "FRESH"}).active
    assert not evaluator.evaluate(low_voltage, {"voltage_v": 0, "feedback_value": 0, "quality": "STALE", "freshness": "STALE"}).active


def test_electrical_threshold_status_and_command_precedence() -> None:
    base = {"configured": True, "quality": "VALID", "freshness": "FRESH", "lower": None, "upper": None}
    assert _electrical_threshold_status(value=0, **base) == "IN_RANGE"
    assert _electrical_threshold_status(value=0.2, **{**base, "lower": 0.3}) == "BELOW_RANGE"
    assert _electrical_threshold_status(value=2.1, **{**base, "upper": 2.0}) == "ABOVE_RANGE"
    assert _electrical_threshold_status(value=None, **{**base, "freshness": "NO_DATA"}) == "NO_DATA"
    assert _electrical_threshold_status(value=1.0, **{**base, "freshness": "STALE"}) == "STALE"
    assert _electrical_threshold_status(value=1.0, **{**base, "quality": "INVALID"}) == "INVALID"
    assert _electrical_threshold_status(value=None, **{**base, "configured": False}) == "UNCONFIGURED"

    metric = {"configured": False, "threshold_status": "UNCONFIGURED"}
    electrical = {"configured": False, "voltage": metric, "current": metric, "active_incident": None}
    conclusion = _actuator_operational_conclusion(True, None, "TIMEOUT", electrical)
    assert conclusion["code"] == "COMMAND_TIMEOUT"
    assert conclusion["label"] == "Lệnh điều khiển hết thời gian chờ"


def test_digital_duration_and_schedule_evaluators_are_typed_and_executable() -> None:
    digital = EVALUATOR_REGISTRY["DIGITAL_STATE"]
    assert digital.evaluate({"active_state": "LOW", "active_value": 0}, {"value": 0, "quality": "VALID", "freshness": "FRESH"}).active
    assert not digital.evaluate({"active_state": "LOW", "active_value": 0}, {"value": 1, "quality": "VALID", "freshness": "FRESH"}).active
    duration = EVALUATOR_REGISTRY["THRESHOLD_DURATION"]
    assert duration.evaluate({"operator": "GT", "value": 85, "duration_seconds": 60}, {"value": 90, "quality": "VALID", "freshness": "FRESH"}).active
    schedule = EVALUATOR_REGISTRY["SCHEDULE_FEEDBACK"]
    schedule_config = {"schedule_id": "GROW_LIGHT_DAY", "feedback_role": "RUNNING_CURRENT", "min_running_current_a": 0.2, "max_running_current_a": 2.0, "startup_grace_seconds": 5, "debounce_seconds": 10, "recovery_current_a": 0.3, "recovery_duration_seconds": 10}
    assert schedule.evaluate(schedule_config, {"expected_on": True, "current_a": 0.0, "quality": "VALID", "freshness": "FRESH"}).active


def test_failed_or_timed_out_command_is_not_hidden_by_matching_state() -> None:
    assert _actuator_sync(True, True, "FAILED") == "IN_SYNC"
    assert _actuator_sync(True, True, "TIMEOUT") == "IN_SYNC"


def test_operational_telegram_message_is_vietnamese_and_snapshot_driven() -> None:
    message = format_operational_message({
        "event_type": "OPEN", "business_risk_level": "EXTREME", "project_name": "Ao thử nghiệm", "project_code": "TB-0015", "device_name": "Bộ điều khiển NFT", "actuator_name": "Bơm NFT", "rule_name": "Bơm nước lên giàn NFT mất hoạt động", "desired_state": True, "reported_state": True, "current_a": 0.02, "minimum_running_current_a": 0.3, "quality": "VALID", "freshness": "FRESH", "recorded_at": "2026-08-24T00:00:00Z", "received_at": "2026-08-24T00:00:01Z", "consequence": "Cây mất nước.", "recommended_action": "Kiểm tra bơm.", "incident_id": 42,
    })
    assert "CẢNH BÁO CỰC CAO" in message
    assert "Dòng điện hiện tại: 0,02 A" in message
    assert "Ngưỡng vận hành: 0,3 A" in message
    assert "Mã sự cố" not in message


@pytest.mark.asyncio
async def test_actuator_incident_lifecycle_deduplicates_escalates_and_recovers_once() -> None:
    suffix = uuid4().hex[:8].upper()
    now = datetime.now(UTC)
    async with AsyncSessionLocal() as db:
        project = await db.scalar(select(Project).where(Project.code == "CODEX-TEST-RUNTIME"))
        assert project is not None
        device = await db.scalar(select(Device).where(Device.project_id == project.id))
        current_model = await db.scalar(select(SensorModel).where(SensorModel.code == "LOAD_CURRENT_A"))
        actuator_model = await db.scalar(select(ActuatorModel).where(ActuatorModel.is_active.is_(True)))
        assert device and current_model and actuator_model
        sensor = Sensor(device_id=device.id, sensor_model_id=current_model.id, code=f"INC-CUR-{suffix}", name="Dòng incident", is_enabled=True)
        actuator = Actuator(device_id=device.id, actuator_model_id=actuator_model.id, sequence_number=900, code=f"INC-ACT-{suffix}", name="Bơm incident", is_enabled=True, desired_state=True, reported_state=True)
        rule = AlertRule(code=f"INCIDENT_TEST_{suffix}", name="Quy tắc vòng đời", target_type="ACTUATOR", evaluator_type="ACTUATOR_FEEDBACK", is_enabled=True)
        db.add_all([sensor, actuator, rule])
        await db.flush()
        revision = AlertRuleRevision(rule_id=rule.id, revision=1, business_risk_level="HIGH", condition_config={}, source_order=900, status="PUBLISHED")
        db.add(revision)
        await db.flush()
        rule.current_revision_id = revision.id
        await db.commit()
        config = {"feedback_role": "RUNNING_CURRENT", "min_running_current_a": 0.3, "max_running_current_a": 2.0, "startup_grace_seconds": 0, "debounce_seconds": 5, "recovery_current_a": 0.4, "recovery_duration_seconds": 10}
        abnormal = {"current_a": 0.0, "quality": "VALID", "freshness": "FRESH"}
        normal = {"current_a": 0.5, "quality": "VALID", "freshness": "FRESH"}

        incident = await _transition_incident(db, project=project, device=device, sensor=sensor, actuator=actuator, rule=rule, revision=revision, config=config, active=True, severity="WARNING", observed_at=now, snapshot=abnormal)
        assert incident and incident.status == "PENDING"
        assert int(await db.scalar(select(func.count(NotificationOutbox.id)).where(NotificationOutbox.incident_id == incident.id)) or 0) == 0
        same = await _transition_incident(db, project=project, device=device, sensor=sensor, actuator=actuator, rule=rule, revision=revision, config=config, active=True, severity="WARNING", observed_at=now + timedelta(seconds=5), snapshot=abnormal)
        assert same is incident and incident.status == "OPEN"
        await _transition_incident(db, project=project, device=device, sensor=sensor, actuator=actuator, rule=rule, revision=revision, config=config, active=True, severity="CRITICAL", observed_at=now + timedelta(seconds=6), snapshot=abnormal)
        await _transition_incident(db, project=project, device=device, sensor=sensor, actuator=actuator, rule=rule, revision=revision, config=config, active=True, severity="CRITICAL", observed_at=now + timedelta(seconds=7), snapshot=abnormal)
        events = list((await db.scalars(select(NotificationOutbox.event_type).where(NotificationOutbox.incident_id == incident.id).order_by(NotificationOutbox.id))).all())
        assert events == ["OPEN"]
        settings = ProjectNotificationSettings(project_id=project.id, telegram_enabled=True, notify_alert_opened=True, notify_alert_escalated=True, notify_alert_resolved=True, minimum_business_risk_level="LOW")
        policy = ProjectNotificationRiskPolicy(project_id=project.id, risk_level="HIGH", telegram_enabled=True, notify_on_open=True, notify_on_escalation=True, notify_on_recovery=True, notify_on_resolved=True, reminder_enabled=True, initial_reminder_seconds=1, repeat_interval_seconds=1, max_reminders=2, stop_reminders_on_ack=True)
        db.add_all([settings, policy])
        await db.commit()
        assert await enqueue_due_reminders(db, now=now + timedelta(seconds=20)) == 1
        assert await enqueue_due_reminders(db, now=now + timedelta(seconds=21)) == 1
        assert await enqueue_due_reminders(db, now=now + timedelta(seconds=100)) == 0
        incident.status = "ACKNOWLEDGED"
        await db.flush()
        assert await enqueue_due_reminders(db, now=now + timedelta(seconds=200)) == 0
        await _transition_incident(db, project=project, device=device, sensor=sensor, actuator=actuator, rule=rule, revision=revision, config=config, active=False, severity="WARNING", observed_at=now + timedelta(seconds=8), snapshot=normal)
        assert incident.status == "NORMALIZED"
        await _transition_incident(db, project=project, device=device, sensor=sensor, actuator=actuator, rule=rule, revision=revision, config=config, active=False, severity="WARNING", observed_at=now + timedelta(seconds=18), snapshot=normal)
        assert incident.status == "RESOLVED"
        events = list((await db.scalars(select(NotificationOutbox.event_type).where(NotificationOutbox.incident_id == incident.id).order_by(NotificationOutbox.id))).all())
        assert events == ["OPEN", "REMINDER", "REMINDER", "RECOVERED", "RESOLVED"]
        assert incident.occurrence_count == 4
        recipients = [ProjectNotificationRecipient(project_id=project.id, name="Nhận thành công", telegram_chat_id=f"ok-{suffix}", enabled=True), ProjectNotificationRecipient(project_id=project.id, name="Nhận lỗi", telegram_chat_id=f"fail-{suffix}", enabled=True)]
        db.add_all(recipients)
        await db.commit()
        pending_outboxes = list((await db.scalars(select(NotificationOutbox).where(NotificationOutbox.incident_id == incident.id))).all())
        for outbox in pending_outboxes:
            outbox.available_at = datetime.now(UTC) - timedelta(seconds=1)
        await db.commit()

        class SelectiveNotifier:
            def __init__(self, fail: bool) -> None:
                self.fail = fail
                self.calls: list[str] = []

            async def send_message(self, chat_id: str, text: str) -> TelegramDeliveryResult:
                assert "WARNING" not in text and "CRITICAL" not in text
                self.calls.append(chat_id)
                return TelegramDeliveryResult(not (self.fail and chat_id.startswith("fail-")), error_category="TIMEOUT" if self.fail and chat_id.startswith("fail-") else None)

        first_notifier = SelectiveNotifier(fail=True)
        assert await process_notification_outbox(db, notifier=first_notifier) == 0
        assert len(first_notifier.calls) == 10
        statuses = list((await db.scalars(select(NotificationDelivery.status).where(NotificationDelivery.incident_id == incident.id))).all())
        assert statuses.count("SENT") == 5
        assert statuses.count("RETRYING") == 5
        pending_outboxes = list((await db.scalars(select(NotificationOutbox).where(NotificationOutbox.incident_id == incident.id))).all())
        for outbox in pending_outboxes:
            outbox.available_at = datetime.now(UTC) - timedelta(seconds=1)
        await db.commit()
        retry_notifier = SelectiveNotifier(fail=False)
        assert await process_notification_outbox(db, notifier=retry_notifier) == 5
        assert len(retry_notifier.calls) == 5
        assert set((await db.scalars(select(NotificationOutbox.status).where(NotificationOutbox.incident_id == incident.id))).all()) == {"PROCESSED"}
        previous_device_status = device.status
        device.status = DeviceStatus.OFFLINE
        suppressed = NotificationOutbox(incident_id=incident.id, event_type="OPEN", idempotency_key=f"incident:{incident.id}:STALE_TEST", payload_snapshot={**incident.trigger_snapshot, "event_type": "OPEN", "freshness": "STALE", "business_risk_level": "HIGH"}, status="PENDING", available_at=datetime.now(UTC) - timedelta(seconds=1), attempt_count=0)
        db.add(suppressed)
        await db.commit()
        suppression_notifier = SelectiveNotifier(fail=False)
        assert await process_notification_outbox(db, notifier=suppression_notifier) == 1
        assert suppression_notifier.calls == []
        assert suppressed.status == "SKIPPED"
        assert suppressed.skip_reason == "SUPPRESSED_BY_DEVICE_OFFLINE"
        device.status = previous_device_status
        await db.commit()
        incident_id, sensor_id, actuator_id, rule_id = incident.id, sensor.id, actuator.id, rule.id
        settings_id = settings.id
        recipient_ids = [recipient.id for recipient in recipients]
        await db.commit()

    async with AsyncSessionLocal() as db:
        await db.execute(delete(NotificationDelivery).where(NotificationDelivery.incident_id == incident_id))
        await db.execute(delete(NotificationOutbox).where(NotificationOutbox.incident_id == incident_id))
        await db.execute(delete(OperationalIncident).where(OperationalIncident.id == incident_id))
        await db.execute(delete(ProjectNotificationRecipient).where(ProjectNotificationRecipient.id.in_(recipient_ids)))
        await db.execute(delete(ProjectNotificationRiskPolicy).where(ProjectNotificationRiskPolicy.project_id == project.id))
        await db.execute(delete(ProjectNotificationSettings).where(ProjectNotificationSettings.id == settings_id))
        await db.execute(delete(Actuator).where(Actuator.id == actuator_id))
        await db.execute(delete(Sensor).where(Sensor.id == sensor_id))
        await db.execute(delete(AlertRuleRevision).where(AlertRuleRevision.rule_id == rule_id))
        await db.execute(delete(AlertRule).where(AlertRule.id == rule_id))
        await db.commit()
