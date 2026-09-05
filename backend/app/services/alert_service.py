from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import AlertSeverity, AlertStatus, AlertType
from app.models.alert import SensorAlert
from app.models.sensor import Sensor
from app.models.user import User
from app.services.project_activity_service import record_project_activity

ACTIVE_STATUSES = [AlertStatus.PENDING, AlertStatus.OPEN, AlertStatus.ACKNOWLEDGED]


async def get_active_alert(
    db: AsyncSession, sensor_id: int, alert_type: AlertType
) -> SensorAlert | None:
    return await db.scalar(
        select(SensorAlert).where(
            SensorAlert.sensor_id == sensor_id,
            SensorAlert.alert_type == alert_type,
            SensorAlert.status.in_(ACTIVE_STATUSES),
        )
    )


async def normalize_active_alert(
    db: AsyncSession,
    sensor_id: int,
    alert_type: AlertType,
    normalized_at: datetime | None = None,
) -> SensorAlert | None:
    alert = await get_active_alert(db, sensor_id, alert_type)
    if alert and alert.condition_active:
        alert.condition_active = False
        alert.normalized_at = normalized_at or datetime.now(UTC)
        return alert
    return None


class AlertResolutionError(ValueError):
    pass


async def resolve_alert_manually(
    db: AsyncSession,
    *,
    alert: SensorAlert,
    actor: User,
    project_id: int,
    resolution_note: str,
) -> SensorAlert:
    if alert.status == AlertStatus.RESOLVED:
        raise AlertResolutionError("Cảnh báo đã được xác nhận khắc phục")
    if alert.condition_active:
        raise AlertResolutionError("Giá trị hiện tại vẫn đang nằm ngoài ngưỡng cảnh báo")
    now = datetime.now(UTC)
    previous_status = alert.status.value
    alert.status = AlertStatus.RESOLVED
    alert.resolved_at = now
    alert.resolved_by_user_id = actor.id
    alert.resolution_note = resolution_note.strip()
    await record_project_activity(
        db,
        project_id=project_id,
        actor=actor,
        action="ALERT_RESOLVED",
        entity_type="ALERT",
        entity_id=alert.id,
        entity_name=alert.message,
        changes={
            "status": {"before": previous_status, "after": AlertStatus.RESOLVED.value},
            "resolution_note": {"before": None, "after": alert.resolution_note},
        },
    )
    await db.commit()
    await db.refresh(alert)
    return alert


async def evaluate_threshold(db: AsyncSession, sensor: Sensor, value: float, recorded_at: datetime) -> list[tuple[SensorAlert, str]]:
    transitions: list[tuple[SensorAlert, str]] = []
    if not sensor.warning_enabled:
        return transitions

    alert_type: AlertType | None = None
    message = ""
    if sensor.lower_threshold is not None and value < sensor.lower_threshold:
        alert_type = AlertType.BELOW_LOWER_THRESHOLD
        message = f"{sensor.name} thấp hơn ngưỡng dưới {sensor.lower_threshold}"
        await normalize_active_alert(db, sensor.id, AlertType.ABOVE_UPPER_THRESHOLD, recorded_at)
    elif sensor.upper_threshold is not None and value > sensor.upper_threshold:
        alert_type = AlertType.ABOVE_UPPER_THRESHOLD
        message = f"{sensor.name} vượt ngưỡng trên {sensor.upper_threshold}"
        await normalize_active_alert(db, sensor.id, AlertType.BELOW_LOWER_THRESHOLD, recorded_at)
    else:
        await normalize_active_alert(db, sensor.id, AlertType.BELOW_LOWER_THRESHOLD, recorded_at)
        await normalize_active_alert(db, sensor.id, AlertType.ABOVE_UPPER_THRESHOLD, recorded_at)
        return transitions

    alert = await get_active_alert(db, sensor.id, alert_type)
    if alert is None:
        status = AlertStatus.OPEN if sensor.alert_delay_seconds == 0 else AlertStatus.PENDING
        new_alert = SensorAlert(
            sensor_id=sensor.id,
            alert_type=alert_type,
            severity=AlertSeverity.WARNING,
            status=status,
            message=message,
            trigger_value=value,
            started_at=recorded_at,
            last_triggered_at=recorded_at,
            occurrence_count=1,
        )
        db.add(new_alert)
        await db.flush()
        if status == AlertStatus.OPEN:
            transitions.append((new_alert, "OPENED"))
        return transitions

    alert.trigger_value = value
    alert.last_triggered_at = recorded_at
    alert.occurrence_count += 1
    alert.message = message
    if not alert.condition_active:
        alert.condition_active = True
        alert.normalized_at = None
        if alert.status == AlertStatus.PENDING:
            alert.started_at = recorded_at
    if (
        alert.status == AlertStatus.PENDING
        and recorded_at >= alert.started_at + timedelta(seconds=sensor.alert_delay_seconds)
    ):
        alert.status = AlertStatus.OPEN
        transitions.append((alert, "OPENED"))
    elif alert.status in {AlertStatus.OPEN, AlertStatus.ACKNOWLEDGED}:
        transitions.append((alert, "ABNORMAL_READING"))
    return transitions
