from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_operational_user, require_roles
from app.db.session import get_db
from app.core.enums import AlertStatus, UserRole, UserStatus
from app.models.alert import SensorAlert
from app.models.device import Device
from app.models.project import Project
from app.models.sensor import Sensor
from app.models.telemetry import TelemetryReading
from app.models.user import User
from app.schemas.device import DeviceRead
from app.services.access_service import active_project_clause, accessible_device_clause
from app.services.overview_service import get_user_overview

router = APIRouter(tags=["Platform overview"])
ACTIVE_ALERTS = [AlertStatus.PENDING, AlertStatus.OPEN, AlertStatus.ACKNOWLEDGED]


@router.get("/me/devices", response_model=list[DeviceRead])
async def my_devices(
    db: AsyncSession = Depends(get_db), actor: User = Depends(get_current_operational_user)
) -> list[Device]:
    return list(
        (
            await db.scalars(
                select(Device)
                .where(Device.is_deleted.is_(False), Device.is_enabled.is_(True), accessible_device_clause(actor))
                .order_by(Device.name)
            )
        ).all()
    )


@router.get("/me/overview")
async def my_overview(
    db: AsyncSession = Depends(get_db), actor: User = Depends(get_current_operational_user)
) -> dict:
    return await get_user_overview(db, actor)


@router.get("/admin/overview")
async def admin_overview(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_roles(UserRole.ADMIN)),
) -> dict:
    projects = list((await db.scalars(select(Project).where(active_project_clause(Project)))).all())
    active_project_ids = {project.id for project in projects}
    devices = list((await db.scalars(select(Device).where(Device.is_deleted.is_(False), Device.deleted_at.is_(None), Device.is_enabled.is_(True), Device.project_id.in_(active_project_ids)))).all()) if active_project_ids else []
    project_owners = {project.id: project.owner_user_id for project in projects}
    sensors = list(
        (await db.scalars(select(Sensor).where(Sensor.is_deleted.is_(False), Sensor.deleted_at.is_(None), Sensor.is_enabled.is_(True), Sensor.device_id.in_([d.id for d in devices])))).all()
    )
    customer_users = list(
        (
            await db.scalars(
                select(User)
                .where(
                    User.system_role.in_([UserRole.OWNER, UserRole.VIEWER]),
                    User.status == UserStatus.ACTIVE,
                    User.is_deleted.is_(False),
                    User.deleted_at.is_(None),
                )
                .order_by(User.full_name)
            )
        ).all()
    )
    open_alerts = int(
        await db.scalar(
            select(func.count(SensorAlert.id)).join(Sensor, Sensor.id == SensorAlert.sensor_id).join(Device, Device.id == Sensor.device_id).where(SensorAlert.status.in_(ACTIVE_ALERTS), Device.id.in_([d.id for d in devices]))
        ) or 0
    )
    alert_distribution = {
        str(kind): int(count)
        for kind, count in (
            await db.execute(
                select(SensorAlert.alert_type, func.count(SensorAlert.id))
                .join(Sensor, Sensor.id == SensorAlert.sensor_id).join(Device, Device.id == Sensor.device_id)
                .where(SensorAlert.status.in_(ACTIVE_ALERTS), Device.id.in_([d.id for d in devices]))
                .group_by(SensorAlert.alert_type)
            )
        ).all()
    }
    customer_health = []
    for user in customer_users:
        owned = [
            device for device in devices if project_owners.get(device.project_id) == user.id
        ]
        owned_ids = [device.id for device in owned]
        user_sensors = [sensor for sensor in sensors if sensor.device_id in owned_ids]
        sensor_ids = [sensor.id for sensor in user_sensors]
        user_alerts = int(
            await db.scalar(
                select(func.count(SensorAlert.id)).where(
                    SensorAlert.sensor_id.in_(sensor_ids),
                    SensorAlert.status.in_(ACTIVE_ALERTS),
                )
            ) or 0
        ) if sensor_ids else 0
        online = sum(device.status.value == "ONLINE" for device in owned)
        ratio = round((online / len(owned)) * 100, 1) if owned else 0
        status = (
            "Không có thiết bị"
            if not owned
            else "Nghiêm trọng"
            if user_alerts or any(d.status.value == "OFFLINE" for d in owned)
            else "Cần chú ý"
            if online < len(owned)
            else "Tốt"
        )
        customer_health.append(
            {
                "user_id": user.id,
                "full_name": user.full_name,
                "role": user.system_role,
                "device_count": len(owned),
                "sensor_count": len(user_sensors),
                "online_devices": online,
                "online_ratio": ratio,
                "open_alerts": user_alerts,
                "last_received_at": max(
                    (d.last_seen_at for d in owned if d.last_seen_at), default=None
                ),
                "health_status": status,
            }
        )
    critical = list(
        (
            await db.execute(
                select(SensorAlert, Sensor, Device)
                .join(Sensor, SensorAlert.sensor_id == Sensor.id)
                .join(Device, Sensor.device_id == Device.id)
                .where(SensorAlert.status.in_(ACTIVE_ALERTS), Sensor.id.in_([s.id for s in sensors]), Device.id.in_([d.id for d in devices]))
                .order_by(SensorAlert.severity.desc(), SensorAlert.started_at)
                .limit(10)
            )
        ).all()
    )
    latest_received = await db.scalar(select(func.max(TelemetryReading.received_at)).where(TelemetryReading.sensor_id.in_([s.id for s in sensors]))) if sensors else None
    return {
        "summary": {
            "total_customers": len(customer_users),
            "total_devices": len(devices),
            "assigned_devices": len(devices),
            "unassigned_devices": 0,
            "online_devices": sum(d.status.value == "ONLINE" for d in devices),
            "offline_devices": sum(d.status.value == "OFFLINE" for d in devices),
            "waiting_devices": sum(d.status.value == "WAITING_CONNECTION" for d in devices),
            "disabled_devices": sum(d.status.value == "DISABLED" for d in devices),
            "total_sensors": len(sensors),
            "online_sensors": sum(s.status.value == "ONLINE" for s in sensors),
            "offline_sensors": sum(s.status.value == "OFFLINE" for s in sensors),
            "open_alerts": open_alerts,
            "latest_received_at": latest_received,
        },
        "alert_distribution": alert_distribution,
        "critical_issues": [
            {
                "alert_id": alert.id,
                "project_id": device.project_id,
                "device_id": device.id,
                "owner_user_id": project_owners.get(device.project_id),
                "sensor_id": sensor.id,
                "message": alert.message,
                "severity": alert.severity,
                "started_at": alert.started_at,
            }
            for alert, sensor, device in critical
        ],
        "customers": customer_health,
    }


@router.get("/admin/users/{user_id}/overview")
async def admin_user_overview(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_roles(UserRole.ADMIN)),
) -> dict:
    user = await db.scalar(select(User).where(User.id == user_id))
    if user is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy người dùng")
    user_summary = {"id": user.id, "full_name": user.full_name, "email": user.email, "role": user.system_role, "status": user.status}
    if user.status.value != "ACTIVE" or user.is_deleted or user.deleted_at is not None:
        return {"user": user_summary, "summary": {"total_devices": 0, "total_sensors": 0, "open_alerts": 0}, "devices": [], "account_inactive": True}
    return {"user": user_summary, **await get_user_overview(db, user)}
