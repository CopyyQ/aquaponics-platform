import hashlib
import json
from datetime import UTC, datetime, timedelta

from sqlalchemy import select

from app.core.config import settings
from app.core.enums import ProjectStatus
from app.db.session import async_session_factory
from app.models.project import Project
from app.models.project_settings import ProjectNotificationSettings
from app.services.monitoring_service import get_project_monitoring_summary
from app.services.project_notification_service import (
    dispatch_project_health_message,
    format_display_time,
)


def _snapshot(summary: dict) -> dict:
    snapshot = {
        "health": summary["health"]["status"],
        "devices": summary["inventory"],
        "device_issues": [
            item for item in summary["device_health"]
            if getattr(item["status"], "value", item["status"]) == "OFFLINE"
        ],
        "sensor_issues": summary["sensor_issues"],
        "actuators": summary["actuator_inventory"],
        "actuator_issues": [
            item for item in summary["actuators"]
            if item["connection_status"] == "DISCONNECTED"
            or item["active_incident"] is not None
            or item["relevant_command_status"] in {"FAILED", "TIMEOUT", "PENDING", "PUBLISHED"}
            or item["synchronization_status"] != "IN_SYNC"
        ],
        "business_alerts": summary["business_alerts"],
    }
    return _json_safe(snapshot)


def _json_safe(value):
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, dict):
        return {key: _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    return getattr(value, "value", value)


def _fingerprint(snapshot: dict) -> str:
    payload = json.dumps(snapshot, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode()).hexdigest()


def _time(value) -> str:
    if isinstance(value, str):
        try:
            value = datetime.fromisoformat(value)
        except ValueError:
            value = None
    return format_display_time(value)


def _number(value, unit: str | None = None) -> str:
    if value is None:
        return "—"
    rendered = f"{float(value):.2f}".rstrip("0").rstrip(".").replace(".", ",")
    return f"{rendered} {unit}".rstrip() if unit else rendered


def _state(value) -> str:
    return "Bật" if value is True else "Tắt" if value is False else "Chưa xác định"


def _duration(seconds: int | None) -> str:
    total = max(0, int(seconds or 0))
    days, rest = divmod(total, 86400)
    hours, minutes = divmod(rest, 3600)[0], divmod(rest % 3600, 60)[0]
    return f"{days} ngày {hours} giờ" if days else f"{hours} giờ {minutes} phút" if hours else f"{minutes} phút"


def _append_limited(lines: list[str], items: list[dict], limit: int, render) -> None:
    for item in items[:limit]:
        lines.extend(render(item))
    remaining = len(items) - limit
    if remaining > 0:
        lines.append(f"… và {remaining} mục khác. Xem Monitoring để xem đầy đủ.")


def should_notify_health(
    *, previous_status: str | None, previous_fingerprint: str | None,
    current_status: str, current_fingerprint: str,
) -> tuple[bool, bool]:
    recovered = current_status == "HEALTHY" and previous_status not in {None, "HEALTHY"}
    degraded_changed = (
        current_status != "HEALTHY" and current_fingerprint != previous_fingerprint
    )
    return recovered or degraded_changed, recovered


def format_health_digest(project: Project, snapshot: dict, evaluated_at: datetime, recovered: bool) -> str:
    devices = snapshot["devices"]
    actuators = snapshot["actuators"]
    heading = "🟢 HỆ THỐNG ĐÃ TRỞ LẠI ỔN ĐỊNH" if recovered else "📊 TÌNH TRẠNG HỆ THỐNG"
    lines = [
        heading, "", "Dự án:", f"{project.name} ({project.code})", "",
        "──────────────", "THIẾT BỊ", "──────────────", "",
        f"🟢 Kết nối: {devices['devices_online']}/{devices['devices_total']}",
        f"🔴 Mất kết nối: {devices['devices_offline']}",
        f"🟡 Chờ kết nối: {devices['devices_waiting']}", "",
    ]
    if snapshot["device_issues"]:
        lines.append("Thiết bị mất kết nối:")
        _append_limited(lines, snapshot["device_issues"], settings.health_report_device_issue_limit, lambda item: [
            f"• {item['name']}", f"  Mã: {item['code']}", f"  Dữ liệu cuối: {_time(item.get('last_seen_at'))}",
            f"  Ảnh hưởng: {item.get('sensor_count', 0)} cảm biến" + (f"; {item['actuator_count']} cơ cấu chấp hành" if item.get('actuator_count') else ""),
        ])
    lines.extend([
        "", "──────────────", "CẢM BIẾN", "──────────────", "",
        f"🟢 Có dữ liệu mới: {devices['sensors_reporting']}",
        f"🟠 Dữ liệu cũ: {devices['sensors_stale']}",
        f"🔴 Mất dữ liệu: {devices['sensors_offline']}", "",
    ])
    if snapshot["sensor_issues"]:
        lines.append("Dữ liệu cần chú ý:")
        _append_limited(lines, snapshot["sensor_issues"], settings.health_report_sensor_issue_limit, lambda item: [
            f"• {item['name']}", f"  Mã: {item['code']}",
            f"  Thiết bị: {item['device_name']} ({item['device_code']})",
            f"  Trạng thái dữ liệu: {'Mất dữ liệu mới' if item.get('connection_lost') else 'Dữ liệu cũ' if item['freshness'] == 'STALE' else 'Mất dữ liệu'}",
            f"  Giá trị cuối: {_number(item.get('value'), item.get('unit'))}",
            f"  Đo lần cuối: {_time(item.get('recorded_at'))}", f"  Nhận lần cuối: {_time(item.get('received_at'))}",
        ])
    lines.extend([
        "", "──────────────", "CƠ CẤU CHẤP HÀNH", "──────────────", "",
        f"🟢 Bình thường: {actuators['responding']}",
        f"🟡 Chờ/không đồng bộ: {actuators['out_of_sync']}",
        f"🔴 Lỗi: {actuators['failed']}", "",
    ])
    if snapshot["actuator_issues"]:
        command_labels = {"PENDING": "Đang chờ", "PUBLISHED": "Đã gửi", "ACKNOWLEDGED": "Đã xác nhận", "FAILED": "Thất bại", "TIMEOUT": "Hết thời gian chờ"}
        sync_labels = {"IN_SYNC": "Đã đồng bộ", "OUT_OF_SYNC": "Chưa đồng bộ", "PENDING": "Đang chờ đồng bộ", "UNKNOWN": "Chưa xác định"}
        def actuator_lines(item):
            result = [f"• {item['name']}", f"  Mã: {item['code']}", f"  Thiết bị: {item['device_name']} ({item['device_code']})", f"  Yêu cầu: {_state(item.get('desired_state'))}", f"  Báo về: {_state(item.get('reported_state'))}", f"  Trạng thái: {sync_labels.get(item['synchronization_status'], 'Chưa xác định')}", f"  Lệnh gần nhất: {command_labels.get(item.get('command_status'), 'Chưa có lệnh')}", f"  Cập nhật cuối: {_time(item.get('last_reported_at'))}"]
            electrical = item.get("electrical") or {}
            for key, label in (("voltage", "Điện áp"), ("current", "Dòng điện")):
                metric = electrical.get(key) or {}
                if metric.get("configured"):
                    result.append(f"  {label}: {_number(metric.get('value'), metric.get('unit'))}")
            return result
        lines.append("Chi tiết bất thường:")
        _append_limited(lines, snapshot["actuator_issues"], settings.health_report_actuator_issue_limit, actuator_lines)
    business = snapshot["business_alerts"]
    risks = (("EXTREME", "🔴", "Cực cao"), ("VERY_HIGH", "🟠", "Rất cao"), ("HIGH", "🟠", "Cao"), ("MEDIUM", "🟡", "Trung bình"), ("LOW_MEDIUM", "🟢", "Thấp–trung bình"), ("LOW", "🟢", "Thấp"))
    lines.extend(["", "──────────────", "CẢNH BÁO ĐANG MỞ", "──────────────", ""])
    if not any(business["counts"].values()):
        lines.append("Không có cảnh báo nghiệp vụ đang mở.")
    else:
        lines.extend(f"{icon} {label}: {business['counts'].get(code, 0)}" for code, icon, label in risks)
        risk_labels = {code: (icon, label) for code, icon, label in risks}
        def incident_lines(item):
            icon, label = risk_labels.get(item.get("risk"), ("🟡", "Chưa phân loại"))
            result = ["", f"• {icon} {label} — {item['rule_name']}"]
            if item.get("device_name"): result.append(f"  Thiết bị: {item['device_name']} ({item.get('device_code') or '—'})")
            if item.get("sensor_name"): result.extend([f"  Cảm biến: {item['sensor_name']}", f"  Mã: {item.get('sensor_code') or '—'}", f"  Giá trị: {_number(item.get('value'), item.get('unit'))}"])
            if item.get("actuator_name"): result.extend([f"  Cơ cấu chấp hành: {item['actuator_name']}", f"  Mã: {item.get('actuator_code') or '—'}", f"  Yêu cầu: {_state(item.get('desired_state'))}", f"  Báo về: {_state(item.get('reported_state'))}", f"  Dòng điện: {_number(item.get('current_a'), 'A')}"])
            result.extend([f"  Điều kiện: {item['condition']}", f"  Bắt đầu: {_time(item.get('started_at'))}", f"  Đã kéo dài: {_duration(item.get('duration_seconds'))}", f"  Nội dung: {item['message']}"])
            return result
        lines.append("Chi tiết:")
        _append_limited(lines, business["items"], settings.health_report_incident_limit, incident_lines)
    lines.extend(["", "──────────────", "", f"Cập nhật: {format_display_time(evaluated_at)}"])
    message = "\n".join(lines)
    if len(message) > 3900:
        message = message[:3850].rsplit("\n", 1)[0] + "\n… Xem Monitoring để xem đầy đủ."
    return message


async def evaluate_project_health() -> int:
    now = datetime.now(UTC)
    notified = 0
    async with async_session_factory() as db:
        projects = list(
            (
                await db.scalars(
                    select(Project).where(
                        Project.status == ProjectStatus.ACTIVE,
                        Project.is_deleted.is_(False),
                        Project.deleted_at.is_(None),
                    )
                )
            ).all()
        )
        for project in projects:
            notification_settings = await db.scalar(
                select(ProjectNotificationSettings).where(
                    ProjectNotificationSettings.project_id == project.id
                )
            )
            if notification_settings is None:
                notification_settings = ProjectNotificationSettings(project_id=project.id)
                db.add(notification_settings)
                await db.flush()
            if (
                notification_settings.last_health_evaluated_at is not None
                and notification_settings.last_health_evaluated_at
                > now - timedelta(seconds=settings.project_health_interval_seconds - 5)
            ):
                continue
            summary = await get_project_monitoring_summary(
                db, project.id, project_status=project.status
            )
            snapshot = _snapshot(summary)
            fingerprint = _fingerprint(snapshot)
            previous_status = notification_settings.last_health_status
            current_status = str(snapshot["health"])
            should_notify, recovered = should_notify_health(
                previous_status=previous_status,
                previous_fingerprint=notification_settings.last_health_fingerprint,
                current_status=current_status,
                current_fingerprint=fingerprint,
            )
            notification_settings.last_health_status = current_status
            notification_settings.last_health_fingerprint = fingerprint
            notification_settings.last_health_snapshot = snapshot
            notification_settings.last_health_evaluated_at = now
            if should_notify:
                notification_settings.last_health_notified_at = now
            await db.commit()
            if should_notify:
                await dispatch_project_health_message(
                    db,
                    project_id=project.id,
                    message=format_health_digest(project, snapshot, now, recovered),
                )
                notified += 1
    return notified
