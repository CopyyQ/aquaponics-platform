from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import UserRole
from app.models.device import Device
from app.models.project import Project
from app.models.sensor import Sensor
from app.models.user import User
from app.queries.project_queries import (
    accessible_device_clause,
    accessible_project_clause,
    active_owner_clause,
    active_project_clause,
    existing_project_clause,
    scope_devices,
)


async def require_project_access(
    db: AsyncSession, project_id: int, user: User, *, manage: bool = False
) -> Project:
    lifecycle_clause = (
        active_project_clause(Project)
        if user.system_role != UserRole.ADMIN or manage
        else existing_project_clause(Project)
    )
    query = select(Project).where(Project.id == project_id, lifecycle_clause)
    if user.system_role != UserRole.ADMIN:
        if manage and user.system_role != UserRole.OWNER:
            raise HTTPException(status_code=403, detail="Không đủ quyền quản lý dự án")
        query = query.where(accessible_project_clause(user))
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
    project_clause = (
        existing_project_clause(Project)
        if user.system_role == UserRole.ADMIN and not manage
        else active_project_clause(Project)
    )
    query = select(Device).join(Project, Project.id == Device.project_id).where(
        Device.id == device_id,
        Device.is_deleted.is_(False),
        Device.deleted_at.is_(None),
        project_clause,
    )
    if not allow_disabled:
        query = query.where(Device.is_enabled.is_(True))
    if user.system_role != UserRole.ADMIN:
        if manage and user.system_role != UserRole.OWNER:
            raise HTTPException(status_code=403, detail="Không đủ quyền quản lý thiết bị")
        query = query.where(accessible_device_clause(user))
    device = await db.scalar(query)
    if device is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy thiết bị")
    return device


async def require_sensor_access(
    db: AsyncSession, sensor_id: int, user: User, *, manage: bool = False, allow_disabled: bool = False
) -> Sensor:
    project_clause = (
        existing_project_clause(Project)
        if user.system_role == UserRole.ADMIN and not manage
        else active_project_clause(Project)
    )
    query = (
        select(Sensor)
        .join(Device, Sensor.device_id == Device.id)
        .join(Project, Project.id == Device.project_id)
        .where(
            Sensor.id == sensor_id,
            Sensor.is_deleted.is_(False),
            Sensor.deleted_at.is_(None),
            Device.is_deleted.is_(False),
            Device.deleted_at.is_(None),
            project_clause,
        )
    )
    if not allow_disabled:
        query = query.where(Device.is_enabled.is_(True), Sensor.is_enabled.is_(True))
    if user.system_role != UserRole.ADMIN:
        if manage and user.system_role != UserRole.OWNER:
            raise HTTPException(status_code=403, detail="Không đủ quyền chỉnh sửa cảm biến")
        query = query.where(accessible_device_clause(user))
    sensor = await db.scalar(query)
    if sensor is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy cảm biến")
    return sensor
