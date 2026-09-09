from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy import delete, func, select

from app.db.session import AsyncSessionLocal
from app.models.actuator import Actuator
from app.models.actuator_model import ActuatorModel
from app.models.device import Device
from app.models.operational_alert import NotificationDelivery, NotificationOutbox, OperationalIncident
from app.models.project import Project
from app.models.project_settings import (
    ProjectNotificationRecipient,
    ProjectNotificationRiskPolicy,
    ProjectNotificationSettings,
)
from app.models.sensor import Sensor
from app.models.sensor_model import SensorModel
from app.models.telemetry import TelemetryReading
from app.models.threshold_alert_config import ThresholdAlertConfig
from app.services.notification_outbox_service import (
    enqueue_operational_event,
    next_notification_generation,
    process_notification_outbox,
    reconcile_active_incident_notifications,
)
from app.services.operational_incident_service import (
    evaluate_actuator_composite_incident,
    evaluate_sensor_threshold_incident,
    reevaluate_latest_sensor_threshold,
)
from app.services.telegram_notifier import TelegramDeliveryResult
from app.services.threshold_alert_config_service import apply_threshold_alert_config_update


class SuccessfulNotifier:
    configured = True

    def __init__(self) -> None:
        self.calls: list[tuple[str, str]] = []

    async def send_message(self, chat_id: str, text: str) -> TelegramDeliveryResult:
        self.calls.append((chat_id, text))
        return TelegramDeliveryResult(sent=True, status_code=200)


async def _runtime() -> tuple[Project, Device]:
    async with AsyncSessionLocal() as db:
        project = await db.scalar(select(Project).where(Project.code == "CODEX-TEST-RUNTIME"))
        assert project is not None
        device = await db.scalar(select(Device).where(Device.project_id == project.id))
        assert device is not None
        return project, device


async def _clear_notification_configuration(db, project_id: int) -> None:
    await db.execute(delete(ProjectNotificationRecipient).where(ProjectNotificationRecipient.project_id == project_id))
    await db.execute(delete(ProjectNotificationRiskPolicy).where(ProjectNotificationRiskPolicy.project_id == project_id))
    await db.execute(delete(ProjectNotificationSettings).where(ProjectNotificationSettings.project_id == project_id))


async def _reset_project_alert_test_state(db, project_id: int) -> None:
    incident_ids = select(OperationalIncident.id).where(OperationalIncident.project_id == project_id)
    await db.execute(delete(NotificationDelivery).where(NotificationDelivery.incident_id.in_(incident_ids)))
    await db.execute(delete(NotificationOutbox).where(NotificationOutbox.project_id == project_id))
    await db.execute(delete(OperationalIncident).where(OperationalIncident.project_id == project_id))
    await _clear_notification_configuration(db, project_id)
    await db.flush()


async def _open_ph_incident(db, *, device: Device, code_prefix: str, value: float = 10.8):
    model = await db.scalar(select(SensorModel).where(SensorModel.code == "PH"))
    assert model is not None
    sensor = Sensor(
        device_id=device.id,
        sensor_model_id=model.id,
        code=f"{code_prefix}-{uuid4().hex[:8].upper()}",
        name="Sensor pH policy test",
        is_enabled=True,
    )
    db.add(sensor)
    await db.flush()
    db.add(ThresholdAlertConfig(
        sensor_id=sensor.id,
        metric_type="SENSOR_VALUE",
        enabled=True,
        lower_threshold=6.0,
        upper_threshold=7.5,
        below_risk_level="LOW",
        above_risk_level="HIGH",
        delay_seconds=0,
    ))
    incident = await evaluate_sensor_threshold_incident(
        db,
        device=device,
        sensor=sensor,
        sensor_model=model,
        value=value,
        quality="VALID",
        recorded_at=datetime.now(UTC),
        received_at=datetime.now(UTC),
    )
    assert incident is not None
    return sensor, incident


@pytest.mark.asyncio
async def test_ph_10_8_patch_to_7_5_opens_and_sends_once_without_new_reading() -> None:
    project, device = await _runtime()
    now = datetime.now(UTC)
    suffix = uuid4().hex[:8].upper()
    async with AsyncSessionLocal() as db:
        await _reset_project_alert_test_state(db, project.id)
        model = await db.scalar(select(SensorModel).where(SensorModel.code == "PH"))
        assert model is not None
        sensor = Sensor(
            device_id=device.id, sensor_model_id=model.id, code=f"PH-CANON-{suffix}",
            name="Sensor pH", is_enabled=True,
        )
        db.add(sensor)
        await db.flush()
        config = ThresholdAlertConfig(
            sensor_id=sensor.id, metric_type="SENSOR_VALUE", enabled=True,
            lower_threshold=6.0, upper_threshold=14.0,
            below_risk_level="LOW", above_risk_level="HIGH", delay_seconds=0,
        )
        db.add_all([
            config,
            TelemetryReading(
                sensor_id=sensor.id, value=10.8,
                recorded_at=now - timedelta(seconds=10), received_at=now - timedelta(seconds=9),
            ),
        ])
        await db.flush()

        # This is the PATCH service sequence: mutate canonical config, flush,
        # then evaluate the latest persisted reading without injecting telemetry.
        apply_threshold_alert_config_update(config, {"upper_threshold": 7.5, "above_risk_level": None})
        await db.flush()
        incident = await reevaluate_latest_sensor_threshold(db, device=await db.get(Device, device.id), sensor=sensor, observed_at=now)
        await db.commit()

        assert config.upper_threshold == 7.5
        assert config.above_risk_level == "HIGH"
        assert incident is not None and incident.status == "OPEN"
        assert incident.business_risk_level_snapshot == "HIGH"
        assert incident.trigger_snapshot["threshold_direction"] == "ABOVE"
        assert incident.trigger_snapshot["condition_key"] == "SENSOR_PH_HIGH"
        assert await db.scalar(select(func.count(NotificationOutbox.id)).where(
            NotificationOutbox.incident_id == incident.id,
            NotificationOutbox.event_type == "OPEN",
        )) == 1

        settings = ProjectNotificationSettings(
            project_id=project.id, enabled=True, in_app_enabled=True,
            telegram_enabled=True, notify_alert_opened=True,
        )
        recipient = ProjectNotificationRecipient(
            project_id=project.id, name="Operator pH", telegram_chat_id="123456789", enabled=True,
        )
        policy = ProjectNotificationRiskPolicy(
            project_id=project.id, risk_level="HIGH", telegram_enabled=True,
            notify_on_open=True, notify_on_escalation=True, notify_on_recovery=True,
            notify_on_resolved=True, reminder_enabled=False,
            initial_reminder_seconds=1800, repeat_interval_seconds=3600,
            max_reminders=0, stop_reminders_on_ack=True,
        )
        db.add_all([settings, recipient, policy])
        await db.commit()
        notifier = SuccessfulNotifier()
        await process_notification_outbox(db, notifier=notifier)
        assert len(notifier.calls) == 1
        assert "pH vượt ngưỡng trên" in notifier.calls[0][1]
        delivery = await db.scalar(select(NotificationDelivery).where(
            NotificationDelivery.incident_id == incident.id,
        ))
        assert delivery is not None and delivery.status == "SENT"

        # Repeated abnormal evaluation updates the occurrence only.
        for index in range(100):
            await evaluate_sensor_threshold_incident(
                db, device=await db.get(Device, device.id), sensor=sensor, sensor_model=model,
                value=10.8, quality="VALID", recorded_at=now + timedelta(seconds=index),
                received_at=now + timedelta(seconds=index),
            )
        await db.commit()
        assert await db.scalar(select(func.count(OperationalIncident.id)).where(
            OperationalIncident.sensor_id == sensor.id,
        )) == 1
        assert await db.scalar(select(func.count(NotificationOutbox.id)).where(
            NotificationOutbox.incident_id == incident.id,
            NotificationOutbox.event_type == "OPEN",
        )) == 1

        # Recovery closes the active generation; relapse creates a new one.
        await evaluate_sensor_threshold_incident(
            db, device=await db.get(Device, device.id), sensor=sensor, sensor_model=model,
            value=7.0, quality="VALID", recorded_at=now + timedelta(minutes=5),
            received_at=now + timedelta(minutes=5),
        )
        await db.flush()
        assert incident.status == "NORMALIZED"
        relapse = await evaluate_sensor_threshold_incident(
            db, device=await db.get(Device, device.id), sensor=sensor, sensor_model=model,
            value=10.8, quality="VALID", recorded_at=now + timedelta(minutes=6),
            received_at=now + timedelta(minutes=6),
        )
        await db.commit()
        assert relapse is not None and relapse.id != incident.id and relapse.status == "OPEN"
        await evaluate_sensor_threshold_incident(
            db, device=await db.get(Device, device.id), sensor=sensor, sensor_model=model,
            value=7.0, quality="VALID", recorded_at=now + timedelta(minutes=7),
            received_at=now + timedelta(minutes=7),
        )
        await db.commit()


@pytest.mark.asyncio
async def test_disabled_open_reconciles_once_when_telegram_is_enabled() -> None:
    project, device = await _runtime()
    now = datetime.now(UTC)
    suffix = uuid4().hex[:8].upper()
    async with AsyncSessionLocal() as db:
        await _reset_project_alert_test_state(db, project.id)
        model = await db.scalar(select(SensorModel).where(SensorModel.code == "PH"))
        assert model is not None
        sensor = Sensor(device_id=device.id, sensor_model_id=model.id, code=f"PH-SYNC-{suffix}", name="pH sync", is_enabled=True)
        db.add(sensor); await db.flush()
        db.add(ThresholdAlertConfig(sensor_id=sensor.id, metric_type="SENSOR_VALUE", enabled=True, upper_threshold=7.5, above_risk_level="HIGH", delay_seconds=0))
        incident = await evaluate_sensor_threshold_incident(
            db, device=await db.get(Device, device.id), sensor=sensor, sensor_model=model,
            value=10.8, quality="VALID", recorded_at=now, received_at=now,
        )
        assert incident is not None
        settings = ProjectNotificationSettings(
            project_id=project.id,
            enabled=True,
            in_app_enabled=True,
            telegram_enabled=False,
            notify_alert_opened=True,
        )
        db.add_all([
            settings,
            ProjectNotificationRecipient(
                project_id=project.id,
                name="Operator sync",
                telegram_chat_id="123456789",
                enabled=True,
            ),
            ProjectNotificationRiskPolicy(
                project_id=project.id,
                risk_level="HIGH",
                telegram_enabled=True,
                notify_on_open=True,
                notify_on_escalation=True,
                notify_on_recovery=True,
                notify_on_resolved=True,
                reminder_enabled=False,
                initial_reminder_seconds=1800,
                repeat_interval_seconds=3600,
                max_reminders=0,
                stop_reminders_on_ack=True,
            ),
        ])
        await db.commit()
        notifier = SuccessfulNotifier()
        await process_notification_outbox(db, notifier=notifier)
        skipped = await db.scalar(select(NotificationOutbox).where(
            NotificationOutbox.incident_id == incident.id,
            NotificationOutbox.event_type == "OPEN",
        ))
        assert skipped is not None and skipped.status == "SKIPPED" and skipped.skip_reason == "TELEGRAM_DISABLED"
        assert not notifier.calls

        settings.telegram_enabled = True
        generation = await next_notification_generation(db, project_id=project.id)
        assert await reconcile_active_incident_notifications(
            db, project_id=project.id, generation=generation,
            reason="TELEGRAM_ENABLED",
        ) == 1
        # Same generation is idempotent.
        assert await reconcile_active_incident_notifications(
            db, project_id=project.id, generation=generation,
            reason="TELEGRAM_ENABLED",
        ) == 0
        await db.commit()
        await process_notification_outbox(db, notifier=notifier)
        assert len(notifier.calls) == 1
        sync = await db.scalar(select(NotificationOutbox).where(
            NotificationOutbox.incident_id == incident.id,
            NotificationOutbox.event_type == "ACTIVE_SYNC",
        ))
        assert sync is not None and sync.status == "SENT"
        incident.status = "NORMALIZED"
        incident.normalized_at = datetime.now(UTC)
        await db.execute(delete(ProjectNotificationRecipient).where(ProjectNotificationRecipient.project_id == project.id))
        await db.execute(delete(ProjectNotificationRiskPolicy).where(ProjectNotificationRiskPolicy.project_id == project.id))
        await db.execute(delete(ProjectNotificationSettings).where(ProjectNotificationSettings.project_id == project.id))
        await db.commit()


@pytest.mark.asyncio
async def test_actuator_composite_rules_are_mutually_exclusive_and_off_is_normal() -> None:
    project, device = await _runtime()
    now = datetime.now(UTC)
    suffix = uuid4().hex[:8].upper()
    async with AsyncSessionLocal() as db:
        await _reset_project_alert_test_state(db, project.id)
        model = await db.scalar(select(ActuatorModel).where(ActuatorModel.code == "FISH_TANK_PUMP"))
        assert model is not None
        model.nominal_voltage_v = 12.0
        model.voltage_tolerance_v = 1.0
        model.zero_voltage_max_v = 0.5
        model.minimum_running_current_a = 0.1
        actuator = Actuator(
            device_id=device.id, actuator_model_id=model.id, sequence_number=999,
            code=f"PUMP-{suffix}", name="Bơm kiểm thử", is_enabled=True,
            electrical_alerts_enabled=True, desired_state=False, reported_state=False,
            voltage_v=0.0, current_a=0.0,
        )
        db.add(actuator); await db.flush()
        assert await evaluate_actuator_composite_incident(
            db, device=await db.get(Device, device.id), actuator=actuator,
            recorded_at=now, received_at=now,
        ) is None

        actuator.desired_state = actuator.reported_state = True
        actuator.voltage_v, actuator.current_a = 12.0, 0.0
        no_load = await evaluate_actuator_composite_incident(
            db, device=await db.get(Device, device.id), actuator=actuator,
            recorded_at=now + timedelta(seconds=1), received_at=now + timedelta(seconds=1),
        )
        assert no_load is not None and no_load.trigger_snapshot["condition_key"] == "ACTUATOR_ON_NO_LOAD"

        actuator.voltage_v, actuator.current_a = 0.0, 0.0
        no_power = await evaluate_actuator_composite_incident(
            db, device=await db.get(Device, device.id), actuator=actuator,
            recorded_at=now + timedelta(seconds=2), received_at=now + timedelta(seconds=2),
        )
        await db.commit()
        assert no_power is not None and no_power.trigger_snapshot["condition_key"] == "ACTUATOR_NO_POWER"
        assert no_load.status == "NORMALIZED"
        assert await db.scalar(select(func.count(OperationalIncident.id)).where(
            OperationalIncident.actuator_id == actuator.id,
            OperationalIncident.status.in_(("OPEN", "ACKNOWLEDGED", "PENDING")),
        )) == 1
        incident_ids = select(OperationalIncident.id).where(OperationalIncident.actuator_id == actuator.id)
        await db.execute(delete(NotificationDelivery).where(NotificationDelivery.incident_id.in_(incident_ids)))
        await db.execute(delete(NotificationOutbox).where(NotificationOutbox.incident_id.in_(incident_ids)))
        await db.execute(delete(OperationalIncident).where(OperationalIncident.actuator_id == actuator.id))
        await db.execute(delete(Actuator).where(Actuator.id == actuator.id))
        await db.commit()


@pytest.mark.asyncio
async def test_ph_below_uses_directional_low_risk() -> None:
    _, device = await _runtime()
    async with AsyncSessionLocal() as db:
        project = await db.get(Project, device.project_id)
        assert project is not None
        await _reset_project_alert_test_state(db, project.id)
        _, incident = await _open_ph_incident(
            db,
            device=await db.get(Device, device.id),
            code_prefix="PH-BELOW",
            value=5.5,
        )
        await db.commit()
        assert incident.status == "OPEN"
        assert incident.business_risk_level_snapshot == "LOW"
        assert incident.trigger_snapshot["threshold_direction"] == "BELOW"
        assert incident.trigger_snapshot["condition_key"] == "SENSOR_PH_LOW"
        incident.status = "NORMALIZED"
        incident.normalized_at = datetime.now(UTC)
        await db.commit()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("case", "settings_kwargs", "policy_kwargs", "add_recipient", "expected_reason"),
    [
        ("disabled", {"telegram_enabled": False}, {}, True, "TELEGRAM_DISABLED"),
        ("no-recipient", {"telegram_enabled": True}, {}, False, "NO_RECIPIENT"),
        ("risk-disabled", {"telegram_enabled": True}, {"telegram_enabled": False}, True, "RISK_DISABLED"),
        ("event-disabled", {"telegram_enabled": True}, {"notify_on_open": False}, True, "EVENT_DISABLED"),
    ],
)
async def test_delivery_history_records_precise_skip_reasons(
    case: str,
    settings_kwargs: dict,
    policy_kwargs: dict,
    add_recipient: bool,
    expected_reason: str,
) -> None:
    project, device = await _runtime()
    async with AsyncSessionLocal() as db:
        await _reset_project_alert_test_state(db, project.id)
        _, incident = await _open_ph_incident(
            db,
            device=await db.get(Device, device.id),
            code_prefix=f"PH-{case.upper()}",
        )
        settings_row = ProjectNotificationSettings(
            project_id=project.id,
            enabled=True,
            in_app_enabled=True,
            telegram_enabled=settings_kwargs.get("telegram_enabled", True),
            notify_alert_opened=True,
        )
        policy = ProjectNotificationRiskPolicy(
            project_id=project.id,
            risk_level="HIGH",
            telegram_enabled=policy_kwargs.get("telegram_enabled", True),
            notify_on_open=policy_kwargs.get("notify_on_open", True),
            notify_on_escalation=True,
            notify_on_recovery=True,
            notify_on_resolved=True,
            reminder_enabled=False,
            initial_reminder_seconds=1800,
            repeat_interval_seconds=3600,
            max_reminders=0,
            stop_reminders_on_ack=True,
        )
        db.add_all([settings_row, policy])
        if add_recipient:
            db.add(ProjectNotificationRecipient(
                project_id=project.id,
                name=f"Operator {case}",
                telegram_chat_id="123456789",
                enabled=True,
            ))
        await db.commit()
        notifier = SuccessfulNotifier()
        await process_notification_outbox(db, notifier=notifier)
        outbox = await db.scalar(select(NotificationOutbox).where(
            NotificationOutbox.incident_id == incident.id,
            NotificationOutbox.event_type == "OPEN",
        ))
        assert outbox is not None
        assert outbox.status == "SKIPPED"
        assert outbox.skip_reason == expected_reason
        delivery = await db.scalar(select(NotificationDelivery).where(
            NotificationDelivery.outbox_id == outbox.id,
        ))
        assert delivery is not None
        assert delivery.status == "SKIPPED"
        assert delivery.error_category == expected_reason
        assert notifier.calls == []
        incident.status = "NORMALIZED"
        incident.normalized_at = datetime.now(UTC)
        await _clear_notification_configuration(db, project.id)
        await db.commit()


@pytest.mark.asyncio
async def test_new_recipient_gets_active_sync_without_resending_to_informed_recipient() -> None:
    project, device = await _runtime()
    async with AsyncSessionLocal() as db:
        await _reset_project_alert_test_state(db, project.id)
        _, incident = await _open_ph_incident(
            db,
            device=await db.get(Device, device.id),
            code_prefix="PH-NEW-RECIPIENT",
        )
        db.add_all([
            ProjectNotificationSettings(
                project_id=project.id,
                enabled=True,
                in_app_enabled=True,
                telegram_enabled=True,
                notify_alert_opened=True,
            ),
            ProjectNotificationRiskPolicy(
                project_id=project.id,
                risk_level="HIGH",
                telegram_enabled=True,
                notify_on_open=True,
                notify_on_escalation=True,
                notify_on_recovery=True,
                notify_on_resolved=True,
                reminder_enabled=False,
                initial_reminder_seconds=1800,
                repeat_interval_seconds=3600,
                max_reminders=0,
                stop_reminders_on_ack=True,
            ),
        ])
        old_recipient = ProjectNotificationRecipient(
            project_id=project.id,
            name="Operator old",
            telegram_chat_id="111111111",
            enabled=True,
        )
        db.add(old_recipient)
        await db.commit()
        notifier = SuccessfulNotifier()
        await process_notification_outbox(db, notifier=notifier)
        assert [call[0] for call in notifier.calls] == ["111111111"]

        new_recipient = ProjectNotificationRecipient(
            project_id=project.id,
            name="Operator new",
            telegram_chat_id="222222222",
            enabled=True,
        )
        db.add(new_recipient)
        await db.flush()
        generation = await next_notification_generation(db, project_id=project.id)
        assert await reconcile_active_incident_notifications(
            db,
            project_id=project.id,
            generation=generation,
            reason="RECIPIENT_ADDED",
            recipient_ids={new_recipient.id},
        ) == 1
        assert await reconcile_active_incident_notifications(
            db,
            project_id=project.id,
            generation=generation,
            reason="RECIPIENT_ADDED",
            recipient_ids={new_recipient.id},
        ) == 0
        await db.commit()
        await process_notification_outbox(db, notifier=notifier)
        assert [call[0] for call in notifier.calls] == ["111111111", "222222222"]
        assert await db.scalar(select(func.count(NotificationDelivery.id)).where(
            NotificationDelivery.incident_id == incident.id,
            NotificationDelivery.status == "SENT",
        )) == 2
        incident.status = "NORMALIZED"
        incident.normalized_at = datetime.now(UTC)
        await _clear_notification_configuration(db, project.id)
        await db.commit()


@pytest.mark.asyncio
async def test_system_event_without_incident_is_processed_without_dereference_error() -> None:
    project, _ = await _runtime()
    async with AsyncSessionLocal() as db:
        await _reset_project_alert_test_state(db, project.id)
        db.add_all([
            ProjectNotificationSettings(
                project_id=project.id,
                enabled=True,
                in_app_enabled=True,
                telegram_enabled=True,
            ),
            ProjectNotificationRecipient(
                project_id=project.id,
                name="Operator system event",
                telegram_chat_id="444444444",
                enabled=True,
            ),
        ])
        await enqueue_operational_event(
            db,
            project_id=project.id,
            source_key=f"test:{uuid4().hex}",
            event_type="DEVICE_STATUS",
            payload_snapshot={"message": "Thiết bị đã đổi trạng thái"},
        )
        await db.commit()
        notifier = SuccessfulNotifier()
        assert await process_notification_outbox(db, notifier=notifier) == 1
        assert len(notifier.calls) == 1
        outbox = await db.scalar(select(NotificationOutbox).where(
            NotificationOutbox.project_id == project.id,
            NotificationOutbox.source_type == "SYSTEM_EVENT",
        ))
        assert outbox is not None and outbox.status == "SENT"
        await _reset_project_alert_test_state(db, project.id)
        await db.commit()
