from __future__ import annotations

from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.device import Device
from app.models.operational_alert import (
    NotificationDelivery,
    NotificationOutbox,
    OperationalIncident,
)
from app.models.project_settings import (
    ProjectNotificationRecipient,
    ProjectNotificationRiskPolicy,
    ProjectNotificationSettings,
)
from app.services.telegram_notifier import TelegramNotifier

RISK_LABELS = {"EXTREME": "CỰC CAO", "VERY_HIGH": "RẤT CAO", "HIGH": "CAO", "MEDIUM": "TRUNG BÌNH", "LOW_MEDIUM": "THẤP–TRUNG BÌNH", "LOW": "THẤP"}
RISK_ORDER = {"LOW": 0, "LOW_MEDIUM": 1, "MEDIUM": 2, "HIGH": 3, "VERY_HIGH": 4, "EXTREME": 5}
RISK_SETTING_FIELDS = {
    "EXTREME": "risk_extreme_enabled",
    "VERY_HIGH": "risk_very_high_enabled",
    "HIGH": "risk_high_enabled",
    "MEDIUM": "risk_medium_enabled",
    "LOW_MEDIUM": "risk_low_medium_enabled",
    "LOW": "risk_low_enabled",
}
QUALITY_LABELS = {"VALID": "Hợp lệ", "OUT_OF_RANGE": "Ngoài phạm vi", "INVALID": "Không hợp lệ", "UNVALIDATED": "Chưa được xác thực", "STALE": "Dữ liệu cũ", "NO_DATA": "Không có dữ liệu"}
COMMAND_LABELS = {"ACKNOWLEDGED": "Đã xác nhận", "FAILED": "Thất bại", "TIMEOUT": "Hết thời gian chờ", "PUBLISHED": "Đã gửi lệnh", "PENDING": "Đang chờ gửi"}
OPERATOR_LABELS = {"LT": "<", "LTE": "≤", "GT": ">", "GTE": "≥", "EQ": "=", "OUTSIDE": "ngoài"}


def _number(value: object, digits: int = 3) -> str:
    if not isinstance(value, (float, int)):
        return "—"
    return f"{value:.{digits}f}".rstrip("0").rstrip(".").replace(".", ",")


def _display_datetime(value: object) -> str:
    if not isinstance(value, str):
        return "—"
    try:
        parsed = datetime.fromisoformat(value)
        return parsed.astimezone(ZoneInfo(settings.display_timezone)).strftime("%d/%m/%Y %H:%M:%S")
    except (ValueError, TypeError):
        return value


def _duration(value: object) -> str:
    seconds = max(0, int(value)) if isinstance(value, (float, int)) else 0
    days, seconds = divmod(seconds, 86400)
    hours, seconds = divmod(seconds, 3600)
    minutes, seconds = divmod(seconds, 60)
    parts = []
    if days:
        parts.append(f"{days} ngày")
    if hours:
        parts.append(f"{hours} giờ")
    if minutes:
        parts.append(f"{minutes} phút")
    if seconds or not parts:
        parts.append(f"{seconds} giây")
    return " ".join(parts)


def format_operational_message(payload: dict) -> str:
    event = payload.get("event_type")
    risk_label = RISK_LABELS.get(payload.get("business_risk_level"), "CHƯA XÁC ĐỊNH")
    heading = "✅ CẢNH BÁO ĐÃ ĐƯỢC XỬ LÝ" if event == "RESOLVED" else "✅ SỰ CỐ ĐÃ PHỤC HỒI" if event == "RECOVERED" else "🔴 CẢNH BÁO ĐÃ TĂNG MỨC ĐỘ" if event == "ESCALATED" else f"⏰ NHẮC LẠI — CẢNH BÁO {risk_label}" if event == "REMINDER" else f"🔴 CẢNH BÁO {risk_label}"
    current = payload.get("current_a")
    voltage = payload.get("voltage_v")
    threshold = payload.get("minimum_running_current_a")
    lines = [
        heading, "",
        f"Mức độ: {risk_label}",
        f"Dự án: {payload.get('project_name', '—')} ({payload.get('project_code', '—')})",
        f"Thiết bị: {payload.get('device_name', '—')}" + (f" ({payload['device_code']})" if payload.get("device_code") else ""),
    ]
    if payload.get("actuator_name"):
        lines.append(f"Cơ cấu chấp hành: {payload['actuator_name']}")
        if payload.get("actuator_code"):
            lines.append(f"Mã cơ cấu chấp hành: {payload['actuator_code']}")
    elif payload.get("sensor_name"):
        lines.append(f"Cảm biến: {payload['sensor_name']}")
        if payload.get("sensor_code"):
            lines.append(f"Mã cảm biến: {payload['sensor_code']}")
    lines.extend(["",
        "Loại cảnh báo:", str(payload.get("rule_name") or "—"), "",
    ])
    if payload.get("actuator_name"):
        lines.extend([f"Trạng thái yêu cầu: {'Bật' if payload.get('desired_state') is True else 'Tắt' if payload.get('desired_state') is False else 'Chưa xác định'}", f"Trạng thái báo về: {'Bật' if payload.get('reported_state') is True else 'Tắt' if payload.get('reported_state') is False else 'Chưa xác định'}", f"Trạng thái lệnh: {COMMAND_LABELS.get(payload.get('command_status'), 'Chưa có lệnh')}"])
        if isinstance(voltage, (float, int)):
            lines.append(f"Điện áp: {_number(voltage)} V")
        if payload.get("feedback_role") == "SUPPLY_VOLTAGE":
            lower, upper = payload.get("lower_threshold"), payload.get("upper_threshold")
            lines.append(f"Ngưỡng điện áp: {_number(lower)}–{_number(upper)} V" if isinstance(lower, (float, int)) and isinstance(upper, (float, int)) else "Ngưỡng điện áp: Chưa cấu hình")
        if isinstance(current, (float, int)):
            lines.append(f"Dòng điện hiện tại: {_number(current)} A")
        if payload.get("feedback_role") == "RUNNING_CURRENT":
            lower = payload.get("lower_threshold", threshold)
            upper = payload.get("upper_threshold")
            lines.append(f"Ngưỡng dòng điện: {_number(lower)}–{_number(upper)} A" if isinstance(lower, (float, int)) and isinstance(upper, (float, int)) else f"Ngưỡng dòng điện: {_number(lower)} A" if isinstance(lower, (float, int)) else "Ngưỡng dòng điện: Chưa cấu hình")
        elif isinstance(threshold, (float, int)):
            lines.append(f"Ngưỡng vận hành: {_number(threshold)} A")
    elif isinstance(payload.get("value"), (float, int)):
        lines.append(f"Giá trị hiện tại: {_number(payload['value'])} {payload.get('unit') or ''}".strip())
        operator = OPERATOR_LABELS.get(payload.get("operator"), payload.get("operator"))
        if isinstance(payload.get("threshold"), (float, int)):
            lines.append(f"Ngưỡng cảnh báo: {operator or ''} {_number(payload['threshold'])} {payload.get('unit') or ''}".strip())
        elif isinstance(payload.get("lower"), (float, int)) and isinstance(payload.get("upper"), (float, int)):
            lines.append(f"Ngưỡng cảnh báo: < {_number(payload['lower'])} hoặc > {_number(payload['upper'])} {payload.get('unit') or ''}".strip())
    lines.extend([f"Chất lượng dữ liệu: {QUALITY_LABELS.get(payload.get('quality'), 'Chưa xác định')}", f"Độ mới dữ liệu: {'Mới' if payload.get('freshness') == 'FRESH' else 'Dữ liệu cũ' if payload.get('freshness') == 'STALE' else 'Không có dữ liệu'}", f"Thời gian đo: {_display_datetime(payload.get('recorded_at'))}", f"Backend nhận lúc: {_display_datetime(payload.get('received_at'))}", f"Bắt đầu: {_display_datetime(payload.get('started_at'))}", f"Đã kéo dài: {_duration(payload.get('duration_seconds'))}"])
    if payload.get("message"):
        lines.extend(["", "Nội dung:", str(payload["message"])])
    if payload.get("consequence"):
        lines.extend(["", "Hậu quả:", str(payload["consequence"])])
    if payload.get("recommended_action"):
        lines.extend(["", "Khuyến nghị:", str(payload["recommended_action"])])
    return "\n".join(lines)


def _payload_at_delivery(outbox: NotificationOutbox, incident: OperationalIncident, now: datetime) -> dict:
    event_at = incident.resolved_at if outbox.event_type == "RESOLVED" else incident.normalized_at if outbox.event_type == "RECOVERED" else now
    canonical_keys = {
        "rule_name", "message", "consequence", "recommended_action",
        "project_name", "project_code", "device_name", "device_code",
        "sensor_name", "sensor_code", "actuator_name", "actuator_code",
        "operator", "threshold", "lower", "upper", "unit",
    }
    canonical = {
        key: value
        for key, value in (incident.trigger_snapshot or {}).items()
        if key in canonical_keys and value is not None
    }
    return {
        **outbox.payload_snapshot,
        **canonical,
        "incident_id": incident.id,
        "event_type": outbox.event_type,
        "business_risk_level": incident.business_risk_level_snapshot,
        "started_at": incident.started_at.isoformat(),
        "opened_at": incident.opened_at.isoformat() if incident.opened_at else None,
        "duration_seconds": max(0, int(((event_at or now) - incident.started_at).total_seconds())),
    }


def _delivery_identity(outbox: NotificationOutbox, incident: OperationalIncident) -> str:
    if outbox.event_type == "REMINDER":
        sequence = outbox.payload_snapshot.get("reminder_sequence") or outbox.idempotency_key.rsplit(":", 1)[-1]
        return f"incident:{incident.id}:REMINDER:{sequence}"
    if outbox.event_type == "ESCALATED":
        risk = outbox.payload_snapshot.get("business_risk_level") or incident.business_risk_level_snapshot
        return f"incident:{incident.id}:ESCALATED:{risk}"
    return f"incident:{incident.id}:{outbox.event_type}"


async def process_notification_outbox(db: AsyncSession, *, notifier: TelegramNotifier | None = None, limit: int = 50) -> int:
    notifier = notifier or TelegramNotifier()
    now = datetime.now(UTC)
    outboxes = list((await db.scalars(select(NotificationOutbox).where(NotificationOutbox.status.in_(("PENDING", "RETRYING")), NotificationOutbox.available_at <= now).order_by(NotificationOutbox.id).limit(limit).with_for_update(skip_locked=True))).all())
    processed = 0
    for outbox in outboxes:
        incident = await db.get(OperationalIncident, outbox.incident_id)
        if incident is None:
            outbox.status = "FAILED"
            continue
        settings = await db.scalar(select(ProjectNotificationSettings).where(ProjectNotificationSettings.project_id == incident.project_id))
        risk = str(outbox.payload_snapshot.get("business_risk_level") or "")
        policy = await db.scalar(select(ProjectNotificationRiskPolicy).where(ProjectNotificationRiskPolicy.project_id == incident.project_id, ProjectNotificationRiskPolicy.risk_level == risk))
        legacy_allowed = bool(settings and _risk_enabled(settings, risk))
        event_allowed = {
            "OPEN": policy.notify_on_open if policy else bool(settings and settings.notify_alert_opened),
            "ESCALATED": policy.notify_on_escalation if policy else bool(settings and settings.notify_alert_escalated),
            "REMINDER": policy.reminder_enabled if policy else bool(settings and settings.notify_alert_reminder),
            "RECOVERED": policy.notify_on_recovery if policy else bool(settings and settings.notify_alert_recovered),
            "RESOLVED": policy.notify_on_resolved if policy else bool(settings and settings.notify_alert_resolved),
        }.get(outbox.event_type, False)
        allowed = bool(settings and settings.telegram_enabled and (policy.telegram_enabled if policy else legacy_allowed) and event_allowed)
        if not allowed:
            outbox.status = "SKIPPED"
            outbox.skip_reason = "POLICY_DISABLED"
            await _record_skipped_delivery(db, outbox, incident, outbox.skip_reason)
            outbox.processed_at = now
            processed += 1
            continue
        if incident.device_id and (outbox.payload_snapshot.get("freshness") == "STALE" or outbox.payload_snapshot.get("quality") == "STALE"):
            device = await db.get(Device, incident.device_id)
            if device is not None and str(device.status.value) == "OFFLINE":
                outbox.status = "SKIPPED"
                outbox.skip_reason = "SUPPRESSED_BY_DEVICE_OFFLINE"
                await _record_skipped_delivery(db, outbox, incident, outbox.skip_reason)
                outbox.processed_at = now
                processed += 1
                continue
        recipients = list((await db.scalars(select(ProjectNotificationRecipient).where(ProjectNotificationRecipient.project_id == incident.project_id, ProjectNotificationRecipient.enabled.is_(True)))).all())
        all_sent = True
        defensive_deduplication = outbox.event_type in {"OPEN", "RECOVERED", "RESOLVED", "ESCALATED"}
        duplicate_for_all = bool(recipients) and defensive_deduplication
        payload = _payload_at_delivery(outbox, incident, now)
        for recipient in recipients:
            if defensive_deduplication:
                prior_sent = await db.scalar(
                    select(NotificationDelivery.id)
                    .join(NotificationOutbox, NotificationOutbox.id == NotificationDelivery.outbox_id)
                    .where(
                        NotificationDelivery.incident_id == incident.id,
                        NotificationDelivery.channel == "TELEGRAM",
                        NotificationDelivery.recipient_id == recipient.id,
                        NotificationDelivery.status == "SENT",
                        NotificationOutbox.event_type == outbox.event_type,
                        NotificationOutbox.id != outbox.id,
                    )
                    .limit(1)
                )
                if prior_sent is not None:
                    continue
                duplicate_for_all = False
            delivery_key = f"{_delivery_identity(outbox, incident)}:TELEGRAM:{recipient.id}"
            await db.execute(insert(NotificationDelivery).values(outbox_id=outbox.id, incident_id=incident.id, channel="TELEGRAM", recipient_id=recipient.id, recipient_reference=recipient.name, idempotency_key=delivery_key, status="PENDING", attempt_count=0).on_conflict_do_nothing(index_elements=["idempotency_key"]))
            delivery = await db.scalar(select(NotificationDelivery).where(NotificationDelivery.idempotency_key == delivery_key).with_for_update())
            if delivery is None or delivery.status == "SENT":
                continue
            delivery.attempt_count += 1
            delivery.last_attempt_at = now
            result = await notifier.send_message(recipient.telegram_chat_id, format_operational_message(payload))
            if result.sent:
                delivery.status = "SENT"
                delivery.sent_at = now
                delivery.failed_at = None
                delivery.error_category = None
            else:
                all_sent = False
                delivery.status = "RETRYING" if delivery.attempt_count < 5 else "FAILED"
                delivery.failed_at = now
                delivery.error_category = result.error_category
                delivery.next_retry_at = now + timedelta(minutes=min(60, 2 ** delivery.attempt_count))
        outbox.attempt_count += 1
        outbox.last_attempt_at = now
        if all_sent and duplicate_for_all:
            outbox.status = "SKIPPED"
            outbox.skip_reason = "DUPLICATE_OPEN_EVENT" if outbox.event_type == "OPEN" else "DUPLICATE_INCIDENT_EVENT"
            outbox.processed_at = now
            processed += 1
        elif all_sent:
            outbox.status = "PROCESSED"
            outbox.processed_at = now
            processed += 1
        elif outbox.attempt_count < 5:
            outbox.status = "RETRYING"
            outbox.available_at = now + timedelta(minutes=min(60, 2 ** outbox.attempt_count))
        else:
            outbox.status = "FAILED"
    await db.commit()
    return processed


async def _record_skipped_delivery(db: AsyncSession, outbox: NotificationOutbox, incident: OperationalIncident, reason: str) -> None:
    await db.execute(
        insert(NotificationDelivery).values(
            outbox_id=outbox.id, incident_id=incident.id, channel="TELEGRAM",
            recipient_id=None, recipient_reference="Hệ thống",
            idempotency_key=f"{outbox.id}:TELEGRAM:SKIPPED",
            status="SKIPPED", attempt_count=0, error_category=reason,
        ).on_conflict_do_nothing(index_elements=["idempotency_key"])
    )


def _risk_enabled(notification_settings: ProjectNotificationSettings, risk: str) -> bool:
    field = RISK_SETTING_FIELDS.get(risk)
    if field is None:
        return False
    flags = [bool(getattr(notification_settings, name)) for name in RISK_SETTING_FIELDS.values()]
    if all(flags) and notification_settings.minimum_business_risk_level != "LOW":
        return RISK_ORDER.get(risk, -1) >= RISK_ORDER.get(notification_settings.minimum_business_risk_level, 0)
    return bool(getattr(notification_settings, field))


async def enqueue_due_reminders(db: AsyncSession, *, now: datetime | None = None) -> int:
    now = now or datetime.now(UTC)
    rows = (
        await db.execute(
            select(OperationalIncident, ProjectNotificationSettings, ProjectNotificationRiskPolicy)
            .join(ProjectNotificationSettings, ProjectNotificationSettings.project_id == OperationalIncident.project_id)
            .join(ProjectNotificationRiskPolicy, (ProjectNotificationRiskPolicy.project_id == OperationalIncident.project_id) & (ProjectNotificationRiskPolicy.risk_level == OperationalIncident.business_risk_level_snapshot))
            .where(
                OperationalIncident.status.in_(("OPEN", "ACKNOWLEDGED")),
                ProjectNotificationSettings.telegram_enabled.is_(True),
                ProjectNotificationRiskPolicy.telegram_enabled.is_(True),
                ProjectNotificationRiskPolicy.reminder_enabled.is_(True),
                ProjectNotificationRiskPolicy.max_reminders > 0,
            )
        )
    ).all()
    inserted = 0
    for incident, notification_settings, policy in rows:
        del notification_settings
        if incident.opened_at is None or (incident.status == "ACKNOWLEDGED" and policy.stop_reminders_on_ack):
            continue
        reminders = list((await db.scalars(select(NotificationOutbox).where(NotificationOutbox.incident_id == incident.id, NotificationOutbox.event_type == "REMINDER").order_by(NotificationOutbox.id))).all())
        sent_count = len(reminders)
        sequence = sent_count + 1
        if sequence > policy.max_reminders:
            continue
        due_at = (
            reminders[-1].available_at + timedelta(seconds=policy.repeat_interval_seconds)
            if reminders
            else incident.opened_at + timedelta(seconds=policy.initial_reminder_seconds)
        )
        if now < due_at:
            continue
        result = await db.execute(
            insert(NotificationOutbox)
            .values(incident_id=incident.id, event_type="REMINDER", idempotency_key=f"incident:{incident.id}:REMINDER:{sequence}", payload_snapshot={**incident.trigger_snapshot, "incident_id": incident.id, "event_type": "REMINDER", "reminder_sequence": sequence, "technical_severity": incident.technical_severity, "business_risk_level": incident.business_risk_level_snapshot, "started_at": incident.started_at.isoformat(), "opened_at": incident.opened_at.isoformat()}, status="PENDING", available_at=now, attempt_count=0)
            .on_conflict_do_nothing(index_elements=["idempotency_key"])
            .returning(NotificationOutbox.id)
        )
        inserted += int(result.scalar_one_or_none() is not None)
    await db.flush()
    return inserted
