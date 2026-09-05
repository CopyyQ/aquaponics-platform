from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import delete, func, select
from test_visibility_authorization import visibility_data  # noqa: F401

from app.core.config import settings
from app.core.enums import AlertSeverity, AlertStatus, AlertType, DeviceStatus, SensorStatus
from app.db.session import AsyncSessionLocal
from app.jobs.actuator_command_timeout import timeout_actuator_commands
from app.jobs.offline_scanner import scan_offline_state
from app.jobs.project_health_evaluator import should_notify_health
from app.models.actuator import Actuator, ActuatorCommand
from app.models.alert import SensorAlert
from app.models.audit import AuditLog
from app.models.device import Device
from app.models.project import Project
from app.models.sensor import Sensor, SensorModel
from app.models.user import User
from app.mqtt.schemas import MqttStatusPayload
from app.services.device_status_service import update_device_status
from app.services.project_activity_service import format_project_activity_message
from app.services.project_notification_service import format_alert_message, format_display_time


def test_vietnamese_timezone_and_operational_payloads_are_explicit() -> None:
    occurred_at = datetime(2026, 8, 17, 4, 12, tzinfo=UTC)
    assert format_display_time(occurred_at) == "17/08/2026 11:12:00 (Asia/Ho_Chi_Minh)"

    sensor = Sensor(
        id=1, device_id=1, sensor_model_id=1, code="PH", name="pH",
        lower_threshold=6.5, upper_threshold=8.5, warning_enabled=True,
    )
    model = SensorModel(id=1, code="PH", name="pH", unit="pH")
    alert = SensorAlert(
        id=1, sensor_id=1, alert_type=AlertType.ABOVE_UPPER_THRESHOLD,
        severity=AlertSeverity.WARNING, status=AlertStatus.OPEN,
        condition_active=True, message="pH vượt ngưỡng trên 8.5",
        trigger_value=8.7, started_at=occurred_at, last_triggered_at=occurred_at,
        occurrence_count=2,
    )
    message = format_alert_message(
        transition="OPENED", project_name="Dự án cá trê", project_code="TB-0015",
        alert=alert, sensor=sensor, sensor_model=model, device_name="Thiết bị môi trường",
    )
    assert "Giá trị hiện tại: 8.7 pH" in message
    assert "Ngưỡng tối đa: 8.5 pH" in message
    assert "Vượt ngưỡng: +0.2 pH" in message
    assert "Lần cảnh báo trong sự cố này: 2" in message


def test_activity_time_and_actuator_desired_reported_semantics() -> None:
    occurred_at = datetime(2026, 8, 17, 4, 12, tzinfo=UTC)
    project = Project(id=1, owner_user_id=1, code="TB-0015", name="Dự án cá trê")
    actor = User(id=1, username="operator", full_name="Nguyễn Văn A")
    activity = AuditLog(
        id=1, user_id=1, project_id=1, action="ACTUATOR_COMMAND_REQUESTED",
        entity_type="ACTUATOR", entity_id=2, description="Yêu cầu lệnh",
        new_data={"display_name": "Bơm tuần hoàn", "changes": {
            "desired_state": {"before": False, "after": True},
            "command_status": {"before": None, "after": "PENDING"},
        }}, created_at=occurred_at,
    )
    message = format_project_activity_message(activity, project, actor)
    assert "Trạng thái yêu cầu: ON" in message
    assert "Trạng thái thiết bị báo về: OFF" in message
    assert "Đang chờ xác nhận" in message
    assert "2026-08-17T04:12" not in message
    assert "17/08/2026 11:12:00" in message


def test_health_policy_suppresses_unchanged_and_sends_recovery() -> None:
    assert should_notify_health(
        previous_status=None, previous_fingerprint=None,
        current_status="HEALTHY", current_fingerprint="healthy",
    ) == (False, False)
    assert should_notify_health(
        previous_status=None, previous_fingerprint=None,
        current_status="WARNING", current_fingerprint="degraded",
    ) == (True, False)
    assert should_notify_health(
        previous_status="WARNING", previous_fingerprint="degraded",
        current_status="WARNING", current_fingerprint="degraded",
    ) == (False, False)
    assert should_notify_health(
        previous_status="WARNING", previous_fingerprint="degraded",
        current_status="HEALTHY", current_fingerprint="healthy",
    ) == (True, True)


@pytest.mark.asyncio
async def test_device_disconnect_is_one_transition_and_suppresses_child_alerts(
    visibility_data, monkeypatch,
) -> None:
    data = visibility_data
    calls: list[tuple[int, str]] = []

    async def capture(_db, *, device_id: int, transition: str, **_kwargs) -> None:
        if device_id == data["active_device"]:
            calls.append((device_id, transition))

    async def suppress_alert(*_args, **_kwargs) -> None:
        return None

    monkeypatch.setattr("app.jobs.offline_scanner.dispatch_device_connectivity_transition", capture)
    monkeypatch.setattr("app.jobs.offline_scanner.dispatch_alert_transition", suppress_alert)
    stale_at = datetime.now(UTC) - timedelta(seconds=settings.device_offline_seconds + 30)
    async with AsyncSessionLocal() as db:
        device = await db.get(Device, data["active_device"])
        sensor = await db.get(Sensor, data["active_sensor"])
        assert device is not None and sensor is not None
        device.status = DeviceStatus.ONLINE
        device.last_seen_at = stale_at
        device.disconnected_at = None
        sensor.status = SensorStatus.ONLINE
        sensor.last_seen_at = stale_at
        await db.execute(delete(SensorAlert).where(
            SensorAlert.sensor_id == sensor.id,
            SensorAlert.alert_type == AlertType.SENSOR_OFFLINE,
        ))
        await db.commit()

    await scan_offline_state()
    await scan_offline_state()
    assert calls == [(data["active_device"], "DISCONNECTED")]
    async with AsyncSessionLocal() as db:
        count = int(await db.scalar(select(func.count(SensorAlert.id)).where(
            SensorAlert.sensor_id == data["active_sensor"],
            SensorAlert.alert_type == AlertType.SENSOR_OFFLINE,
        )) or 0)
        assert count == 0


@pytest.mark.asyncio
async def test_device_reconnect_is_one_transition(visibility_data, monkeypatch) -> None:
    data = visibility_data
    calls: list[str] = []

    async def capture(_db, *, transition: str, **_kwargs) -> None:
        calls.append(transition)

    monkeypatch.setattr(
        "app.services.device_status_service.dispatch_device_connectivity_transition", capture
    )
    now = datetime.now(UTC)
    async with AsyncSessionLocal() as db:
        device = await db.get(Device, data["active_device"])
        assert device is not None
        device.status = DeviceStatus.OFFLINE
        device.disconnected_at = now - timedelta(minutes=3)
        await db.commit()
        payload = MqttStatusPayload(status="ONLINE", sent_at=now, actuators=[])
        assert await update_device_status(db, device_code=device.code, payload=payload, received_at=now)
        assert await update_device_status(db, device_code=device.code, payload=payload, received_at=now)
    assert calls == ["RECONNECTED"]


@pytest.mark.asyncio
async def test_actuator_timeout_is_persisted_and_emitted_once(visibility_data, monkeypatch) -> None:
    data = visibility_data
    calls: list[tuple[int, str]] = []

    async def capture(_db, *, command_id: int, transition: str, **_kwargs) -> None:
        calls.append((command_id, transition))

    monkeypatch.setattr(
        "app.jobs.actuator_command_timeout.dispatch_actuator_command_transition", capture
    )
    async with AsyncSessionLocal() as db:
        actuator = Actuator(
            device_id=data["active_device"], sequence_number=99, code="P0-PUMP",
            name="Bơm P0", is_enabled=True, desired_state=True, reported_state=False,
        )
        db.add(actuator)
        await db.flush()
        command = ActuatorCommand(
            actuator_id=actuator.id, desired_state=True, reported_state=False,
            status="PUBLISHED", requested_by_user_id=data["admin_id"],
            requested_at=datetime.now(UTC) - timedelta(seconds=settings.actuator_command_timeout_seconds + 5),
        )
        db.add(command)
        await db.commit()
        command_id = command.id
        actuator_id = actuator.id

    await timeout_actuator_commands()
    await timeout_actuator_commands()
    assert calls == [(command_id, "TIMEOUT")]
    async with AsyncSessionLocal() as db:
        command = await db.get(ActuatorCommand, command_id)
        assert command is not None and command.status == "TIMEOUT"
        await db.execute(delete(AuditLog).where(
            AuditLog.action == "ACTUATOR_COMMAND_TIMEOUT",
            AuditLog.entity_id == actuator_id,
        ))
        await db.execute(delete(ActuatorCommand).where(ActuatorCommand.id == command_id))
        await db.execute(delete(Actuator).where(Actuator.id == actuator_id))
        await db.commit()
