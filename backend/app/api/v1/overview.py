from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_operational_user
from app.db.session import get_db
from app.core.enums import DeviceStatus, SensorStatus
from app.models.device import Device
from app.models.sensor import Sensor
from app.models.user import User
from app.schemas.overview import StatusCount
from app.services.overview_service import get_user_overview

router = APIRouter(prefix="/overview", tags=["Overview"])


async def count_devices(db: AsyncSession) -> StatusCount:
    rows = (
        await db.execute(
            select(Device.status, func.count(Device.id))
            .where(Device.is_deleted.is_(False))
            .group_by(Device.status)
        )
    ).all()
    counts = {status.value: count for status, count in rows}
    return StatusCount(
        total=sum(counts.values()),
        online=counts.get(DeviceStatus.ONLINE.value, 0),
        offline=counts.get(DeviceStatus.OFFLINE.value, 0),
        waiting=counts.get(DeviceStatus.WAITING_CONNECTION.value, 0),
        disabled=counts.get(DeviceStatus.DISABLED.value, 0),
    )


async def count_sensors(db: AsyncSession) -> StatusCount:
    rows = (
        await db.execute(
            select(Sensor.status, func.count(Sensor.id))
            .where(Sensor.is_deleted.is_(False))
            .group_by(Sensor.status)
        )
    ).all()
    counts = {status.value: count for status, count in rows}
    return StatusCount(
        total=sum(counts.values()),
        online=counts.get(SensorStatus.ONLINE.value, 0),
        offline=counts.get(SensorStatus.OFFLINE.value, 0),
        waiting=counts.get(SensorStatus.WAITING_CONNECTION.value, 0),
        disabled=counts.get(SensorStatus.DISABLED.value, 0),
    )


@router.get("")
async def overview(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_operational_user),
) -> dict:
    # Legacy alias; cùng policy và payload với /me/overview để không còn rò rỉ dữ liệu.
    return await get_user_overview(db, user)
