from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_operational_user
from app.core.config import settings
from app.core.enums import MonitoringRange
from app.db.session import get_db
from app.models.project_settings import ProjectPublicSettings
from app.models.user import User
from app.schemas.notifications import PublicSettingsRead, PublicSettingsUpdate
from app.services.access_service import require_project_access
from app.services.public_monitoring_service import get_public_overview, get_public_power_series, get_public_series, require_public_project
from app.services.project_activity_service import dispatch_project_activity, record_project_activity

router = APIRouter(tags=["Public monitoring"])


@router.get("/projects/{project_id}/public-settings", response_model=PublicSettingsRead)
async def get_public_settings(project_id: int, db: AsyncSession = Depends(get_db), actor: User = Depends(get_current_operational_user)) -> PublicSettingsRead:
    project = await require_project_access(db, project_id, actor, manage=True)
    item = await db.scalar(select(ProjectPublicSettings).where(ProjectPublicSettings.project_id == project_id))
    return PublicSettingsRead(
        enabled=item.enabled if item else False,
        remote_monitoring_available=settings.public_monitoring_project_id == project.id,
    )


@router.put("/projects/{project_id}/public-settings", response_model=PublicSettingsRead)
async def update_public_settings(project_id: int, payload: PublicSettingsUpdate, db: AsyncSession = Depends(get_db), actor: User = Depends(get_current_operational_user)) -> PublicSettingsRead:
    await require_project_access(db, project_id, actor, manage=True)
    if payload.enabled and settings.public_monitoring_project_id != project_id:
        raise HTTPException(status_code=409, detail="Dự án này không phải dự án Theo dõi từ xa được cấu hình")
    item = await db.scalar(select(ProjectPublicSettings).where(ProjectPublicSettings.project_id == project_id))
    before_enabled = item.enabled if item is not None else False
    if item is None:
        # public_slug is retained only for backward-compatible storage. It is no
        # longer part of the active API or routing contract.
        item = ProjectPublicSettings(project_id=project_id, enabled=payload.enabled, public_slug=f"remote-project-{project_id}")
        db.add(item)
    else:
        item.enabled = payload.enabled
    activity = None
    if before_enabled != payload.enabled:
        activity = await record_project_activity(db, project_id=project_id, actor=actor, action="REMOTE_MONITORING_ENABLED" if payload.enabled else "REMOTE_MONITORING_DISABLED", entity_type="REMOTE_MONITORING", entity_id=item.id, entity_name="Theo dõi từ xa", changes={"enabled": {"before": before_enabled, "after": payload.enabled}})
    await db.commit()
    if activity is not None:
        await dispatch_project_activity(db, activity_id=activity.id)
    return PublicSettingsRead(
        enabled=item.enabled,
        remote_monitoring_available=settings.public_monitoring_project_id == project_id,
    )


@router.get("/public-monitoring/overview")
async def public_overview(db: AsyncSession = Depends(get_db)) -> dict:
    project = await require_public_project(db)
    return await get_public_overview(db, project)


@router.get("/public-monitoring/telemetry-series")
async def public_telemetry_series(range: MonitoringRange = Query(default=MonitoringRange.TWENTY_FOUR_HOURS), db: AsyncSession = Depends(get_db)) -> dict:
    project = await require_public_project(db)
    return await get_public_series(db, project, range)


@router.get("/public-monitoring/energy/power-series")
async def public_energy_power_series(device_code: str, range: MonitoringRange = Query(default=MonitoringRange.TWENTY_FOUR_HOURS), db: AsyncSession = Depends(get_db)) -> dict:
    project = await require_public_project(db)
    return await get_public_power_series(db, project, device_code, range)
