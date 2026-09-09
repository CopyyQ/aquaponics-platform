from fastapi import HTTPException
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.device import Device
from app.models.project import Project
from app.models.sensor import Sensor
from app.models.user import User
from app.core.enums import ProjectStatus
from app.services.permission_service import has_permission


async def require_project_access(
    db: AsyncSession, project_id: int, user: User, *, manage: bool = False
) -> Project:
    global_scope = await has_permission(db, user, "aquaponics_systems.manage_all" if manage else "aquaponics_systems.read_all")
    query = select(Project).where(Project.id == project_id, Project.is_deleted.is_(False))
    if not global_scope:
        query = query.where(Project.status == ProjectStatus.ACTIVE, or_(Project.owner_user_id == user.id, Project.members.any(user_id=user.id)))
    project = await db.scalar(query)
    if project is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy dự án")
    return project


async def get_admin_project_for_lifecycle(db: AsyncSession, project_id: int) -> Project:
    project = await db.scalar(
        select(Project).where(
            Project.id == project_id,
            Project.is_deleted.is_(False),
            Project.deleted_at.is_(None),
        )
    )
    if project is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy dự án")
    return project


async def require_device_access(
    db: AsyncSession, device_id: int, user: User, *, manage: bool = False, allow_disabled: bool = False
) -> Device:
    device = await db.scalar(select(Device).where(Device.id == device_id, Device.is_deleted.is_(False)))
    if device is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy thiết bị")
    await require_project_access(db, device.project_id, user, manage=manage)
    if not allow_disabled and not device.is_enabled:
        raise HTTPException(status_code=404, detail="Không tìm thấy thiết bị")
    return device


async def require_sensor_access(
    db: AsyncSession, sensor_id: int, user: User, *, manage: bool = False, allow_disabled: bool = False
) -> Sensor:
    sensor = await db.scalar(select(Sensor).where(Sensor.id == sensor_id, Sensor.is_deleted.is_(False)))
    if sensor is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy cảm biến")
    await require_device_access(db, sensor.device_id, user, manage=manage, allow_disabled=allow_disabled)
    if not allow_disabled and not sensor.is_enabled:
        raise HTTPException(status_code=404, detail="Không tìm thấy cảm biến")
    return sensor
