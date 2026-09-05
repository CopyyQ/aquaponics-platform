from datetime import UTC, datetime, timedelta

from sqlalchemy import select

from app.core.config import settings
from app.core.enums import (
    AlertSeverity,
    AlertStatus,
    AlertType,
    DeviceStatus,
    ProjectStatus,
    SensorStatus,
    UserStatus,
)
from app.db.session import async_session_factory
from app.models.alert import SensorAlert
from app.models.device import Device
from app.models.project import Project
from app.models.sensor import Sensor
from app.models.user import User
from app.services.alert_service import get_active_alert
from app.services.project_notification_service import (
    dispatch_device_connectivity_transition,
)


async def scan_offline_state() -> None:
    now = datetime.now(UTC)
    device_cutoff = now - timedelta(seconds=settings.device_offline_seconds)
    sensor_cutoff = now - timedelta(seconds=settings.sensor_offline_seconds)
    async with async_session_factory() as db:
        disconnected_device_ids: list[int] = []
        operational_scope = (
            Project.status == ProjectStatus.ACTIVE,
            Project.is_deleted.is_(False),
            Project.deleted_at.is_(None),
            User.status == UserStatus.ACTIVE,
            User.is_deleted.is_(False),
            User.deleted_at.is_(None),
        )
        devices = list(
            (
                await db.scalars(
                    select(Device)
                    .join(Project, Device.project_id == Project.id)
                    .join(User, Project.owner_user_id == User.id)
                    .where(
                        Device.is_deleted.is_(False),
                        Device.deleted_at.is_(None),
                        Device.is_enabled.is_(True),
                        Device.status == DeviceStatus.ONLINE,
                        Device.last_seen_at < device_cutoff,
                        *operational_scope,
                    )
                )
            ).all()
        )
        for device in devices:
            device.status = DeviceStatus.OFFLINE
            device.disconnected_at = now
            disconnected_device_ids.append(device.id)

        sensor_rows = list(
            (
                await db.execute(
                    select(Sensor, Device)
                    .join(Device, Sensor.device_id == Device.id)
                    .join(Project, Device.project_id == Project.id)
                    .join(User, Project.owner_user_id == User.id)
                    .where(
                        Sensor.is_deleted.is_(False),
                        Sensor.deleted_at.is_(None),
                        Sensor.is_enabled.is_(True),
                        Sensor.status.not_in([SensorStatus.WAITING_CONNECTION]),
                        Sensor.last_seen_at < sensor_cutoff,
                        Device.is_enabled.is_(True),
                        Device.is_deleted.is_(False),
                        Device.deleted_at.is_(None),
                        *operational_scope,
                    )
                )
            ).all()
        )
        for sensor, parent_device in sensor_rows:
            sensor.status = SensorStatus.OFFLINE
            if parent_device.status == DeviceStatus.OFFLINE:
                # Parent transition is the operator-level incident. Keep child
                # Sensor state visible but suppress N duplicate NO_DATA alerts.
                continue
            active_alert = await get_active_alert(db, sensor.id, AlertType.SENSOR_OFFLINE)
            if active_alert is None:
                alert = SensorAlert(
                        sensor_id=sensor.id,
                        alert_type=AlertType.SENSOR_OFFLINE,
                        severity=AlertSeverity.CRITICAL,
                        status=AlertStatus.OPEN,
                        message=f"{sensor.name} đã ngừng gửi dữ liệu",
                        started_at=now,
                    )
                db.add(alert)
                await db.flush()
            elif not active_alert.condition_active:
                active_alert.condition_active = True
                active_alert.normalized_at = None
        await db.commit()
        for device_id in disconnected_device_ids:
            await dispatch_device_connectivity_transition(
                db,
                device_id=device_id,
                transition="DISCONNECTED",
                disconnected_at=now,
                occurred_at=now,
            )
