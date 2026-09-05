from datetime import UTC, datetime

from fastapi import APIRouter, Body, Depends, HTTPException, Query
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_roles
from app.db.session import get_db
from app.core.enums import AlertStatus, DeviceStatus, UserRole, UserStatus
from app.core.security import hash_password
from app.models.alert import SensorAlert
from app.models.audit import AuditLog
from app.models.device import Device
from app.models.project import Project
from app.models.sensor import Sensor
from app.models.telemetry import TelemetryReading
from app.models.user import User
from app.schemas.common import MessageResponse
from app.schemas.device import DeviceRead
from app.schemas.project import (
    AdminProjectCreate,
    AdminUserProjectListResponse,
    AdminUserProjectRead,
    ProjectRead,
)
from app.schemas.user import (
    AccountLifecycleRequest,
    AdminSetPasswordRequest,
    AdminSetPasswordResponse,
    AdminUserCreate,
    AdminUserDetail,
    ResetPasswordRequest,
    UserUpdate,
)
from app.services.account_lifecycle_service import change_account_status, force_logout_user
from app.services.audit_service import write_audit
from app.services.project_activity_service import dispatch_project_activity, record_project_activity
from app.services.user_service import create_admin_user, update_user
from app.services.access_service import active_project_clause
from app.queries.project_queries import existing_project_clause

router = APIRouter(prefix="/admin/users", tags=["Admin users"])
ACTIVE_ALERTS = [AlertStatus.PENDING, AlertStatus.OPEN, AlertStatus.ACKNOWLEDGED]


async def get_user(db: AsyncSession, user_id: int) -> User:
    user = await db.scalar(select(User).where(User.id == user_id))
    if user is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy người dùng")
    return user


async def get_user_including_deleted(db: AsyncSession, user_id: int) -> User:
    user = await db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy người dùng")
    return user


async def build_detail(db: AsyncSession, user: User) -> AdminUserDetail:
    if user.status != UserStatus.ACTIVE or user.is_deleted or user.deleted_at is not None:
        return AdminUserDetail.model_validate(user).model_copy(update={"project_count": 0, "device_count": 0, "sensor_count": 0, "open_alert_count": 0, "online_device_count": 0, "offline_device_count": 0, "last_telemetry_at": None})
    project_ids = list(
        (await db.scalars(select(Project.id).where(Project.owner_user_id == user.id, existing_project_clause(Project)))).all()
    )
    device_rows = list(
        (
            await db.scalars(
                select(Device).where(
                    Device.project_id.in_(project_ids), Device.is_deleted.is_(False)
                )
            )
        ).all()
    ) if project_ids else []
    device_ids = [device.id for device in device_rows]
    sensor_ids = list(
        (
            await db.scalars(
                select(Sensor.id).where(
                    Sensor.device_id.in_(device_ids), Sensor.is_deleted.is_(False)
                )
            )
        ).all()
    ) if device_ids else []
    open_alert_count = int(
        await db.scalar(
            select(func.count(SensorAlert.id)).where(
                SensorAlert.sensor_id.in_(sensor_ids), SensorAlert.status.in_(ACTIVE_ALERTS)
            )
        ) or 0
    ) if sensor_ids else 0
    last_telemetry_at = await db.scalar(
        select(func.max(TelemetryReading.recorded_at)).where(
            TelemetryReading.sensor_id.in_(sensor_ids)
        )
    ) if sensor_ids else None
    return AdminUserDetail.model_validate(user).model_copy(
        update={
            "project_count": len(project_ids),
            "device_count": len(device_rows),
            "sensor_count": len(sensor_ids),
            "open_alert_count": open_alert_count,
            "online_device_count": sum(d.status == DeviceStatus.ONLINE for d in device_rows),
            "offline_device_count": sum(d.status == DeviceStatus.OFFLINE for d in device_rows),
            "last_telemetry_at": last_telemetry_at,
        }
    )


@router.get("")
async def admin_list_users(
    q: str = Query(default="", max_length=255),
    role: UserRole | None = None,
    status: str | None = None,
    customer_only: bool = False,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_roles(UserRole.ADMIN)),
) -> dict:
    query = select(User)
    keyword = q.strip()
    if keyword:
        pattern = f"%{keyword}%"
        query = query.where(or_(User.full_name.ilike(pattern), User.username.ilike(pattern), User.email.ilike(pattern), User.phone_number.ilike(pattern)))
    if role is not None:
        query = query.where(User.system_role == role)
    if customer_only:
        query = query.where(User.system_role.in_([UserRole.OWNER, UserRole.VIEWER]))
    if status:
        try:
            query = query.where(User.status == UserStatus(status))
        except ValueError as exc:
            raise HTTPException(status_code=422, detail="Trạng thái tài khoản không hợp lệ") from exc
    total = int(await db.scalar(select(func.count()).select_from(query.subquery())) or 0)
    users = list((await db.scalars(query.order_by(User.full_name).offset((page - 1) * page_size).limit(page_size))).all())
    return {"items": [await build_detail(db, user) for user in users], "total": total, "page": page, "page_size": page_size}


@router.post("", response_model=AdminUserDetail, status_code=201)
async def admin_create_user(
    payload: AdminUserCreate, db: AsyncSession = Depends(get_db),
    actor: User = Depends(require_roles(UserRole.ADMIN)),
) -> AdminUserDetail:
    return await build_detail(db, await create_admin_user(db, payload, actor))


@router.get("/{user_id}", response_model=AdminUserDetail)
async def admin_get_user(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_roles(UserRole.ADMIN)),
) -> AdminUserDetail:
    return await build_detail(db, await get_user(db, user_id))


@router.patch("/{user_id}", response_model=AdminUserDetail)
async def admin_patch_user(
    user_id: int,
    payload: UserUpdate,
    db: AsyncSession = Depends(get_db),
    actor: User = Depends(require_roles(UserRole.ADMIN)),
) -> AdminUserDetail:
    user = await update_user(db, await get_user(db, user_id), payload, actor)
    return await build_detail(db, user)


@router.post("/{user_id}/projects", response_model=ProjectRead, status_code=201)
async def admin_create_user_project(
    user_id: int,
    payload: AdminProjectCreate,
    db: AsyncSession = Depends(get_db),
    actor: User = Depends(require_roles(UserRole.ADMIN)),
) -> Project:
    owner = await get_user(db, user_id)
    if owner.system_role != UserRole.OWNER:
        raise HTTPException(status_code=400, detail="Chủ dự án phải có vai trò Owner")
    if owner.status != UserStatus.ACTIVE or owner.is_deleted or owner.deleted_at is not None:
        raise HTTPException(status_code=409, detail="Không thể tạo dự án cho tài khoản không hoạt động")
    if await db.scalar(select(Project.id).where(Project.code == payload.code)):
        raise HTTPException(status_code=409, detail="Mã dự án đã tồn tại")
    project = Project(owner_user_id=user_id, **payload.model_dump())
    db.add(project)
    await db.flush()
    activity = await record_project_activity(db, project_id=project.id, actor=actor, action="PROJECT_CREATED", entity_type="PROJECT", entity_id=project.id, entity_name=project.name, changes={"created": True})
    await db.commit()
    await db.refresh(project)
    await dispatch_project_activity(db, activity_id=activity.id)
    return project


@router.get("/{user_id}/projects", response_model=AdminUserProjectListResponse)
async def admin_user_projects(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_roles(UserRole.ADMIN)),
) -> AdminUserProjectListResponse:
    user = await get_user(db, user_id)
    if user.status != UserStatus.ACTIVE or user.is_deleted or user.deleted_at is not None:
        return AdminUserProjectListResponse(items=[], total=0)

    device_count = (
        select(func.count(Device.id))
        .where(
            Device.project_id == Project.id,
            Device.is_deleted.is_(False),
            Device.deleted_at.is_(None),
        )
        .correlate(Project)
        .scalar_subquery()
    )
    sensor_count = (
        select(func.count(Sensor.id))
        .join(Device, Device.id == Sensor.device_id)
        .where(
            Device.project_id == Project.id,
            Device.is_deleted.is_(False),
            Device.deleted_at.is_(None),
            Sensor.is_deleted.is_(False),
            Sensor.deleted_at.is_(None),
        )
        .correlate(Project)
        .scalar_subquery()
    )
    open_alert_count = (
        select(func.count(SensorAlert.id))
        .join(Sensor, Sensor.id == SensorAlert.sensor_id)
        .join(Device, Device.id == Sensor.device_id)
        .where(
            Device.project_id == Project.id,
            Device.is_deleted.is_(False),
            Device.deleted_at.is_(None),
            Sensor.is_deleted.is_(False),
            Sensor.deleted_at.is_(None),
            Sensor.is_enabled.is_(True),
            Device.is_enabled.is_(True),
            SensorAlert.status.in_(ACTIVE_ALERTS),
        )
        .correlate(Project)
        .scalar_subquery()
    )
    latest_telemetry_at = (
        select(func.max(TelemetryReading.recorded_at))
        .join(Sensor, Sensor.id == TelemetryReading.sensor_id)
        .join(Device, Device.id == Sensor.device_id)
        .where(
            Device.project_id == Project.id,
            Device.is_deleted.is_(False),
            Device.deleted_at.is_(None),
            Sensor.is_deleted.is_(False),
            Sensor.deleted_at.is_(None),
            Sensor.is_enabled.is_(True),
            Device.is_enabled.is_(True),
        )
        .correlate(Project)
        .scalar_subquery()
    )
    rows = (
        await db.execute(
            select(
                Project,
                device_count.label("device_count"),
                sensor_count.label("sensor_count"),
                open_alert_count.label("open_alert_count"),
                latest_telemetry_at.label("latest_telemetry_at"),
            )
            .where(Project.owner_user_id == user_id, existing_project_clause(Project))
            .order_by(Project.name)
        )
    ).all()
    items = [
        AdminUserProjectRead(
            id=project.id,
            name=project.name,
            code=project.code,
            location=project.location,
            status=project.status,
            device_count=int(row_device_count or 0),
            sensor_count=int(row_sensor_count or 0),
            open_alert_count=int(row_open_alert_count or 0),
            latest_telemetry_at=row_latest_telemetry_at,
        )
        for (
            project,
            row_device_count,
            row_sensor_count,
            row_open_alert_count,
            row_latest_telemetry_at,
        ) in rows
    ]
    return AdminUserProjectListResponse(items=items, total=len(items))


@router.get("/{user_id}/devices", response_model=list[DeviceRead])
async def admin_user_devices(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_roles(UserRole.ADMIN)),
) -> list[Device]:
    user = await get_user(db, user_id)
    if user.status != UserStatus.ACTIVE or user.is_deleted or user.deleted_at is not None:
        return []
    return list(
        (
            await db.scalars(
                select(Device)
                .join(Project, Project.id == Device.project_id)
                .where(Project.owner_user_id == user_id, active_project_clause(Project), Device.is_deleted.is_(False))
                .order_by(Project.name, Device.name)
            )
        ).all()
    )


@router.get("/{user_id}/activity")
async def admin_user_activity(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_roles(UserRole.ADMIN)),
) -> list[dict]:
    await get_user(db, user_id)
    logs = list(
        (
            await db.scalars(
                select(AuditLog)
                .where(
                    (AuditLog.user_id == user_id)
                    | ((AuditLog.entity_type == "USER") & (AuditLog.entity_id == user_id))
                )
                .order_by(AuditLog.created_at.desc())
                .limit(100)
            )
        ).all()
    )
    actor_ids = {log.user_id for log in logs}
    actors = {actor.id: actor for actor in (await db.scalars(select(User).where(User.id.in_(actor_ids)))).all()} if actor_ids else {}
    target_ids = {log.entity_id for log in logs if log.entity_type == "USER" and log.entity_id is not None}
    targets = {target.id: target for target in (await db.scalars(select(User).where(User.id.in_(target_ids)))).all()} if target_ids else {}
    return [
        {
            "id": log.id, "action": log.action, "description": log.description,
            "entity_type": log.entity_type, "entity_id": log.entity_id,
            "old_data": log.old_data, "new_data": log.new_data, "created_at": log.created_at,
            "actor_name": actors[log.user_id].full_name if log.user_id in actors else "Người dùng đã xóa",
            "target_name": (
                f"{targets[log.entity_id].full_name} (@{targets[log.entity_id].username})"
                if log.entity_id in targets
                else str((log.new_data or log.old_data or {}).get("display_name") or f"#{log.entity_id}")
            ),
        }
        for log in logs
    ]
