import logging
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_operational_user, require_admin, require_roles
from app.db.session import get_db
from app.core.enums import AlertType, ProjectStatus, SensorPurpose, SensorStatus, UserRole
from app.models.sensor import Sensor, SensorModel
from app.models.user import User
from app.schemas.common import DisableReasonRequest, MessageResponse
from app.schemas.sensor import SensorCreate, SensorFromModelRequest, SensorRead, SensorThresholdUpdate, SensorUpdate
from app.services.alert_service import normalize_active_alert
from app.services.audit_service import write_audit
from app.services.access_service import accessible_device_clause, require_device_access, require_sensor_access
from app.services.project_activity_service import dispatch_project_activity, record_project_activity
from app.models.device import Device
from app.models.project import Project

router = APIRouter(tags=["Sensors"])
logger = logging.getLogger("uvicorn.error")


async def get_sensor_or_404(db: AsyncSession, sensor_id: int, include_deleted: bool = False) -> Sensor:
    query = select(Sensor).where(Sensor.id == sensor_id)
    if not include_deleted:
        query = query.where(Sensor.is_deleted.is_(False))
    sensor = await db.scalar(query)
    if sensor is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy cảm biến")
    return sensor


@router.get("/sensors", response_model=list[SensorRead])
async def list_sensors(
    device_id: int | None = None,
    db: AsyncSession = Depends(get_db),
    actor: User = Depends(get_current_operational_user),
) -> list[Sensor]:
    query = (
        select(Sensor)
        .join(Device, Sensor.device_id == Device.id)
        .where(
            Sensor.is_deleted.is_(False),
            Sensor.is_enabled.is_(True),
            Sensor.purpose == SensorPurpose.GENERAL,
            Device.is_enabled.is_(True),
            Device.is_deleted.is_(False),
            accessible_device_clause(actor),
        )
        .order_by(Sensor.created_at.desc())
    )
    if device_id is not None:
        query = query.where(Sensor.device_id == device_id)
    return list((await db.scalars(query)).all())


@router.get("/devices/{device_id}/sensors", response_model=list[SensorRead])
async def list_device_sensors(
    device_id: int,
    include_disabled: bool = Query(default=False),
    db: AsyncSession = Depends(get_db),
    actor: User = Depends(get_current_operational_user),
) -> list[Sensor]:
    if include_disabled and actor.system_role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Chỉ Admin được xem cảm biến đã tắt")
    await require_device_access(db, device_id, actor, allow_disabled=include_disabled)
    query = select(Sensor).where(
        Sensor.device_id == device_id,
        Sensor.is_deleted.is_(False),
        Sensor.deleted_at.is_(None),
        Sensor.purpose == SensorPurpose.GENERAL,
    )
    if not include_disabled:
        query = query.where(Sensor.is_enabled.is_(True))
    return list(
        (
            await db.scalars(
                query.order_by(Sensor.name)
            )
        ).all()
    )


async def _sensor_lifecycle_context(db: AsyncSession, device_id: int, sensor_id: int) -> tuple[Device, Project, Sensor]:
    context = (await db.execute(select(Device, Project).join(Project, Project.id == Device.project_id).where(
        Device.id == device_id, Device.is_deleted.is_(False), Device.deleted_at.is_(None),
        Project.is_deleted.is_(False), Project.deleted_at.is_(None),
    ))).first()
    if context is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy thiết bị")
    device, project = context
    if project.status != ProjectStatus.ACTIVE:
        raise HTTPException(status_code=409, detail={"code": "PROJECT_NOT_ACTIVE", "detail": "Dự án không ở trạng thái hoạt động."})
    sensor = await db.scalar(select(Sensor).where(
        Sensor.id == sensor_id, Sensor.device_id == device.id,
        Sensor.is_deleted.is_(False), Sensor.deleted_at.is_(None),
    ))
    if sensor is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy cảm biến trong thiết bị")
    return device, project, sensor


@router.post("/devices/{device_id}/sensors/{sensor_id}/disable", status_code=204)
async def disable_device_sensor(
    device_id: int,
    sensor_id: int,
    payload: DisableReasonRequest,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
) -> Response:
    device, project, sensor = await _sensor_lifecycle_context(db, device_id, sensor_id)
    old_data = {"is_enabled": sensor.is_enabled}
    sensor.is_enabled = False
    sensor.disabled_at = datetime.now(UTC)
    sensor.disabled_by_user_id = admin.id
    sensor.disabled_reason = payload.reason.strip() or None
    activity = await record_project_activity(db, project_id=project.id, actor=admin, action="SENSOR_DISABLED", entity_type="SENSOR", entity_id=sensor.id, entity_name=sensor.name, changes={"is_enabled": {"before": old_data["is_enabled"], "after": False}})
    await db.commit()
    await dispatch_project_activity(db, activity_id=activity.id)
    return Response(status_code=204)


@router.post("/devices/{device_id}/sensors/{sensor_id}/activate", status_code=204)
async def activate_device_sensor(
    device_id: int, sensor_id: int, db: AsyncSession = Depends(get_db), admin: User = Depends(require_admin)
) -> Response:
    device, project, sensor = await _sensor_lifecycle_context(db, device_id, sensor_id)
    old_data = {"is_enabled": sensor.is_enabled, "disabled_reason": sensor.disabled_reason}
    sensor.is_enabled = True
    sensor.disabled_at = None
    sensor.disabled_by_user_id = None
    sensor.disabled_reason = None
    activity = await record_project_activity(db, project_id=project.id, actor=admin, action="SENSOR_ENABLED", entity_type="SENSOR", entity_id=sensor.id, entity_name=sensor.name, changes={"is_enabled": {"before": old_data["is_enabled"], "after": True}})
    await db.commit()
    await dispatch_project_activity(db, activity_id=activity.id)
    return Response(status_code=204)


@router.post("/devices/{device_id}/sensors", response_model=SensorRead, status_code=201)
async def create_sensor(
    device_id: int,
    payload: SensorCreate,
    db: AsyncSession = Depends(get_db),
    actor: User = Depends(require_roles(UserRole.ADMIN)),
) -> Sensor:
    device = await require_device_access(db, device_id, actor, manage=True)
    model = await db.scalar(
        select(SensorModel).where(
            SensorModel.id == payload.sensor_model_id,
            SensorModel.is_deleted.is_(False),
        )
    )
    if model is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy mẫu cảm biến")
    exists = await db.scalar(
        select(Sensor.id).where(Sensor.device_id == device_id, Sensor.code == payload.code)
    )
    if exists:
        raise HTTPException(status_code=409, detail="Mã cảm biến đã tồn tại trong thiết bị")
    sensor = Sensor(
        device_id=device_id,
        sensor_model_id=model.id,
        code=payload.code,
        name=payload.name,
        description=payload.description,
        status=SensorStatus.WAITING_CONNECTION,
        warning_enabled=model.default_warning_enabled,
        lower_threshold=model.default_lower_threshold,
        upper_threshold=model.default_upper_threshold,
        below_threshold_message=model.default_below_threshold_message,
        above_threshold_message=model.default_above_threshold_message,
        alert_risk_level=model.default_alert_risk_level,
        alert_delay_seconds=0,
    )
    db.add(sensor)
    await db.flush()
    activity = await record_project_activity(db, project_id=device.project_id, actor=actor, action="SENSOR_ADDED", entity_type="SENSOR", entity_id=sensor.id, entity_name=sensor.name, changes={"created": True})
    await db.commit()
    await db.refresh(sensor)
    await dispatch_project_activity(db, activity_id=activity.id)
    return sensor


@router.post("/devices/{device_id}/sensors/from-model", response_model=SensorRead, status_code=201)
async def create_sensor_from_model(
    device_id: int,
    payload: SensorFromModelRequest,
    db: AsyncSession = Depends(get_db),
    actor: User = Depends(require_roles(UserRole.ADMIN)),
) -> Sensor:
    device = await require_device_access(db, device_id, actor, manage=True)
    project = await db.get(Project, device.project_id)
    if project is None or project.is_deleted or project.status != ProjectStatus.ACTIVE:
        raise HTTPException(status_code=400, detail="Dự án của thiết bị không hoạt động")
    model = await db.scalar(select(SensorModel).where(
        SensorModel.id == payload.sensor_model_id,
        SensorModel.is_active.is_(True), SensorModel.is_deleted.is_(False),
    ))
    if model is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy mẫu cảm biến đang khả dụng")
    duplicate = await db.scalar(select(Sensor.id).where(
        Sensor.device_id == device.id, Sensor.sensor_model_id == model.id, Sensor.is_deleted.is_(False),
    ))
    if duplicate:
        raise HTTPException(status_code=409, detail="Thiết bị đã có cảm biến thuộc mẫu này")
    if db.bind and db.bind.dialect.name == "postgresql":
        await db.execute(text("SELECT pg_advisory_xact_lock(hashtext(:key))"), {"key": f"sensor-code:{device.id}:{model.id}"})
    prefix = f"{device.code}-{model.code}"[:77]
    existing = set((await db.scalars(select(Sensor.code).where(Sensor.code.like(f"{prefix}-%")))).all())
    sequence = 1
    code = f"{prefix}-{sequence:02d}"[:80]
    while code in existing:
        sequence += 1
        code = f"{prefix}-{sequence:02d}"[:80]
    sensor = Sensor(
        device_id=device.id, sensor_model_id=model.id, code=code, name=model.name,
        status=SensorStatus.WAITING_CONNECTION, lower_threshold=model.default_lower_threshold,
        upper_threshold=model.default_upper_threshold,
        warning_enabled=model.default_warning_enabled,
        below_threshold_message=model.default_below_threshold_message,
        above_threshold_message=model.default_above_threshold_message,
        alert_risk_level=model.default_alert_risk_level,
        alert_delay_seconds=0,
    )
    db.add(sensor)
    await db.flush()
    activity = await record_project_activity(db, project_id=project.id, actor=actor, action="SENSOR_ADDED", entity_type="SENSOR", entity_id=sensor.id, entity_name=sensor.name, changes={"sensor_model": model.code})
    await db.commit()
    await db.refresh(sensor)
    await dispatch_project_activity(db, activity_id=activity.id)
    return sensor


@router.get("/sensors/{sensor_id}", response_model=SensorRead)
async def get_sensor(
    sensor_id: int,
    db: AsyncSession = Depends(get_db),
    actor: User = Depends(get_current_operational_user),
) -> Sensor:
    return await require_sensor_access(db, sensor_id, actor, allow_disabled=actor.system_role == UserRole.ADMIN)


@router.get(
    "/projects/{project_id}/devices/{device_id}/sensors/{sensor_id}",
    response_model=SensorRead,
)
async def get_project_device_sensor(
    project_id: int,
    device_id: int,
    sensor_id: int,
    db: AsyncSession = Depends(get_db),
    actor: User = Depends(get_current_operational_user),
) -> Sensor:
    device = await require_device_access(
        db,
        device_id,
        actor,
        allow_disabled=actor.system_role == UserRole.ADMIN,
    )
    if device.project_id != project_id:
        raise HTTPException(status_code=404, detail="Thiết bị không thuộc Project")
    query = select(Sensor).where(
        Sensor.id == sensor_id,
        Sensor.device_id == device.id,
        Sensor.is_deleted.is_(False),
        Sensor.deleted_at.is_(None),
    )
    if actor.system_role != UserRole.ADMIN:
        query = query.where(Sensor.is_enabled.is_(True))
    sensor = await db.scalar(query)
    if sensor is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy cảm biến trong thiết bị")
    return sensor


@router.patch("/sensors/{sensor_id}", response_model=SensorRead)
async def update_sensor(
    sensor_id: int,
    payload: SensorUpdate,
    db: AsyncSession = Depends(get_db),
    actor: User = Depends(require_roles(UserRole.ADMIN)),
) -> Sensor:
    sensor = await require_sensor_access(db, sensor_id, actor, manage=True)
    device = await db.get(Device, sensor.device_id)
    if device is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy thiết bị của cảm biến")
    values = payload.model_dump(exclude_unset=True)
    before = {key: getattr(sensor, key) for key in values}
    for key, value in values.items():
        setattr(sensor, key, value)
    changes = {key: {"before": before[key], "after": value} for key, value in values.items() if before[key] != value}
    if not changes:
        return sensor
    activity = await record_project_activity(db, project_id=device.project_id, actor=actor, action="SENSOR_UPDATED", entity_type="SENSOR", entity_id=sensor.id, entity_name=sensor.name, changes=changes)
    await db.commit()
    await db.refresh(sensor)
    await dispatch_project_activity(db, activity_id=activity.id)
    return sensor


@router.patch(
    "/projects/{project_id}/devices/{device_id}/sensors/{sensor_id}",
    response_model=SensorRead,
)
async def update_project_sensor(
    project_id: int,
    device_id: int,
    sensor_id: int,
    payload: SensorUpdate,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
) -> Sensor:
    device, project, sensor = await _sensor_lifecycle_context(db, device_id, sensor_id)
    if device.project_id != project_id:
        raise HTTPException(status_code=404, detail="Cảm biến không thuộc Project")
    values = payload.model_dump(exclude_unset=True)
    before = {key: getattr(sensor, key) for key in values}
    for key, value in values.items():
        setattr(sensor, key, value)
    changes = {key: {"before": before[key], "after": value} for key, value in values.items() if before[key] != value}
    if not changes:
        return sensor
    activity = await record_project_activity(db, project_id=project.id, actor=admin, action="SENSOR_UPDATED", entity_type="SENSOR", entity_id=sensor.id, entity_name=sensor.name, changes=changes)
    await db.commit()
    await db.refresh(sensor)
    await dispatch_project_activity(db, activity_id=activity.id)
    return sensor


@router.patch("/sensors/{sensor_id}/thresholds", response_model=SensorRead)
async def update_sensor_thresholds(
    sensor_id: int,
    payload: SensorThresholdUpdate,
    db: AsyncSession = Depends(get_db),
    actor: User = Depends(require_roles(UserRole.ADMIN, UserRole.OWNER)),
) -> Sensor:
    sensor = await require_sensor_access(db, sensor_id, actor, manage=True)
    old_data = {
        "warning_enabled": sensor.warning_enabled,
        "lower_threshold": sensor.lower_threshold,
        "upper_threshold": sensor.upper_threshold,
        "alert_delay_seconds": sensor.alert_delay_seconds,
        "below_threshold_message": sensor.below_threshold_message,
        "above_threshold_message": sensor.above_threshold_message,
        "alert_risk_level": sensor.alert_risk_level,
    }
    device = await db.get(Device, sensor.device_id)
    if device is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy thiết bị của cảm biến")
    sensor.warning_enabled = payload.warning_enabled
    sensor.lower_threshold = payload.lower_threshold
    sensor.upper_threshold = payload.upper_threshold
    sensor.alert_delay_seconds = payload.alert_delay_seconds
    sensor.below_threshold_message = payload.below_threshold_message
    sensor.above_threshold_message = payload.above_threshold_message
    sensor.alert_risk_level = payload.alert_risk_level
    if not payload.warning_enabled:
        await normalize_active_alert(db, sensor.id, AlertType.BELOW_LOWER_THRESHOLD)
        await normalize_active_alert(db, sensor.id, AlertType.ABOVE_UPPER_THRESHOLD)
    after_data = payload.model_dump()
    changes = {key: {"before": old_data[key], "after": value} for key, value in after_data.items() if old_data[key] != value}
    if not changes:
        return sensor
    activity = await record_project_activity(db, project_id=device.project_id, actor=actor, action="SENSOR_UPDATED", entity_type="SENSOR", entity_id=sensor.id, entity_name=sensor.name, changes=changes)
    await db.commit()
    await db.refresh(sensor)
    await dispatch_project_activity(db, activity_id=activity.id)
    return sensor


@router.delete("/sensors/{sensor_id}", status_code=204)
async def delete_sensor(
    sensor_id: int,
    db: AsyncSession = Depends(get_db),
    actor: User = Depends(require_roles(UserRole.ADMIN)),
) -> Response:
    sensor = await get_sensor_or_404(db, sensor_id)
    sensor.is_deleted = True
    sensor.deleted_at = datetime.now(UTC)
    await write_audit(db, user_id=actor.id, action="DELETE_SENSOR", entity_type="SENSOR", entity_id=sensor.id)
    await db.commit()
    return Response(status_code=204)


@router.post("/sensors/{sensor_id}/restore", response_model=MessageResponse)
async def restore_sensor(
    sensor_id: int,
    db: AsyncSession = Depends(get_db),
    actor: User = Depends(require_roles(UserRole.ADMIN)),
) -> MessageResponse:
    sensor = await get_sensor_or_404(db, sensor_id, include_deleted=True)
    sensor.is_deleted = False
    sensor.deleted_at = None
    await write_audit(db, user_id=actor.id, action="RESTORE_SENSOR", entity_type="SENSOR", entity_id=sensor.id)
    await db.commit()
    return MessageResponse(message="Đã khôi phục cảm biến")
