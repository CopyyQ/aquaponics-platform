from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_operational_user, require_roles
from app.db.session import get_db
from app.core.enums import AlertStatus, AlertType, UserRole
from app.models.alert import SensorAlert
from app.models.user import User
from app.models.sensor import Sensor
from app.models.device import Device
from app.schemas.alert import AlertRead, AlertResolutionRequest
from app.services.audit_service import write_audit
from app.services.access_service import accessible_device_clause
from app.services.alert_service import AlertResolutionError, resolve_alert_manually

router = APIRouter(prefix="/alerts", tags=["Alerts"])


async def get_alert_or_404(db: AsyncSession, alert_id: int, actor: User) -> SensorAlert:
    alert = await db.scalar(
        select(SensorAlert)
        .join(Sensor, SensorAlert.sensor_id == Sensor.id)
        .join(Device, Sensor.device_id == Device.id)
        .where(
            SensorAlert.id == alert_id,
            Sensor.is_deleted.is_(False),
            Sensor.deleted_at.is_(None),
            Sensor.is_enabled.is_(True),
            Device.is_deleted.is_(False),
            Device.deleted_at.is_(None),
            Device.is_enabled.is_(True),
            accessible_device_clause(actor),
        )
    )
    if alert is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy cảnh báo")
    return alert


@router.get("", response_model=list[AlertRead])
async def list_alerts(
    status: AlertStatus | None = None,
    alert_type: AlertType | None = None,
    sensor_id: int | None = None,
    db: AsyncSession = Depends(get_db),
    actor: User = Depends(get_current_operational_user),
) -> list[SensorAlert]:
    query = (
        select(SensorAlert)
        .join(Sensor, SensorAlert.sensor_id == Sensor.id)
        .join(Device, Sensor.device_id == Device.id)
        .where(
            Sensor.is_deleted.is_(False),
            Sensor.is_enabled.is_(True),
            Device.is_deleted.is_(False),
            Device.is_enabled.is_(True),
            accessible_device_clause(actor),
        )
        .order_by(SensorAlert.started_at.desc())
    )
    if status:
        query = query.where(SensorAlert.status == status)
    if alert_type:
        query = query.where(SensorAlert.alert_type == alert_type)
    if sensor_id:
        query = query.where(SensorAlert.sensor_id == sensor_id)
    return list((await db.scalars(query.limit(500))).all())


@router.get("/{alert_id}", response_model=AlertRead)
async def get_alert(
    alert_id: int,
    db: AsyncSession = Depends(get_db),
    actor: User = Depends(get_current_operational_user),
) -> SensorAlert:
    return await get_alert_or_404(db, alert_id, actor)


@router.post("/{alert_id}/acknowledge", response_model=AlertRead)
async def acknowledge_alert(
    alert_id: int,
    db: AsyncSession = Depends(get_db),
    actor: User = Depends(require_roles(UserRole.ADMIN, UserRole.OWNER)),
) -> SensorAlert:
    alert = await get_alert_or_404(db, alert_id, actor)
    if alert.status == AlertStatus.RESOLVED:
        raise HTTPException(status_code=409, detail="Cảnh báo đã được xử lý")
    alert.status = AlertStatus.ACKNOWLEDGED
    alert.acknowledged_at = datetime.now(UTC)
    alert.acknowledged_by = actor.id
    await write_audit(
        db,
        user_id=actor.id,
        action="ACKNOWLEDGE_ALERT",
        entity_type="SENSOR_ALERT",
        entity_id=alert.id,
    )
    await db.commit()
    await db.refresh(alert)
    return alert


@router.post("/{alert_id}/resolve", response_model=AlertRead)
async def resolve_alert(
    alert_id: int,
    payload: AlertResolutionRequest,
    db: AsyncSession = Depends(get_db),
    actor: User = Depends(require_roles(UserRole.ADMIN, UserRole.OWNER)),
) -> SensorAlert:
    alert = await get_alert_or_404(db, alert_id, actor)
    project_id = await db.scalar(
        select(Device.project_id).join(Sensor, Sensor.device_id == Device.id).where(Sensor.id == alert.sensor_id)
    )
    if project_id is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy Project của cảnh báo")
    try:
        return await resolve_alert_manually(
            db,
            alert=alert,
            actor=actor,
            project_id=project_id,
            resolution_note=payload.resolution_note,
        )
    except AlertResolutionError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
