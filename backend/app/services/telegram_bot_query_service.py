from __future__ import annotations

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.project import Project
from app.models.project_settings import ProjectNotificationRecipient
from app.services.monitoring_service import get_project_monitoring_summary
from app.services.project_notification_service import format_display_time

ACTIVE_INCIDENT_STATUSES = {"PENDING", "OPEN", "ACKNOWLEDGED"}
RISK_ICONS = {
    "EXTREME": "🔴",
    "VERY_HIGH": "🟠",
    "HIGH": "🟠",
    "MEDIUM": "🟡",
    "LOW_MEDIUM": "🟢",
    "LOW": "🟢",
}


def telegram_action_keyboard(project_id: int, *, view: str | None = None) -> dict:
    rows = [[
        {"text": "🚨 Cảnh báo hiện tại", "callback_data": f"a:{project_id}"},
        {"text": "📊 Tình trạng hệ thống", "callback_data": f"s:{project_id}"},
    ]]
    if view in {"a", "s"}:
        rows.append([{"text": "🔄 Làm mới", "callback_data": f"r:{view}:{project_id}"}])
    return {"inline_keyboard": rows}


def project_picker_keyboard(projects: list[Project]) -> dict:
    return {
        "inline_keyboard": [
            [{"text": f"{project.code} — {project.name}", "callback_data": f"m:{project.id}"}]
            for project in projects[:20]
        ]
    }


async def list_authorized_projects(db: AsyncSession, chat_id: str) -> list[Project]:
    return list((await db.scalars(
        select(Project)
        .join(ProjectNotificationRecipient, ProjectNotificationRecipient.project_id == Project.id)
        .where(
            ProjectNotificationRecipient.telegram_chat_id == str(chat_id),
            ProjectNotificationRecipient.enabled.is_(True),
            Project.is_deleted.is_(False),
        )
        .order_by(Project.code, Project.id)
    )).all())


async def authorized_project(
    db: AsyncSession, *, chat_id: str, project_id: int
) -> Project | None:
    return await db.scalar(
        select(Project)
        .join(ProjectNotificationRecipient, ProjectNotificationRecipient.project_id == Project.id)
        .where(
            Project.id == project_id,
            ProjectNotificationRecipient.telegram_chat_id == str(chat_id),
            ProjectNotificationRecipient.enabled.is_(True),
            Project.is_deleted.is_(False),
        )
        .limit(1)
    )


def _number(value: object, unit: str | None = None) -> str:
    if not isinstance(value, (float, int)):
        return "—"
    rendered = f"{float(value):.3f}".rstrip("0").rstrip(".").replace(".", ",")
    return f"{rendered} {unit}".strip() if unit else rendered


def _state(value: object) -> str:
    return "Bật" if value is True else "Tắt" if value is False else "—"


def _time(value: object) -> str:
    return format_display_time(value if isinstance(value, datetime) else None)


def format_active_alerts(project: Project, summary: dict, *, limit: int = 10) -> str:
    business = summary.get("business_alerts") or {}
    items = list(business.get("items") or [])
    lines = [
        f"🚨 CẢNH BÁO HIỆN TẠI — {len(items)}",
        "",
        f"Hệ thống: {project.name} ({project.code})",
    ]
    if not items:
        lines.extend(["", "✅ Hiện không có cảnh báo đang hoạt động."])
        return "\n".join(lines)

    for index, item in enumerate(items[:limit], start=1):
        risk = str(item.get("risk") or "MEDIUM")
        lines.extend([
            "",
            f"{index}. {RISK_ICONS.get(risk, '🟡')} {item.get('rule_name') or 'Cảnh báo'}",
        ])
        if item.get("device_name"):
            lines.append(f"   Thiết bị: {item['device_name']}")
        if item.get("sensor_name"):
            lines.append(f"   Cảm biến: {item['sensor_name']}")
            lines.append(f"   Giá trị: {_number(item.get('value'), item.get('unit'))}")
        elif item.get("actuator_name"):
            lines.append(f"   Cơ cấu: {item['actuator_name']}")
            lines.append(
                f"   Yêu cầu/Báo về: {_state(item.get('desired_state'))}/{_state(item.get('reported_state'))}"
            )
            if item.get("current_a") is not None:
                lines.append(f"   Dòng điện: {_number(item.get('current_a'), 'A')}")
        if item.get("started_at"):
            lines.append(f"   Bắt đầu: {_time(item.get('started_at'))}")
    if len(items) > limit:
        lines.extend(["", f"… và {len(items) - limit} cảnh báo khác."])
    return "\n".join(lines)


def format_system_status(project: Project, summary: dict) -> str:
    inventory = summary.get("inventory") or {}
    actuators = summary.get("actuator_inventory") or {}
    business = summary.get("business_alerts") or {}
    counts = business.get("counts") or {}
    active_alerts = sum(int(value or 0) for value in counts.values())
    health = summary.get("health") or {}
    updated_at = (summary.get("freshness") or {}).get("last_received_at")
    return "\n".join([
        "📊 TÌNH TRẠNG HỆ THỐNG",
        "",
        f"Hệ thống: {project.name} ({project.code})",
        f"Trạng thái: {health.get('label') or health.get('status') or '—'}",
        "",
        "THIẾT BỊ",
        f"🟢 Online: {inventory.get('devices_online', 0)}/{inventory.get('devices_total', 0)}",
        f"🔴 Offline: {inventory.get('devices_offline', 0)}",
        f"🟡 Chờ kết nối: {inventory.get('devices_waiting', 0)}",
        "",
        "CẢM BIẾN",
        f"🟢 Có dữ liệu mới: {inventory.get('sensors_reporting', 0)}",
        f"🟠 Dữ liệu cũ: {inventory.get('sensors_stale', 0)}",
        f"🔴 Mất dữ liệu: {inventory.get('sensors_offline', 0)}",
        "",
        "CƠ CẤU CHẤP HÀNH",
        f"🟢 Bình thường: {actuators.get('responding', 0)}",
        f"🟡 Chưa đồng bộ: {actuators.get('out_of_sync', 0)}",
        f"🔴 Lỗi: {actuators.get('failed', 0)}",
        "",
        f"🚨 Cảnh báo đang mở: {active_alerts}",
        f"Cập nhật dữ liệu: {_time(updated_at)}",
    ])


async def render_project_view(
    db: AsyncSession, *, chat_id: str, project_id: int, view: str
) -> tuple[str, dict] | None:
    project = await authorized_project(db, chat_id=chat_id, project_id=project_id)
    if project is None:
        return None
    summary = await get_project_monitoring_summary(
        db, project.id, project_status=project.status
    )
    if view == "a":
        return format_active_alerts(project, summary), telegram_action_keyboard(project.id, view="a")
    return format_system_status(project, summary), telegram_action_keyboard(project.id, view="s")
