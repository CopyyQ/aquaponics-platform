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
    if payload.get("resource_type") and payload.get("metric_type"):
        return format_canonical_operational_message(payload)
    risk = str(payload.get("business_risk_level") or "MEDIUM")
    lines = [
        f"🔴 CẢNH BÁO {RISK_LABELS.get(risk, risk)}",
        "",
        f"Hệ thống Aquaponics: {payload.get('project_name', '—')}",
        f"Thiết bị: {payload.get('device_name', '—')}",
    ]
    if payload.get("sensor_name"):
        lines.append(f"Cảm biến: {payload['sensor_name']}")
    if payload.get("sensor_code"):
        lines.append(f"Mã cảm biến: {payload['sensor_code']}")
    unit = str(payload.get("unit") or "").strip()
    if isinstance(payload.get("lower"), (float, int)) and isinstance(payload.get("upper"), (float, int)):
        lines.append(f"Ngưỡng cảnh báo: < {_number(payload['lower'])} hoặc > {_number(payload['upper'])} {unit}".strip())
    elif isinstance(payload.get("threshold"), (float, int)):
        operator = OPERATOR_LABELS.get(payload.get("operator"), payload.get("operator") or "")
        lines.append(f"Ngưỡng cảnh báo: {operator} {_number(payload['threshold'])} {unit}".strip())
    lines.extend([
        f"Bắt đầu: {_display_datetime(payload.get('started_at'))}",
        f"Đã kéo dài: {_duration(payload.get('duration_seconds'))}",
    ])
    if payload.get("message"):
        lines.extend(["", str(payload["message"])])
    return "\n".join(lines)


def format_canonical_operational_message(payload: dict) -> str:
    event = str(payload.get("event_type") or "OPEN")
    risk = str(payload.get("business_risk_level") or "MEDIUM")
    direction = str(payload.get("threshold_direction") or "")
    resource = str(payload.get("resource_name") or "Thiết bị")
    metric = str(payload.get("metric_type") or "").replace("_", " ")
    heading = "✅ CẢNH BÁO ĐÃ ĐƯỢC XỬ LÝ" if event == "RESOLVED" else "✅ SỰ CỐ ĐÃ PHỤC HỒI" if event == "RECOVERED" else f"🔴 CẢNH BÁO {RISK_LABELS.get(risk, risk)} — HỆ THỐNG AQUAPONICS"
    lines = [heading, "", f"MỨC ĐỘ: {RISK_LABELS.get(risk, risk)}", f"HỆ THỐNG: {payload.get('project_name', '—')}", f"THIẾT BỊ: {payload.get('device_name', '—')}", f"NGUỒN: {resource}"]
    if payload.get("title"):
        lines.extend(["", "SỰ CỐ:", str(payload["title"])])
    if metric:
        lines.append(f"Chỉ số: {metric}")
    if payload.get("value") is not None:
        lines.append(f"Giá trị: {_number(payload['value'])} {payload.get('unit') or ''}".strip())
    if payload.get("threshold") is not None:
        operator = "<" if direction == "BELOW" else ">" if direction == "ABOVE" else ""
        lines.append(f"Ngưỡng: {operator} {_number(payload['threshold'])} {payload.get('unit') or ''}".strip())
    if payload.get("voltage_v") is not None:
        lines.append(f"Điện áp: {_number(payload['voltage_v'])} V")
    if payload.get("current_a") is not None:
        lines.append(f"Dòng điện: {_number(payload['current_a'])} A")
    if payload.get("reported_state") is not None:
        lines.append(f"Trạng thái báo về: {'Bật' if payload['reported_state'] else 'Tắt'}")
    if payload.get("desired_state") is not None:
        lines.append(f"Trạng thái yêu cầu: {'Bật' if payload['desired_state'] else 'Tắt'}")
    lines.append(f"Thời gian: {_display_datetime(payload.get('recorded_at'))}")
    if payload.get("consequence"):
        lines.extend(["", "Ảnh hưởng:", str(payload["consequence"])])
    actions = payload.get("recommended_actions")
    if isinstance(actions, list) and actions:
        lines.extend(["", "Khuyến nghị xử lý:"])
        lines.extend(f"• {item}" for item in actions)
    elif payload.get("recommended_action"):
        lines.extend(["", "Khuyến nghị xử lý:", str(payload["recommended_action"])])
    custom_message = str(payload.get("message") or "").strip()
    if custom_message and custom_message != str(payload.get("title") or "").strip():
        lines.extend(["", f"Ghi chú: {custom_message}"])
    return "\n".join(lines)


def format_project_activity_message(payload: dict) -> str:
    """Render an already snapshotted project activity event without live reads."""
    return str(payload.get("message") or "Thông báo hoạt động dự án")


async def resolve_notification_recipients(
    db: AsyncSession, *, project_id: int
) -> list[ProjectNotificationRecipient]:
    return list((await db.scalars(
        select(ProjectNotificationRecipient).where(
            ProjectNotificationRecipient.project_id == project_id,
            ProjectNotificationRecipient.enabled.is_(True),
        )
    )).all())


async def evaluate_notification_policy(
    db: AsyncSession, *, project_id: int, source_type: str, event_type: str, risk: str | None
) -> str | None:
    """Return a precise skip reason, or ``None`` when delivery is allowed.

    Settings own the global channel switch. Risk policies own incident risk and
    lifecycle switches. Project activity has no alert risk, so it uses only the
    global channel switch rather than inventing one.
    """
    settings = await db.scalar(select(ProjectNotificationSettings).where(ProjectNotificationSettings.project_id == project_id))
    if settings is None:
        return "PROJECT_NOTIFICATION_NOT_CONFIGURED"
    if not settings.enabled:
        return "NOTIFICATIONS_DISABLED"
    if not settings.telegram_enabled:
        return "TELEGRAM_DISABLED"
    if source_type != "INCIDENT":
        return None
    policy = await db.scalar(select(ProjectNotificationRiskPolicy).where(
        ProjectNotificationRiskPolicy.project_id == project_id,
        ProjectNotificationRiskPolicy.risk_level == risk,
    ))
    risk_allowed = policy.telegram_enabled if policy else _risk_enabled(settings, risk or "")
    if not risk_allowed:
        return "RISK_DISABLED"
    event_allowed = {
        "OPEN": policy.notify_on_open if policy else settings.notify_alert_opened,
        "ACTIVE_SYNC": policy.notify_on_open if policy else settings.notify_alert_opened,
        "ESCALATED": policy.notify_on_escalation if policy else settings.notify_alert_escalated,
        "REMINDER": policy.reminder_enabled if policy else settings.notify_alert_reminder,
        "RECOVERED": policy.notify_on_recovery if policy else settings.notify_alert_recovered,
        "RESOLVED": policy.notify_on_resolved if policy else settings.notify_alert_resolved,
    }.get(event_type, False)
    return None if event_allowed else "EVENT_DISABLED"


async def next_notification_generation(db: AsyncSession, *, project_id: int) -> int:
    settings_row = await db.scalar(
        select(ProjectNotificationSettings)
        .where(ProjectNotificationSettings.project_id == project_id)
        .with_for_update()
    )
    if settings_row is None:
        settings_row = ProjectNotificationSettings(project_id=project_id)
        db.add(settings_row)
        await db.flush()
    settings_row.notification_generation += 1
    await db.flush()
    return settings_row.notification_generation


async def reconcile_active_incident_notifications(
    db: AsyncSession,
    *,
    project_id: int,
    generation: int,
    reason: str,
    recipient_ids: set[int] | None = None,
    risk_levels: set[str] | None = None,
    skip_previously_informed: bool = True,
) -> int:
    """Queue recipient-scoped ACTIVE_SYNC without waiting for new telemetry."""
    incidents = list((await db.scalars(select(OperationalIncident).where(
        OperationalIncident.project_id == project_id,
        OperationalIncident.status.in_(("OPEN", "ACKNOWLEDGED")),
    ))).all())
    if risk_levels is not None:
        incidents = [item for item in incidents if item.business_risk_level_snapshot in risk_levels]
    recipient_query = select(ProjectNotificationRecipient).where(
        ProjectNotificationRecipient.project_id == project_id,
        ProjectNotificationRecipient.enabled.is_(True),
    )
    if recipient_ids is not None:
        recipient_query = recipient_query.where(ProjectNotificationRecipient.id.in_(recipient_ids))
    recipients = list((await db.scalars(recipient_query)).all())
    targets: list[ProjectNotificationRecipient | None] = recipients or ([None] if recipient_ids is None else [])
    inserted = 0
    for incident in incidents:
        for recipient in targets:
            if recipient is not None and skip_previously_informed:
                informed = await db.scalar(
                    select(NotificationDelivery.id)
                    .where(
                        NotificationDelivery.incident_id == incident.id,
                        NotificationDelivery.recipient_id == recipient.id,
                        NotificationDelivery.status == "SENT",
                    )
                    .limit(1)
                )
                if informed is not None:
                    continue
            recipient_key = recipient.id if recipient is not None else "none"
            result = await db.execute(
                insert(NotificationOutbox)
                .values(
                    incident_id=incident.id,
                    project_id=project_id,
                    source_type="INCIDENT",
                    target_recipient_id=recipient.id if recipient is not None else None,
                    event_type="ACTIVE_SYNC",
                    idempotency_key=f"incident:{incident.id}:ACTIVE_SYNC:generation:{generation}:recipient:{recipient_key}",
                    payload_snapshot={
                        **incident.trigger_snapshot,
                        "incident_id": incident.id,
                        "event_type": "ACTIVE_SYNC",
                        "sync_reason": reason,
                        "notification_generation": generation,
                        "target_recipient_id": recipient.id if recipient is not None else None,
                        "business_risk_level": incident.business_risk_level_snapshot,
                    },
                    status="PENDING",
                    available_at=datetime.now(UTC),
                    attempt_count=0,
                )
                .on_conflict_do_nothing(index_elements=["idempotency_key"])
                .returning(NotificationOutbox.id)
            )
            inserted += int(result.scalar_one_or_none() is not None)
    return inserted


async def enqueue_project_activity_notification(
    db: AsyncSession, *, project_id: int, activity_id: int, payload_snapshot: dict
) -> None:
    await db.execute(insert(NotificationOutbox).values(
        incident_id=None, project_id=project_id, source_type="PROJECT_ACTIVITY",
        event_type="PROJECT_ACTIVITY", idempotency_key=f"project-activity:{activity_id}",
        payload_snapshot={**payload_snapshot, "source_type": "PROJECT_ACTIVITY", "activity_id": activity_id},
        status="PENDING", available_at=datetime.now(UTC), attempt_count=0,
    ).on_conflict_do_nothing(index_elements=["idempotency_key"]))


async def enqueue_operational_event(
    db: AsyncSession, *, project_id: int, source_key: str, event_type: str, payload_snapshot: dict
) -> None:
    """Persist a non-threshold operational event for the common worker."""
    await db.execute(insert(NotificationOutbox).values(
        incident_id=None, project_id=project_id, source_type="SYSTEM_EVENT",
        event_type=event_type, idempotency_key=f"system-event:{source_key}",
        payload_snapshot={**payload_snapshot, "source_type": "SYSTEM_EVENT"},
        status="PENDING", available_at=datetime.now(UTC), attempt_count=0,
    ).on_conflict_do_nothing(index_elements=["idempotency_key"]))


def _payload_at_delivery(outbox: NotificationOutbox, incident: OperationalIncident, now: datetime) -> dict:
    event_at = incident.resolved_at if outbox.event_type == "RESOLVED" else incident.normalized_at if outbox.event_type == "RECOVERED" else now
    canonical_keys = {
        "rule_name", "condition_key", "title", "message", "consequence",
        "recommended_action", "recommended_actions", "catalog_version",
        "project_name", "project_code", "device_name", "device_code",
        "sensor_name", "sensor_code", "actuator_name", "actuator_code",
        "resource_type", "resource_name", "metric_type", "threshold_direction",
        "operator", "threshold", "lower", "upper", "unit", "value",
        "voltage_v", "current_a", "desired_state", "reported_state", "recorded_at",
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


def _delivery_identity(outbox: NotificationOutbox, incident: OperationalIncident | None) -> str:
    if incident is None:
        return f"{outbox.source_type.lower()}:{outbox.idempotency_key}"
    if outbox.event_type == "REMINDER":
        sequence = outbox.payload_snapshot.get("reminder_sequence") or outbox.idempotency_key.rsplit(":", 1)[-1]
        return f"incident:{incident.id}:REMINDER:{sequence}"
    if outbox.event_type == "ESCALATED":
        risk = outbox.payload_snapshot.get("business_risk_level") or incident.business_risk_level_snapshot
        return f"incident:{incident.id}:ESCALATED:{risk}"
    if outbox.event_type == "ACTIVE_SYNC":
        generation = outbox.payload_snapshot.get("notification_generation", 0)
        return f"incident:{incident.id}:ACTIVE_SYNC:generation:{generation}"
    return f"incident:{incident.id}:{outbox.event_type}"


async def process_notification_outbox(db: AsyncSession, *, notifier: TelegramNotifier | None = None, limit: int = 50) -> int:
    notifier = notifier or TelegramNotifier()
    now = datetime.now(UTC)
    # MQTT evaluation locks an incident before inserting/updating its outbox.
    # Claim in the same order to avoid an incident<->outbox deadlock while
    # telemetry and the scheduler are active concurrently.
    candidates = (await db.execute(
        select(NotificationOutbox.id, NotificationOutbox.incident_id)
        .where(
            NotificationOutbox.status.in_(("PENDING", "RETRYING")),
            NotificationOutbox.available_at <= now,
        )
        .order_by(NotificationOutbox.id)
        .limit(limit)
    )).all()
    claimed: list[tuple[NotificationOutbox, OperationalIncident | None]] = []
    for outbox_id, incident_id in candidates:
        incident = None
        if incident_id is not None:
            incident = await db.scalar(
                select(OperationalIncident)
                .where(OperationalIncident.id == incident_id)
                .with_for_update()
            )
        outbox = await db.scalar(
            select(NotificationOutbox)
            .where(
                NotificationOutbox.id == outbox_id,
                NotificationOutbox.status.in_(("PENDING", "RETRYING")),
                NotificationOutbox.available_at <= now,
            )
            .with_for_update(skip_locked=True)
        )
        if outbox is not None:
            claimed.append((outbox, incident))
    processed = 0
    for outbox, incident in claimed:
        project_id = incident.project_id if incident else outbox.project_id
        if project_id is None or (outbox.incident_id is not None and incident is None):
            outbox.status = "FAILED"
            outbox.skip_reason = "SOURCE_NOT_FOUND"
            continue
        risk = str(outbox.payload_snapshot.get("business_risk_level") or "")
        policy_reason = await evaluate_notification_policy(
            db, project_id=project_id, source_type=outbox.source_type,
            event_type=outbox.event_type, risk=risk or None,
        )
        if policy_reason:
            outbox.status = "SKIPPED"
            outbox.skip_reason = policy_reason
            await _record_skipped_delivery(db, outbox, incident, policy_reason)
            outbox.processed_at = now
            processed += 1
            continue
        if incident is not None and incident.device_id and (outbox.payload_snapshot.get("freshness") == "STALE" or outbox.payload_snapshot.get("quality") == "STALE"):
            device = await db.get(Device, incident.device_id)
            if device is not None and str(device.status.value) == "OFFLINE":
                outbox.status = "SKIPPED"
                outbox.skip_reason = "SUPPRESSED_BY_DEVICE_OFFLINE"
                await _record_skipped_delivery(db, outbox, incident, outbox.skip_reason)
                outbox.processed_at = now
                processed += 1
                continue
        recipients = await resolve_notification_recipients(db, project_id=project_id)
        target_recipient_id = outbox.target_recipient_id or outbox.payload_snapshot.get("target_recipient_id")
        if target_recipient_id is not None:
            recipients = [item for item in recipients if item.id == target_recipient_id]
            if not recipients:
                outbox.status = "SKIPPED"
                outbox.skip_reason = "RECIPIENT_DISABLED"
                await _record_skipped_delivery(db, outbox, incident, outbox.skip_reason)
                outbox.processed_at = now
                processed += 1
                continue
        if not recipients:
            outbox.status = "SKIPPED"
            outbox.skip_reason = "NO_RECIPIENT"
            await _record_skipped_delivery(db, outbox, incident, outbox.skip_reason)
            outbox.processed_at = now
            processed += 1
            continue
        if not getattr(notifier, "configured", True):
            outbox.status = "SKIPPED"
            outbox.skip_reason = "BOT_NOT_CONFIGURED"
            await _record_skipped_delivery(db, outbox, incident, outbox.skip_reason)
            outbox.processed_at = now
            processed += 1
            continue
        all_sent = True
        defensive_deduplication = outbox.event_type in {"OPEN", "RECOVERED", "RESOLVED", "ESCALATED"}
        duplicate_for_all = bool(recipients) and defensive_deduplication
        payload = _payload_at_delivery(outbox, incident, now) if incident else {**outbox.payload_snapshot, "event_type": outbox.event_type}
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
            await db.execute(insert(NotificationDelivery).values(outbox_id=outbox.id, incident_id=incident.id if incident else None, channel="TELEGRAM", recipient_id=recipient.id, recipient_reference=recipient.name, idempotency_key=delivery_key, status="PENDING", attempt_count=0).on_conflict_do_nothing(index_elements=["idempotency_key"]))
            delivery = await db.scalar(select(NotificationDelivery).where(NotificationDelivery.idempotency_key == delivery_key).with_for_update())
            if delivery is None or delivery.status == "SENT":
                continue
            delivery.attempt_count += 1
            delivery.last_attempt_at = now
            message = format_project_activity_message(payload) if outbox.source_type == "PROJECT_ACTIVITY" else format_operational_message(payload)
            result = await notifier.send_message(recipient.telegram_chat_id, message)
            if result.sent:
                delivery.status = "SENT"
                delivery.sent_at = now
                delivery.failed_at = None
                delivery.error_category = None
                delivery.provider_status_code = result.status_code
                delivery.error_message = None
            else:
                all_sent = False
                delivery.status = "RETRYING" if delivery.attempt_count < 5 else "FAILED"
                delivery.failed_at = now
                delivery.error_category = result.error_category
                delivery.provider_status_code = result.status_code
                delivery.error_message = {
                    "RATE_LIMITED": "Telegram giới hạn tần suất gửi; hệ thống sẽ thử lại.",
                    "BAD_REQUEST": "Telegram từ chối yêu cầu hoặc Chat ID không hợp lệ.",
                    "FORBIDDEN": "Bot không được phép gửi tới người nhận này.",
                    "INVALID_TOKEN": "Cấu hình Telegram phía máy chủ không hợp lệ.",
                    "TIMEOUT": "Telegram không phản hồi trong thời gian cho phép.",
                    "NETWORK_ERROR": "Không thể kết nối tới Telegram.",
                }.get(result.error_category, "Telegram trả về lỗi; hệ thống sẽ thử lại nếu phù hợp.")
                retry_delay = result.retry_after_seconds or min(3600, 60 * (2 ** delivery.attempt_count))
                delivery.next_retry_at = now + timedelta(seconds=retry_delay)
        outbox.attempt_count += 1
        outbox.last_attempt_at = now
        if all_sent and duplicate_for_all:
            outbox.status = "SKIPPED"
            outbox.skip_reason = "DUPLICATE_OPEN_EVENT" if outbox.event_type == "OPEN" else "DUPLICATE_INCIDENT_EVENT"
            outbox.processed_at = now
            processed += 1
        elif all_sent:
            outbox.status = "SENT"
            outbox.processed_at = now
            processed += 1
        elif outbox.attempt_count < 5:
            outbox.status = "RETRYING"
            retry_after = max(
                (delivery.next_retry_at for delivery in (await db.scalars(select(NotificationDelivery).where(NotificationDelivery.outbox_id == outbox.id))).all() if delivery.next_retry_at),
                default=now + timedelta(minutes=min(60, 2 ** outbox.attempt_count)),
            )
            outbox.available_at = retry_after
        else:
            outbox.status = "FAILED"
    await db.commit()
    return processed


async def _record_skipped_delivery(db: AsyncSession, outbox: NotificationOutbox, incident: OperationalIncident | None, reason: str) -> None:
    await db.execute(
        insert(NotificationDelivery).values(
            outbox_id=outbox.id, incident_id=incident.id if incident else None, channel="TELEGRAM",
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
            .values(incident_id=incident.id, project_id=incident.project_id, event_type="REMINDER", idempotency_key=f"incident:{incident.id}:REMINDER:{sequence}", payload_snapshot={**incident.trigger_snapshot, "incident_id": incident.id, "event_type": "REMINDER", "reminder_sequence": sequence, "technical_severity": incident.technical_severity, "business_risk_level": incident.business_risk_level_snapshot, "started_at": incident.started_at.isoformat(), "opened_at": incident.opened_at.isoformat()}, status="PENDING", available_at=now, attempt_count=0)
            .on_conflict_do_nothing(index_elements=["idempotency_key"])
            .returning(NotificationOutbox.id)
        )
        inserted += int(result.scalar_one_or_none() is not None)
    await db.flush()
    return inserted
