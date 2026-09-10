"""Compatibility dispatchers for non-threshold operational events.

Threshold meaning belongs to ThresholdAlertConfig and OperationalIncident.
This module never calls Telegram; it only queues non-threshold events.
"""
from __future__ import annotations

from datetime import UTC, datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.actuator import Actuator, ActuatorCommand
from app.models.device import Device
from app.models.project import Project
from app.models.user import User
from app.services.notification_outbox_service import enqueue_operational_event


def format_display_time(value: datetime | None) -> str:
    if not isinstance(value, datetime):
        return "—"
    try:
        zone = ZoneInfo(settings.display_timezone)
    except ZoneInfoNotFoundError:
        zone = ZoneInfo("UTC")
    return f"{value.astimezone(zone).strftime('%d/%m/%Y %H:%M:%S')} ({settings.display_timezone})"


def _state(value: bool | None) -> str:
    return "Bật" if value is True else "Tắt" if value is False else "Chưa xác định"


async def dispatch_device_connectivity_transition(
    db: AsyncSession, *, device_id: int, transition: str, occurred_at: datetime | None = None, **_: object
) -> None:
    if transition not in {"DISCONNECTED", "RECONNECTED"}:
        return
    row = (await db.execute(select(Device, Project).join(Project, Project.id == Device.project_id).where(Device.id == device_id))).first()
    if row is None:
        return
    device, project = row
    at = occurred_at or datetime.now(UTC)
    heading = "🔌 THIẾT BỊ MẤT KẾT NỐI" if transition == "DISCONNECTED" else "🟢 THIẾT BỊ ĐÃ KẾT NỐI LẠI"
    text = "\n".join((heading, "", f"Dự án: {project.name} ({project.code})", f"Thiết bị: {device.name}", f"Thời gian: {format_display_time(at)}"))
    await enqueue_operational_event(db, project_id=project.id, source_key=f"device:{device.id}:{transition}:{at.isoformat()}", event_type=f"DEVICE_{transition}", payload_snapshot={"message": text})
    await db.commit()


async def dispatch_actuator_command_transition(
    db: AsyncSession, *, command_id: int, transition: str, **_: object
) -> None:
    if transition not in {"ACKNOWLEDGED", "FAILED", "TIMEOUT"}:
        return
    row = (await db.execute(select(ActuatorCommand, Actuator, Device, Project, User).join(Actuator, Actuator.id == ActuatorCommand.actuator_id).join(Device, Device.id == Actuator.device_id).join(Project, Project.id == Device.project_id).outerjoin(User, User.id == ActuatorCommand.requested_by_user_id).where(ActuatorCommand.id == command_id))).first()
    if row is None:
        return
    command, actuator, device, project, actor = row
    at = command.acknowledged_at or command.failed_at or command.timed_out_at or datetime.now(UTC)
    heading = {"ACKNOWLEDGED": "🟢 LỆNH ĐÃ ĐƯỢC XÁC NHẬN", "FAILED": "🔴 LỆNH ĐIỀU KHIỂN THẤT BẠI", "TIMEOUT": "🔴 LỆNH ĐIỀU KHIỂN HẾT THỜI GIAN CHỜ"}[transition]
    actor_name = (actor.full_name or actor.username) if actor else "—"
    text = "\n".join((heading, "", f"Dự án: {project.name} ({project.code})", f"Thiết bị: {device.name}", f"Cơ cấu chấp hành: {actuator.name}", f"Yêu cầu: {_state(command.desired_state)}", f"Báo về: {_state(command.reported_state)}", f"Người thực hiện: {actor_name}", f"Thời gian: {format_display_time(at)}"))
    await enqueue_operational_event(db, project_id=project.id, source_key=f"command:{command.id}:{transition}", event_type=f"ACTUATOR_{transition}", payload_snapshot={"message": text})
    await db.commit()


async def dispatch_project_health_message(db: AsyncSession, *, project_id: int, message: str, **_: object) -> None:
    await enqueue_operational_event(db, project_id=project_id, source_key=f"project-health:{project_id}:{message}", event_type="PROJECT_HEALTH", payload_snapshot={"message": message})
    await db.commit()


async def dispatch_alert_transition(*_: object, **__: object) -> None:
    """Retired legacy SensorAlert dispatcher; canonical alerts use incidents."""
    return None
