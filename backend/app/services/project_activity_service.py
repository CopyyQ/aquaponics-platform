import logging
from datetime import datetime
from typing import Any

from fastapi.encoders import jsonable_encoder
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit import AuditLog
from app.models.project import Project
from app.models.user import User
from app.services.audit_service import write_audit
from app.services.notification_outbox_service import enqueue_project_activity_notification

logger = logging.getLogger(__name__)


def format_display_time(value: datetime | None) -> str:
    if value is None:
        return "—"
    return value.astimezone().strftime("%d/%m/%Y %H:%M:%S")

ACTION_LABELS = {
    "PROJECT_CREATED": "Tạo dự án",
    "PROJECT_UPDATED": "Cập nhật dự án",
    "PROJECT_DISABLED": "Vô hiệu hóa dự án",
    "PROJECT_ENABLED": "Kích hoạt lại dự án",
    "DEVICE_ADDED": "Thêm thiết bị",
    "DEVICE_UPDATED": "Cập nhật thiết bị",
    "DEVICE_DISABLED": "Vô hiệu hóa thiết bị",
    "DEVICE_ENABLED": "Kích hoạt thiết bị",
    "DEVICE_REMOVED": "Xóa thiết bị",
    "SENSOR_ADDED": "Thêm cảm biến",
    "SENSOR_UPDATED": "Cập nhật cảm biến",
    "SENSOR_DISABLED": "Vô hiệu hóa cảm biến",
    "SENSOR_ENABLED": "Kích hoạt cảm biến",
    "ACTUATOR_COMMAND_REQUESTED": "Yêu cầu lệnh điều khiển",
    "SCADA_LAYOUT_UPDATED": "Lưu sơ đồ vận hành",
    "SCADA_LAYOUT_PUBLISHED": "Xuất bản sơ đồ vận hành",
    "MEMBER_ADDED": "Thêm thành viên",
    "MEMBER_UPDATED": "Cập nhật thành viên",
    "MEMBER_REMOVED": "Xóa thành viên",
    "NOTIFICATION_SETTINGS_UPDATED": "Cập nhật cấu hình thông báo",
    "NOTIFICATION_RECIPIENT_ADDED": "Thêm người nhận thông báo",
    "NOTIFICATION_RECIPIENT_UPDATED": "Cập nhật người nhận thông báo",
    "NOTIFICATION_RECIPIENT_ENABLED": "Bật người nhận thông báo",
    "NOTIFICATION_RECIPIENT_DISABLED": "Tắt người nhận thông báo",
    "NOTIFICATION_RECIPIENT_REMOVED": "Xóa người nhận thông báo",
    "REMOTE_MONITORING_ENABLED": "Bật theo dõi từ xa",
    "REMOTE_MONITORING_DISABLED": "Tắt theo dõi từ xa",
    "ALERT_RESOLVED": "Xác nhận đã khắc phục cảnh báo",
}

HEADINGS = {
    "PROJECT_DISABLED": "⏸️ DỰ ÁN ĐÃ BỊ VÔ HIỆU HÓA",
    "PROJECT_ENABLED": "▶️ DỰ ÁN ĐÃ ĐƯỢC KÍCH HOẠT LẠI",
    "PROJECT_UPDATED": "✏️ CẬP NHẬT DỰ ÁN",
    "DEVICE_ADDED": "➕ THÊM THIẾT BỊ",
    "DEVICE_UPDATED": "✏️ CẬP NHẬT THIẾT BỊ",
    "SENSOR_UPDATED": "🌡️ CẬP NHẬT CẢM BIẾN",
    "ACTUATOR_COMMAND_REQUESTED": "🎛️ LỆNH ĐIỀU KHIỂN",
    "SCADA_LAYOUT_UPDATED": "🗺️ SƠ ĐỒ VẬN HÀNH ĐÃ ĐƯỢC CẬP NHẬT",
    "SCADA_LAYOUT_PUBLISHED": "🗺️ SƠ ĐỒ VẬN HÀNH ĐÃ ĐƯỢC XUẤT BẢN",
    "MEMBER_ADDED": "👤 THAY ĐỔI THÀNH VIÊN",
    "MEMBER_UPDATED": "👤 THAY ĐỔI THÀNH VIÊN",
    "MEMBER_REMOVED": "👤 THAY ĐỔI THÀNH VIÊN",
    "NOTIFICATION_RECIPIENT_ADDED": "📨 CẬP NHẬT NGƯỜI NHẬN THÔNG BÁO",
    "NOTIFICATION_RECIPIENT_UPDATED": "📨 CẬP NHẬT NGƯỜI NHẬN THÔNG BÁO",
    "NOTIFICATION_RECIPIENT_REMOVED": "📨 CẬP NHẬT NGƯỜI NHẬN THÔNG BÁO",
    "ALERT_RESOLVED": "✅ XÁC NHẬN KHẮC PHỤC CẢNH BÁO",
}


async def record_project_activity(
    db: AsyncSession,
    *,
    project_id: int,
    actor: User,
    action: str,
    entity_type: str,
    entity_id: int | None,
    entity_name: str,
    changes: dict[str, Any] | None = None,
) -> AuditLog:
    return await write_audit(
        db,
        user_id=actor.id,
        project_id=project_id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        description=ACTION_LABELS.get(action, action),
        new_data={"display_name": entity_name, "changes": jsonable_encoder(changes or {})},
    )


def format_project_activity_message(activity: AuditLog, project: Project, actor: User | None) -> str:
    actor_name = actor.full_name or actor.username if actor else f"User #{activity.user_id}"
    metadata = activity.new_data or {}
    entity_name = str(metadata.get("display_name") or f"#{activity.entity_id}")
    changes = metadata.get("changes") if isinstance(metadata.get("changes"), dict) else {}
    changed_fields = [str(field).replace("_", " ") for field in changes]
    lines = [
        HEADINGS.get(activity.action, f"ℹ️ {ACTION_LABELS.get(activity.action, activity.action).upper()}"),
        "",
        f"Dự án: {project.name}",
        f"Mã: {project.code}",
        "",
        f"Đối tượng: {entity_name}",
        f"Thực hiện bởi: {actor_name}",
        f"Thao tác: {ACTION_LABELS.get(activity.action, activity.action)}",
    ]
    if changed_fields:
        lines.extend(["", "Đã thay đổi:", *[f"• {field}" for field in changed_fields]])
    if activity.action == "ACTUATOR_COMMAND_REQUESTED":
        desired = changes.get("desired_state", {}).get("after") if isinstance(changes.get("desired_state"), dict) else None
        reported = changes.get("desired_state", {}).get("before") if isinstance(changes.get("desired_state"), dict) else None
        lines.extend(
            [
                "",
                f"Trạng thái yêu cầu: {'ON' if desired is True else 'OFF' if desired is False else '—'}",
                f"Trạng thái thiết bị báo về: {'ON' if reported is True else 'OFF' if reported is False else '—'}",
                "Trạng thái lệnh: Đang chờ xác nhận",
                "Không coi lệnh là thành công cho đến khi thiết bị ACK/report.",
            ]
        )
    lines.extend(["", f"Thời gian: {format_display_time(activity.created_at if isinstance(activity.created_at, datetime) else None)}"])
    return "\n".join(lines)


async def dispatch_project_activity(
    db: AsyncSession,
    *,
    activity_id: int,
) -> None:
    row = (
        await db.execute(
            select(AuditLog, Project, User)
            .join(Project, Project.id == AuditLog.project_id)
            .outerjoin(User, User.id == AuditLog.user_id)
            .where(AuditLog.id == activity_id)
        )
    ).first()
    if row is None:
        return
    activity, project, actor = row
    message = format_project_activity_message(activity, project, actor)
    await enqueue_project_activity_notification(
        db,
        project_id=project.id,
        activity_id=activity.id,
        payload_snapshot={
            "message": message,
            "project_name": project.name,
            "project_code": project.code,
            "recorded_at": activity.created_at.isoformat() if activity.created_at else None,
        },
    )
    # Existing callers record and commit the audit row first. Commit the
    # durable event here; duplicate calls are harmless due to its key.
    await db.commit()


async def list_project_activities(db: AsyncSession, *, project_id: int, page: int, page_size: int, action: str | None, entity_type: str | None) -> tuple[list[AuditLog], int]:
    filters = [AuditLog.project_id == project_id]
    if action:
        filters.append(AuditLog.action == action)
    if entity_type:
        filters.append(AuditLog.entity_type == entity_type)
    total = int(await db.scalar(select(func.count(AuditLog.id)).where(*filters)) or 0)
    items = list((await db.scalars(select(AuditLog).where(*filters).order_by(AuditLog.created_at.desc()).offset((page - 1) * page_size).limit(page_size))).all())
    return items, total
