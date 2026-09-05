from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_admin
from app.db.session import get_db
from app.models.operational_alert import AlertRule, NotificationDelivery, OperationalIncident
from app.models.project import Project
from app.models.project_settings import ProjectNotificationRecipient
from app.models.user import User
from app.schemas.operational_alert import NotificationDeliveryRead

router = APIRouter(prefix="/admin/notification-deliveries", tags=["Admin notification deliveries"])


@router.get("/history", response_model=list[NotificationDeliveryRead])
async def notification_delivery_history(
    db: AsyncSession = Depends(get_db), _: User = Depends(require_admin)
) -> list[NotificationDeliveryRead]:
    rows = (await db.execute(
        select(NotificationDelivery, OperationalIncident, AlertRule, Project, ProjectNotificationRecipient)
        .join(OperationalIncident, OperationalIncident.id == NotificationDelivery.incident_id)
        .outerjoin(AlertRule, AlertRule.id == OperationalIncident.rule_id)
        .join(Project, Project.id == OperationalIncident.project_id)
        .outerjoin(ProjectNotificationRecipient, ProjectNotificationRecipient.id == NotificationDelivery.recipient_id)
        .order_by(NotificationDelivery.created_at.desc()).limit(1000)
    )).all()
    return [
        NotificationDeliveryRead(
            id=delivery.id, created_at=delivery.created_at, project_id=project.id,
            project_name=project.name,
            rule_name=rule.name if rule else str((incident.trigger_snapshot or {}).get("sensor_name") or "Ngưỡng cảm biến"),
            business_risk_level=incident.business_risk_level_snapshot,
            channel=delivery.channel,
            recipient_name=recipient.name if recipient else delivery.recipient_reference,
            status=delivery.status, attempt_count=delivery.attempt_count,
            reason=delivery.error_category,
        )
        for delivery, incident, rule, project, recipient in rows
    ]
