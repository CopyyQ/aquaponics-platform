"""Typed system-scoped operational resources."""

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import require_permission
from app.core.enums import MonitoringRange
from app.db.session import get_db
from app.models.project_member import ProjectMember
from app.models.project import Project
from app.models.device import Device
from app.models.sensor import Sensor
from app.models.actuator import Actuator
from app.models.project_settings import ProjectNotificationSettings
from app.models.user import User
from app.schemas.monitoring import MonitoringActuatorHistoryRead, MonitoringLatestRead, MonitoringSeriesRead
from app.schemas.project_activity import (AquaponicsSystemActivityActor, AquaponicsSystemActivityEntity,
    AquaponicsSystemActivityListResponse, AquaponicsSystemActivityRead)
from app.schemas.scada import ScadaLayout, ScadaLayoutMutationResponse, ScadaRuntimeResponse
from app.services.access_service import require_project_access
from app.services.monitoring_service import get_device_actuator_history, get_project_monitoring_latest, get_project_monitoring_series
from app.services.project_activity_service import ACTION_LABELS, list_project_activities
from app.services.scada_runtime_service import (ScadaDraftNotFoundError, ScadaLayoutValidationError,
    get_scada_runtime, publish_scada_draft, save_scada_draft)
from app.services.notification_outbox_service import next_notification_generation, reconcile_active_incident_notifications
from app.services.aquaponics_system_membership_service import (
    MembershipError, assign_system_member, remove_system_member, update_system_member_role,
)
from app.services.public_identity_service import (
    PublicIdentityNotFoundError, get_device_by_public_id, get_system_by_public_id,
    get_user_by_public_id,
)

router = APIRouter(prefix="/aquaponics-systems")


class AlertSettingsRead(BaseModel):
    enabled: bool
    in_app_enabled: bool
    telegram_enabled: bool


class AlertSettingsUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    enabled: bool = True
    in_app_enabled: bool = True
    telegram_enabled: bool = False


class AquaponicsSystemMemberCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    user_id: UUID
    role: str = Field(default="VIEWER", pattern="^(VIEWER|TECHNICIAN)$")


class AquaponicsSystemMemberUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    role: str = Field(pattern="^(VIEWER|TECHNICIAN)$")


class AquaponicsSystemMemberRead(BaseModel):
    id: int
    user_id: UUID
    name: str
    role: str
    joined_at: datetime


def _settings_read(item: ProjectNotificationSettings | None) -> AlertSettingsRead:
    return AlertSettingsRead(enabled=bool(item.enabled) if item else True,
        in_app_enabled=bool(item.in_app_enabled) if item else True, telegram_enabled=bool(item.telegram_enabled) if item else False)


def _member_read(row: ProjectMember) -> AquaponicsSystemMemberRead:
    return AquaponicsSystemMemberRead(id=row.id, user_id=row.user.public_id, name=row.user.full_name,
        role=row.role, joined_at=row.created_at)


def _membership_http_error(exc: MembershipError) -> HTTPException:
    return HTTPException(exc.status_code, {"code": exc.code, "detail": exc.message})


async def _system(db: AsyncSession, system_id: UUID, actor: User, *, manage: bool = False) -> Project:
    try:
        system = await get_system_by_public_id(db, system_id)
    except PublicIdentityNotFoundError as exc:
        raise HTTPException(404, str(exc)) from exc
    return await require_project_access(db, system.id, actor, manage=manage)


@router.get("/{system_id}/monitoring/latest", response_model=MonitoringLatestRead, tags=["Monitoring"])
async def monitoring_latest(system_id: UUID, db: AsyncSession = Depends(get_db), actor: User = Depends(require_permission("monitoring.read"))) -> dict:
    system = await _system(db, system_id, actor)
    payload = await get_project_monitoring_latest(db, system.id)
    payload["aquaponics_system_id"] = payload.pop("project_id")
    for device in payload.get("devices", []):
        for actuator in device.get("actuators", []):
            actuator["active_alert"] = actuator.pop("active_incident", None)
    return payload


@router.get("/{system_id}/monitoring/series", response_model=MonitoringSeriesRead, tags=["Monitoring"])
async def monitoring_series(system_id: UUID, range: MonitoringRange = Query(default=MonitoringRange.TWENTY_FOUR_HOURS), db: AsyncSession = Depends(get_db), actor: User = Depends(require_permission("monitoring.read"))) -> dict:
    system = await _system(db, system_id, actor)
    payload = await get_project_monitoring_series(db, project_id=system.id, monitoring_range=range)
    payload["aquaponics_system_id"] = payload.pop("project_id")
    return payload


@router.get("/{system_id}/devices/{device_id}/monitoring/actuator-history", response_model=MonitoringActuatorHistoryRead, tags=["Monitoring"])
async def monitoring_actuator_history(system_id: UUID, device_id: UUID, range: MonitoringRange = Query(default=MonitoringRange.TWENTY_FOUR_HOURS), db: AsyncSession = Depends(get_db), actor: User = Depends(require_permission("monitoring.read"))) -> dict:
    system = await _system(db, system_id, actor)
    try:
        device = await get_device_by_public_id(db, system, device_id)
    except PublicIdentityNotFoundError as exc:
        raise HTTPException(404, str(exc)) from exc
    payload = await get_device_actuator_history(db, project_id=system.id, device_id=device.id, monitoring_range=range)
    payload["aquaponics_system_id"] = payload.pop("project_id")
    return payload


@router.get("/{system_id}/members", response_model=list[AquaponicsSystemMemberRead], tags=["Members"])
async def list_members(system_id: UUID, db: AsyncSession = Depends(get_db), actor: User = Depends(require_permission("aquaponics_systems.read"))) -> list[AquaponicsSystemMemberRead]:
    system = await _system(db, system_id, actor)
    rows = (await db.scalars(select(ProjectMember).options(selectinload(ProjectMember.user)).where(ProjectMember.project_id == system.id).order_by(ProjectMember.created_at))).all()
    return [_member_read(row) for row in rows]


@router.post("/{system_id}/members", response_model=AquaponicsSystemMemberRead, status_code=201, tags=["Members"])
async def add_member(system_id: UUID, payload: AquaponicsSystemMemberCreate, db: AsyncSession = Depends(get_db), actor: User = Depends(require_permission("aquaponics_systems.manage_members"))) -> AquaponicsSystemMemberRead:
    system = await _system(db, system_id, actor, manage=True)
    try: user = await get_user_by_public_id(db, payload.user_id)
    except PublicIdentityNotFoundError as exc: raise HTTPException(404, str(exc)) from exc
    try:
        row = await assign_system_member(db, system_id=system.id, user_id=user.id, role=payload.role, created_by=actor.id)
    except MembershipError as exc:
        raise _membership_http_error(exc) from exc
    row = await db.scalar(select(ProjectMember).options(selectinload(ProjectMember.user)).where(ProjectMember.id == row.id))
    return _member_read(row)


@router.patch("/{system_id}/members/{user_id}", response_model=AquaponicsSystemMemberRead, tags=["Members"])
async def update_member(system_id: UUID, user_id: UUID, payload: AquaponicsSystemMemberUpdate, db: AsyncSession = Depends(get_db), actor: User = Depends(require_permission("aquaponics_systems.manage_members"))) -> AquaponicsSystemMemberRead:
    system = await _system(db, system_id, actor, manage=True)
    try: user = await get_user_by_public_id(db, user_id)
    except PublicIdentityNotFoundError as exc: raise HTTPException(404, str(exc)) from exc
    try:
        await update_system_member_role(db, system_id=system.id, user_id=user.id, role=payload.role, created_by=actor.id)
    except MembershipError as exc:
        raise _membership_http_error(exc) from exc
    row = await db.scalar(select(ProjectMember).options(selectinload(ProjectMember.user)).where(ProjectMember.project_id == system.id, ProjectMember.user_id == user.id))
    return _member_read(row)


@router.delete("/{system_id}/members/{user_id}", status_code=204, tags=["Members"])
async def remove_member(system_id: UUID, user_id: UUID, db: AsyncSession = Depends(get_db), actor: User = Depends(require_permission("aquaponics_systems.manage_members"))) -> None:
    system = await _system(db, system_id, actor, manage=True)
    try: user = await get_user_by_public_id(db, user_id)
    except PublicIdentityNotFoundError as exc: raise HTTPException(404, str(exc)) from exc
    try:
        await remove_system_member(db, system_id=system.id, user_id=user.id)
    except MembershipError as exc:
        raise _membership_http_error(exc) from exc


@router.get("/{system_id}/activities", response_model=AquaponicsSystemActivityListResponse, tags=["Activities"])
async def activities(system_id: UUID, page: int = Query(default=1, ge=1), page_size: int = Query(default=50, ge=1, le=100), action: str | None = None, entity_type: str | None = None, db: AsyncSession = Depends(get_db), actor: User = Depends(require_permission("activities.read"))) -> AquaponicsSystemActivityListResponse:
    system = await _system(db, system_id, actor)
    items, total = await list_project_activities(db, project_id=system.id, page=page, page_size=page_size, action=action, entity_type=entity_type)
    ids = {item.user_id for item in items}
    users = {u.id: u for u in (await db.scalars(select(User).where(User.id.in_(ids)))).all()} if ids else {}
    core_models = {"USER": User, "PROJECT": Project, "AQUAPONICS_SYSTEM": Project, "DEVICE": Device, "SENSOR": Sensor, "ACTUATOR": Actuator}
    public_entities: dict[tuple[str, int], UUID] = {}
    for core_type, model in core_models.items():
        entity_ids = {item.entity_id for item in items if item.entity_type == core_type and item.entity_id is not None}
        if entity_ids:
            rows = (await db.execute(select(model.id, model.public_id).where(model.id.in_(entity_ids)))).all()
            public_entities.update({(core_type, internal_id): public_id for internal_id, public_id in rows})
    return AquaponicsSystemActivityListResponse(items=[AquaponicsSystemActivityRead(id=i.id, action=i.action,
        actor=AquaponicsSystemActivityActor(id=users[i.user_id].public_id, name=users[i.user_id].full_name),
        entity=AquaponicsSystemActivityEntity(type=i.entity_type, id=public_entities.get((i.entity_type, i.entity_id), i.entity_id), name=str((i.new_data or {}).get("display_name") or f"#{i.entity_id}")),
        summary=i.description or ACTION_LABELS.get(i.action, i.action), created_at=i.created_at) for i in items], total=total, page=page, page_size=page_size)


@router.get("/{system_id}/scada/runtime", response_model=ScadaRuntimeResponse, tags=["SCADA"])
async def scada_runtime(system_id: UUID, db: AsyncSession = Depends(get_db), actor: User = Depends(require_permission("scada.read"))) -> ScadaRuntimeResponse:
    return await get_scada_runtime(db, await _system(db, system_id, actor))


@router.put("/{system_id}/scada/layout/draft", response_model=ScadaLayoutMutationResponse, tags=["SCADA"])
async def scada_draft(system_id: UUID, payload: ScadaLayout, db: AsyncSession = Depends(get_db), actor: User = Depends(require_permission("scada.update"))) -> ScadaLayoutMutationResponse:
    project = await _system(db, system_id, actor, manage=True)
    try: return await save_scada_draft(db, project, actor, payload)
    except ScadaLayoutValidationError as exc: raise HTTPException(422, {"code": "INVALID_SCADA_LAYOUT", "detail": str(exc)}) from exc


@router.post("/{system_id}/scada/layout/publish", response_model=ScadaLayoutMutationResponse, tags=["SCADA"])
async def scada_publish(system_id: UUID, db: AsyncSession = Depends(get_db), actor: User = Depends(require_permission("scada.update"))) -> ScadaLayoutMutationResponse:
    project = await _system(db, system_id, actor, manage=True)
    try: return await publish_scada_draft(db, project, actor)
    except ScadaDraftNotFoundError as exc: raise HTTPException(409, {"code": "SCADA_DRAFT_NOT_FOUND", "detail": str(exc)}) from exc


@router.get("/{system_id}/alerts/settings", response_model=AlertSettingsRead, tags=["Alerts"])
async def get_alert_settings(system_id: UUID, db: AsyncSession = Depends(get_db), actor: User = Depends(require_permission("notifications.settings.read"))) -> AlertSettingsRead:
    system = await _system(db, system_id, actor)
    return _settings_read(await db.scalar(select(ProjectNotificationSettings).where(ProjectNotificationSettings.project_id == system.id)))


@router.put("/{system_id}/alerts/settings", response_model=AlertSettingsRead, tags=["Alerts"])
async def put_alert_settings(system_id: UUID, payload: AlertSettingsUpdate, db: AsyncSession = Depends(get_db), actor: User = Depends(require_permission("notifications.settings.update"))) -> AlertSettingsRead:
    system = await _system(db, system_id, actor, manage=True)
    item = await db.scalar(select(ProjectNotificationSettings).where(ProjectNotificationSettings.project_id == system.id))
    if item is None: item = ProjectNotificationSettings(project_id=system.id); db.add(item)
    changed = (item.enabled, item.telegram_enabled, item.in_app_enabled) != (payload.enabled, payload.telegram_enabled, payload.in_app_enabled)
    item.enabled = payload.enabled
    item.telegram_enabled = payload.telegram_enabled
    item.in_app_enabled = payload.in_app_enabled
    if changed:
        generation = await next_notification_generation(db, project_id=system.id)
        await reconcile_active_incident_notifications(
            db, project_id=system.id, generation=generation,
            reason="GENERAL_SETTINGS_CHANGED", skip_previously_informed=True,
        )
    await db.commit(); return _settings_read(item)
