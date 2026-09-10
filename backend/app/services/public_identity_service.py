from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.actuator import Actuator
from app.models.device import Device
from app.models.project import Project
from app.models.sensor import Sensor
from app.models.user import User


class PublicIdentityNotFoundError(Exception):
    pass


async def get_user_by_public_id(db: AsyncSession, public_id: UUID, *, include_deleted: bool = False) -> User:
    query = select(User).where(User.public_id == public_id)
    if not include_deleted:
        query = query.where(User.is_deleted.is_(False))
    row = await db.scalar(query)
    if row is None:
        raise PublicIdentityNotFoundError("Không tìm thấy người dùng")
    return row


async def get_system_by_public_id(db: AsyncSession, public_id: UUID) -> Project:
    row = await db.scalar(select(Project).where(Project.public_id == public_id, Project.is_deleted.is_(False)))
    if row is None:
        raise PublicIdentityNotFoundError("Không tìm thấy Hệ thống Aquaponics")
    return row


async def get_device_by_public_id(db: AsyncSession, system: Project, public_id: UUID) -> Device:
    row = await db.scalar(select(Device).where(
        Device.public_id == public_id, Device.project_id == system.id, Device.is_deleted.is_(False)
    ))
    if row is None:
        raise PublicIdentityNotFoundError("Không tìm thấy Device trong Hệ thống Aquaponics")
    return row


async def get_sensor_by_public_id(db: AsyncSession, device: Device, public_id: UUID) -> Sensor:
    row = await db.scalar(select(Sensor).where(
        Sensor.public_id == public_id, Sensor.device_id == device.id, Sensor.is_deleted.is_(False)
    ))
    if row is None:
        raise PublicIdentityNotFoundError("Không tìm thấy Sensor trong Device")
    return row


async def get_actuator_by_public_id(db: AsyncSession, device: Device, public_id: UUID) -> Actuator:
    row = await db.scalar(select(Actuator).where(
        Actuator.public_id == public_id, Actuator.device_id == device.id,
        Actuator.is_deleted.is_(False), Actuator.removed_at.is_(None),
    ))
    if row is None:
        raise PublicIdentityNotFoundError("Không tìm thấy Actuator trong Device")
    return row
