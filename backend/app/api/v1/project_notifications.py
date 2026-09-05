from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_operational_user
from app.core.config import settings
from app.db.session import get_db
from app.models.project_settings import ProjectNotificationRecipient, ProjectNotificationRiskPolicy, ProjectNotificationSettings
from app.models.operational_alert import AlertRule, NotificationDelivery, OperationalIncident
from app.models.user import User
from app.schemas.notifications import (
    NotificationRecipientCreate,
    NotificationRecipientRead,
    NotificationRecipientUpdate,
    NotificationRiskPolicy,
    NotificationSettingsRead,
    NotificationSettingsUpdate,
    TestMessageResult,
)
from app.schemas.operational_alert import IncidentResolutionRequest, NotificationDeliveryRead, OperationalIncidentRead
from app.services.access_service import require_project_access
from app.services.telegram_notifier import TelegramNotifier
from app.services.operational_incident_service import enqueue_incident_notification
from app.services.project_activity_service import dispatch_project_activity, record_project_activity

router = APIRouter(prefix="/projects", tags=["Project notifications"])

RISK_LEVELS = ("EXTREME", "VERY_HIGH", "HIGH", "MEDIUM", "LOW_MEDIUM", "LOW")
RISK_DEFAULTS = {
    "EXTREME": (True, True, 300, 600, 4),
    "VERY_HIGH": (True, True, 900, 1800, 3),
    "HIGH": (True, True, 1800, 3600, 2),
    "MEDIUM": (True, False, 1800, 3600, 0),
    "LOW_MEDIUM": (False, False, 3600, 7200, 0),
    "LOW": (False, False, 3600, 7200, 0),
}


def _default_risk_policies(item: ProjectNotificationSettings | None) -> list[NotificationRiskPolicy]:
    legacy_flags = {
        "EXTREME": "risk_extreme_enabled", "VERY_HIGH": "risk_very_high_enabled",
        "HIGH": "risk_high_enabled", "MEDIUM": "risk_medium_enabled",
        "LOW_MEDIUM": "risk_low_medium_enabled", "LOW": "risk_low_enabled",
    }
    values = []
    for level in RISK_LEVELS:
        enabled, reminder, initial, repeat, maximum = RISK_DEFAULTS[level]
        if item:
            enabled = bool(getattr(item, legacy_flags[level]))
            reminder = item.notify_alert_reminder or reminder
            if item.reminder_interval_minutes:
                initial = repeat = item.reminder_interval_minutes * 60
        values.append(NotificationRiskPolicy(
            risk_level=level, telegram_enabled=enabled,
            notify_on_open=item.notify_alert_opened if item else True,
            notify_on_escalation=item.notify_alert_escalated if item else True,
            notify_on_recovery=item.notify_alert_recovered if item else True,
            notify_on_resolved=item.notify_alert_resolved if item else True,
            reminder_enabled=reminder, initial_reminder_seconds=initial,
            repeat_interval_seconds=repeat, max_reminders=maximum,
            stop_reminders_on_ack=True,
        ))
    return values


async def _incident(db: AsyncSession, project_id: int, incident_id: int) -> OperationalIncident:
    incident = await db.scalar(select(OperationalIncident).where(OperationalIncident.id == incident_id, OperationalIncident.project_id == project_id))
    if incident is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy sự cố trong dự án")
    return incident


async def _settings(db: AsyncSession, project_id: int) -> ProjectNotificationSettings | None:
    return await db.scalar(select(ProjectNotificationSettings).where(ProjectNotificationSettings.project_id == project_id))


async def _recipient(db: AsyncSession, project_id: int, recipient_id: int) -> ProjectNotificationRecipient:
    recipient = await db.scalar(select(ProjectNotificationRecipient).where(ProjectNotificationRecipient.id == recipient_id, ProjectNotificationRecipient.project_id == project_id))
    if recipient is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy người nhận Telegram")
    return recipient


async def _response(db: AsyncSession, project_id: int) -> NotificationSettingsRead:
    item = await _settings(db, project_id)
    policy_rows = list((await db.scalars(select(ProjectNotificationRiskPolicy).where(ProjectNotificationRiskPolicy.project_id == project_id))).all())
    risk_policies = [NotificationRiskPolicy.model_validate(value, from_attributes=True) for value in policy_rows] if len(policy_rows) == 6 else _default_risk_policies(item)
    recipients = list((await db.scalars(select(ProjectNotificationRecipient).where(ProjectNotificationRecipient.project_id == project_id).order_by(ProjectNotificationRecipient.created_at))).all())
    return NotificationSettingsRead(
        telegram_enabled=item.telegram_enabled if item else False,
        notify_alert_opened=item.notify_alert_opened if item else True,
        notify_alert_resolved=item.notify_alert_resolved if item else True,
        notify_alert_recovered=item.notify_alert_recovered if item else True,
        notify_alert_escalated=item.notify_alert_escalated if item else True,
        notify_alert_reminder=item.notify_alert_reminder if item else False,
        reminder_interval_minutes=item.reminder_interval_minutes if item else None,
        minimum_business_risk_level=item.minimum_business_risk_level if item else "LOW",
        risk_extreme_enabled=item.risk_extreme_enabled if item else True,
        risk_very_high_enabled=item.risk_very_high_enabled if item else True,
        risk_high_enabled=item.risk_high_enabled if item else True,
        risk_medium_enabled=item.risk_medium_enabled if item else True,
        risk_low_medium_enabled=item.risk_low_medium_enabled if item else True,
        risk_low_enabled=item.risk_low_enabled if item else True,
        risk_policies=sorted(risk_policies, key=lambda value: RISK_LEVELS.index(value.risk_level)),
        telegram_bot_configured=bool(settings.telegram_bot_token and settings.telegram_bot_token.strip()),
        recipients=[NotificationRecipientRead.model_validate(value) for value in recipients],
    )


@router.get("/{project_id}/notification-history", response_model=list[NotificationDeliveryRead])
async def notification_history(project_id: int, db: AsyncSession = Depends(get_db), actor: User = Depends(get_current_operational_user)) -> list[NotificationDeliveryRead]:
    project = await require_project_access(db, project_id, actor, manage=True)
    rows = (
        await db.execute(
            select(NotificationDelivery, OperationalIncident, AlertRule, ProjectNotificationRecipient)
            .join(OperationalIncident, OperationalIncident.id == NotificationDelivery.incident_id)
            .join(AlertRule, AlertRule.id == OperationalIncident.rule_id)
            .outerjoin(ProjectNotificationRecipient, ProjectNotificationRecipient.id == NotificationDelivery.recipient_id)
            .where(OperationalIncident.project_id == project_id)
            .order_by(NotificationDelivery.created_at.desc())
            .limit(500)
        )
    ).all()
    return [NotificationDeliveryRead(id=delivery.id, created_at=delivery.created_at, project_id=project_id, project_name=project.name, rule_name=rule.name, business_risk_level=incident.business_risk_level_snapshot, channel=delivery.channel, recipient_name=recipient.name if recipient else delivery.recipient_reference, status=delivery.status, attempt_count=delivery.attempt_count, reason=delivery.error_category) for delivery, incident, rule, recipient in rows]


@router.get("/{project_id}/operational-incidents", response_model=list[OperationalIncidentRead])
async def operational_incidents(project_id: int, db: AsyncSession = Depends(get_db), actor: User = Depends(get_current_operational_user)) -> list[OperationalIncident]:
    await require_project_access(db, project_id, actor)
    return list((await db.scalars(select(OperationalIncident).where(OperationalIncident.project_id == project_id).order_by(OperationalIncident.started_at.desc()).limit(500))).all())


@router.post("/{project_id}/operational-incidents/{incident_id}/acknowledge", response_model=OperationalIncidentRead)
async def acknowledge_incident(project_id: int, incident_id: int, db: AsyncSession = Depends(get_db), actor: User = Depends(get_current_operational_user)) -> OperationalIncident:
    await require_project_access(db, project_id, actor, manage=True)
    incident = await _incident(db, project_id, incident_id)
    if incident.status != "OPEN":
        raise HTTPException(status_code=409, detail="Chỉ có thể xác nhận sự cố đang mở")
    incident.status = "ACKNOWLEDGED"
    incident.acknowledged_at = datetime.now(UTC)
    incident.acknowledged_by = actor.id
    await db.commit()
    await db.refresh(incident)
    return incident


@router.post("/{project_id}/operational-incidents/{incident_id}/resolve", response_model=OperationalIncidentRead)
async def resolve_incident(project_id: int, incident_id: int, payload: IncidentResolutionRequest, db: AsyncSession = Depends(get_db), actor: User = Depends(get_current_operational_user)) -> OperationalIncident:
    await require_project_access(db, project_id, actor, manage=True)
    incident = await _incident(db, project_id, incident_id)
    if incident.status != "NORMALIZED":
        raise HTTPException(status_code=409, detail="Chỉ có thể đóng sự cố sau khi điều kiện đã bình thường")
    incident.status = "RESOLVED"
    incident.resolved_at = datetime.now(UTC)
    incident.resolved_by = actor.id
    incident.resolution_note = payload.resolution_note.strip()
    await enqueue_incident_notification(db, incident, "RESOLVED")
    await db.commit()
    await db.refresh(incident)
    return incident


@router.get("/{project_id}/notification-settings", response_model=NotificationSettingsRead)
async def get_notification_settings(project_id: int, db: AsyncSession = Depends(get_db), actor: User = Depends(get_current_operational_user)) -> NotificationSettingsRead:
    await require_project_access(db, project_id, actor, manage=True)
    return await _response(db, project_id)


@router.put("/{project_id}/notification-settings", response_model=NotificationSettingsRead)
async def update_notification_settings(project_id: int, payload: NotificationSettingsUpdate, db: AsyncSession = Depends(get_db), actor: User = Depends(get_current_operational_user)) -> NotificationSettingsRead:
    await require_project_access(db, project_id, actor, manage=True)
    item = await _settings(db, project_id)
    if item is None:
        item = ProjectNotificationSettings(project_id=project_id)
        db.add(item)
    values = payload.model_dump(exclude={"risk_policies"})
    before = {field: getattr(item, field) for field in values}
    for field, value in values.items():
        setattr(item, field, value)
    changes = {field: {"before": before[field], "after": value} for field, value in values.items() if before[field] != value}
    if payload.risk_policies:
        existing = {value.risk_level: value for value in (await db.scalars(select(ProjectNotificationRiskPolicy).where(ProjectNotificationRiskPolicy.project_id == project_id))).all()}
        for policy in payload.risk_policies:
            row = existing.get(policy.risk_level)
            if row is None:
                row = ProjectNotificationRiskPolicy(project_id=project_id, **policy.model_dump())
                db.add(row)
            else:
                for field, value in policy.model_dump(exclude={"risk_level"}).items():
                    setattr(row, field, value)
        changes["risk_policies"] = {"before": "configured", "after": "updated"}
    if not changes:
        return await _response(db, project_id)
    activity = await record_project_activity(db, project_id=project_id, actor=actor, action="NOTIFICATION_SETTINGS_UPDATED", entity_type="NOTIFICATION", entity_id=item.id, entity_name="Cấu hình Telegram", changes=changes)
    await db.commit()
    await dispatch_project_activity(db, activity_id=activity.id)
    return await _response(db, project_id)


@router.post("/{project_id}/notification-recipients", response_model=NotificationRecipientRead, status_code=status.HTTP_201_CREATED)
async def create_recipient(project_id: int, payload: NotificationRecipientCreate, db: AsyncSession = Depends(get_db), actor: User = Depends(get_current_operational_user)) -> ProjectNotificationRecipient:
    await require_project_access(db, project_id, actor, manage=True)
    item = ProjectNotificationRecipient(project_id=project_id, **payload.model_dump())
    db.add(item)
    try:
        await db.flush()
        activity = await record_project_activity(db, project_id=project_id, actor=actor, action="NOTIFICATION_RECIPIENT_ADDED", entity_type="NOTIFICATION", entity_id=item.id, entity_name=item.name, changes={"enabled": {"before": None, "after": item.enabled}})
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(status_code=409, detail="Telegram Chat ID đã tồn tại trong dự án") from exc
    await db.refresh(item)
    await dispatch_project_activity(db, activity_id=activity.id)
    return item


@router.patch("/{project_id}/notification-recipients/{recipient_id}", response_model=NotificationRecipientRead)
async def update_recipient(project_id: int, recipient_id: int, payload: NotificationRecipientUpdate, db: AsyncSession = Depends(get_db), actor: User = Depends(get_current_operational_user)) -> ProjectNotificationRecipient:
    await require_project_access(db, project_id, actor, manage=True)
    item = await _recipient(db, project_id, recipient_id)
    values = payload.model_dump(exclude_unset=True)
    before = {field: getattr(item, field) for field in values if field != "telegram_chat_id"}
    for field, value in values.items():
        setattr(item, field, value)
    changes = {field: {"before": before[field], "after": value} for field, value in values.items() if field != "telegram_chat_id" and before[field] != value}
    if not changes and "telegram_chat_id" not in values:
        return item
    action = "NOTIFICATION_RECIPIENT_ENABLED" if values.get("enabled") is True else "NOTIFICATION_RECIPIENT_DISABLED" if values.get("enabled") is False else "NOTIFICATION_RECIPIENT_UPDATED"
    activity = await record_project_activity(db, project_id=project_id, actor=actor, action=action, entity_type="NOTIFICATION", entity_id=item.id, entity_name=item.name, changes=changes)
    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(status_code=409, detail="Telegram Chat ID đã tồn tại trong dự án") from exc
    await db.refresh(item)
    await dispatch_project_activity(db, activity_id=activity.id)
    return item


@router.delete("/{project_id}/notification-recipients/{recipient_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_recipient(project_id: int, recipient_id: int, db: AsyncSession = Depends(get_db), actor: User = Depends(get_current_operational_user)) -> Response:
    await require_project_access(db, project_id, actor, manage=True)
    item = await _recipient(db, project_id, recipient_id)
    activity = await record_project_activity(db, project_id=project_id, actor=actor, action="NOTIFICATION_RECIPIENT_REMOVED", entity_type="NOTIFICATION", entity_id=item.id, entity_name=item.name, changes={"removed": True})
    await db.delete(item)
    await db.commit()
    await dispatch_project_activity(db, activity_id=activity.id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{project_id}/notification-recipients/{recipient_id}/test", response_model=TestMessageResult)
async def test_recipient(project_id: int, recipient_id: int, db: AsyncSession = Depends(get_db), actor: User = Depends(get_current_operational_user)) -> TestMessageResult:
    project = await require_project_access(db, project_id, actor, manage=True)
    item = await _recipient(db, project_id, recipient_id)
    if not item.enabled:
        raise HTTPException(status_code=409, detail="Người nhận đang tắt")
    result = await TelegramNotifier().send_message(item.telegram_chat_id, f"✅ Aquaponics Platform\n\nKết nối Telegram thành công.\n\nDự án: {project.name}\nNgười nhận: {item.name}")
    if not result.sent:
        detail = "Bot Telegram chưa được cấu hình trên máy chủ." if result.error_category == "NOT_CONFIGURED" else "Không thể gửi tin nhắn thử qua Telegram."
        raise HTTPException(status_code=503, detail=detail)
    return TestMessageResult(sent=True, detail="Đã gửi tin nhắn thử")
