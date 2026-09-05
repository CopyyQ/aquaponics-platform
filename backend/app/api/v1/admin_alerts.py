from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from app.api.deps import require_roles
from app.db.session import get_db
from app.core.enums import AlertSeverity, AlertStatus, UserRole
from app.models.alert import SensorAlert
from app.models.device import Device
from app.models.project import Project
from app.models.sensor import Sensor, SensorModel
from app.models.telemetry import TelemetryReading
from app.models.user import User
from app.schemas.alert import AlertResolutionRequest
from app.services.audit_service import write_audit
from app.services.access_service import active_project_clause
from app.services.alert_service import AlertResolutionError, resolve_alert_manually

router = APIRouter(prefix="/admin/alerts", tags=["Admin alerts"])


def context(
    alert: SensorAlert,
    sensor: Sensor,
    model: SensorModel,
    device: Device,
    project: Project,
    owner: User,
    resolver: User | None,
) -> dict:
    return {
        "id": alert.id, "alert_type": alert.alert_type, "severity": alert.severity,
        "status": alert.status, "message": alert.message, "trigger_value": alert.trigger_value,
        "started_at": alert.started_at, "acknowledged_at": alert.acknowledged_at,
        "acknowledged_by": alert.acknowledged_by, "resolved_at": alert.resolved_at,
        "condition_active": alert.condition_active, "normalized_at": alert.normalized_at,
        "resolved_by_user_id": alert.resolved_by_user_id,
        "resolved_by_name": resolver.full_name if resolver else None,
        "resolution_note": alert.resolution_note,
        "project": {"id": project.id, "name": project.name},
        "customer": {"id": owner.id, "full_name": owner.full_name},
        "device": {"id": device.id, "name": device.name, "code": device.code},
        "sensor": {"id": sensor.id, "name": sensor.name, "code": sensor.code, "unit": model.unit, "model_code": model.code},
        "threshold": {"lower": sensor.lower_threshold, "upper": sensor.upper_threshold},
    }


async def base_rows(db: AsyncSession):
    owner = aliased(User)
    resolver = aliased(User)
    return list((await db.execute(select(SensorAlert, Sensor, SensorModel, Device, Project, owner, resolver).join(Sensor, Sensor.id == SensorAlert.sensor_id).join(SensorModel, SensorModel.id == Sensor.sensor_model_id).join(Device, Device.id == Sensor.device_id).join(Project, Project.id == Device.project_id).join(owner, owner.id == Project.owner_user_id).outerjoin(resolver, resolver.id == SensorAlert.resolved_by_user_id).where(Sensor.is_deleted.is_(False), Sensor.deleted_at.is_(None), Sensor.is_enabled.is_(True), Device.is_deleted.is_(False), Device.deleted_at.is_(None), Device.is_enabled.is_(True), active_project_clause(Project)))).all())


@router.get("")
async def list_admin_alerts(
    severity: AlertSeverity | None = None, status: AlertStatus | None = None,
    customer_id: int | None = None, project_id: int | None = None, device_id: int | None = None,
    sensor_type: str | None = None, unacknowledged: bool = False,
    page: int = Query(default=1, ge=1), page_size: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db), _: User = Depends(require_roles(UserRole.ADMIN)),
) -> dict:
    rows = await base_rows(db)
    if severity:
        rows = [row for row in rows if row[0].severity == severity]
    if status:
        rows = [row for row in rows if row[0].status == status]
    if customer_id:
        rows = [row for row in rows if row[5].id == customer_id]
    if project_id:
        rows = [row for row in rows if row[4].id == project_id]
    if device_id:
        rows = [row for row in rows if row[3].id == device_id]
    if sensor_type:
        rows = [row for row in rows if row[2].code == sensor_type]
    if unacknowledged:
        rows = [row for row in rows if row[0].acknowledged_at is None]
    rows.sort(key=lambda row: (row[0].severity == AlertSeverity.CRITICAL, row[0].started_at), reverse=True)
    total = len(rows)
    start = (page - 1) * page_size
    return {"items": [context(*row) for row in rows[start:start + page_size]], "total": total, "page": page, "page_size": page_size}


async def get_row(db: AsyncSession, alert_id: int):
    row = next((row for row in await base_rows(db) if row[0].id == alert_id), None)
    if row is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy cảnh báo")
    return row


@router.get("/{alert_id}")
async def admin_alert_detail(alert_id: int, db: AsyncSession = Depends(get_db), _: User = Depends(require_roles(UserRole.ADMIN))) -> dict:
    row = await get_row(db, alert_id)
    result = context(*row)
    alert = row[0]
    readings = list((await db.scalars(select(TelemetryReading).where(TelemetryReading.sensor_id == alert.sensor_id).order_by(func.abs(func.extract("epoch", TelemetryReading.recorded_at - alert.started_at))).limit(12))).all())
    result["telemetry_context"] = [{"value": item.value, "recorded_at": item.recorded_at} for item in sorted(readings, key=lambda item: item.recorded_at)]
    latest_reading = await db.scalar(
        select(TelemetryReading)
        .where(TelemetryReading.sensor_id == alert.sensor_id)
        .order_by(TelemetryReading.recorded_at.desc())
        .limit(1)
    )
    result["current_value"] = latest_reading.value if latest_reading else None
    return result


async def acknowledge(alert_id: int, db: AsyncSession, actor: User) -> dict:
    row = await get_row(db, alert_id)
    alert = row[0]
    now = datetime.now(UTC)
    if alert.status == AlertStatus.RESOLVED:
        raise HTTPException(status_code=409, detail="Cảnh báo đã được xác nhận khắc phục")
    alert.acknowledged_at = now
    alert.acknowledged_by = actor.id
    alert.status = AlertStatus.ACKNOWLEDGED
    await write_audit(db, user_id=actor.id, action="ACKNOWLEDGED_ALERT", entity_type="SENSOR_ALERT", entity_id=alert.id)
    await db.commit()
    return context(*await get_row(db, alert_id))


@router.patch("/{alert_id}/acknowledge")
async def admin_acknowledge(alert_id: int, db: AsyncSession = Depends(get_db), actor: User = Depends(require_roles(UserRole.ADMIN))) -> dict:
    return await acknowledge(alert_id, db, actor)


@router.patch("/{alert_id}/resolve")
async def admin_resolve(
    alert_id: int,
    payload: AlertResolutionRequest,
    db: AsyncSession = Depends(get_db),
    actor: User = Depends(require_roles(UserRole.ADMIN)),
) -> dict:
    row = await get_row(db, alert_id)
    try:
        await resolve_alert_manually(
            db,
            alert=row[0],
            actor=actor,
            project_id=row[4].id,
            resolution_note=payload.resolution_note,
        )
    except AlertResolutionError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return context(*await get_row(db, alert_id))
