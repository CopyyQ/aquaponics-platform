from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import AlertSeverity, AlertStatus, AlertType, DeviceStatus, UserRole
from app.models.alert import SensorAlert
from app.models.device import Device
from app.models.project import Project
from app.models.sensor import Sensor
from app.models.telemetry import TelemetryReading
from app.models.user import User
from app.services.access_service import accessible_project_clause, active_project_clause

ACTIVE_ALERTS = [AlertStatus.PENDING, AlertStatus.OPEN, AlertStatus.ACKNOWLEDGED]
THRESHOLD_ALERTS = [AlertType.BELOW_LOWER_THRESHOLD, AlertType.ABOVE_UPPER_THRESHOLD]


def health_for(score: int) -> str:
    if score >= 70:
        return "CRITICAL"
    if score >= 35:
        return "WARNING"
    if score > 0:
        return "ATTENTION"
    return "HEALTHY"


async def build_project_health_rows(db: AsyncSession, actor: User) -> list[dict]:
    projects = list(
        (
            await db.scalars(
                select(Project)
                .where(active_project_clause(Project), accessible_project_clause(actor))
                .order_by(Project.name)
            )
        ).all()
    )
    project_ids = {project.id for project in projects}
    if not project_ids:
        return []

    owners = {
        owner.id: owner
        for owner in (
            await db.scalars(select(User).where(User.id.in_({p.owner_user_id for p in projects})))
        ).all()
    }
    devices = list(
        (
            await db.scalars(
                select(Device).where(
                    Device.project_id.in_(project_ids),
                    Device.is_deleted.is_(False),
                    Device.deleted_at.is_(None),
                    Device.is_enabled.is_(True),
                )
            )
        ).all()
    )
    device_ids = {device.id for device in devices}
    sensors = (
        list(
            (
                await db.scalars(
                    select(Sensor).where(
                        Sensor.device_id.in_(device_ids),
                        Sensor.is_deleted.is_(False),
                        Sensor.deleted_at.is_(None),
                        Sensor.is_enabled.is_(True),
                    )
                )
            ).all()
        )
        if device_ids
        else []
    )
    sensor_ids = {sensor.id for sensor in sensors}
    alerts = (
        list(
            (
                await db.scalars(
                    select(SensorAlert).where(
                        SensorAlert.sensor_id.in_(sensor_ids),
                        SensorAlert.status.in_(ACTIVE_ALERTS),
                    )
                )
            ).all()
        )
        if sensor_ids
        else []
    )
    latest_by_sensor = (
        dict(
            (
                await db.execute(
                    select(TelemetryReading.sensor_id, func.max(TelemetryReading.recorded_at))
                    .where(TelemetryReading.sensor_id.in_(sensor_ids))
                    .group_by(TelemetryReading.sensor_id)
                )
            ).all()
        )
        if sensor_ids
        else {}
    )

    now = datetime.now(UTC)
    rows: list[dict] = []
    for project in projects:
        project_devices = [device for device in devices if device.project_id == project.id]
        project_device_ids = {device.id for device in project_devices}
        project_sensors = [sensor for sensor in sensors if sensor.device_id in project_device_ids]
        project_sensor_ids = {sensor.id for sensor in project_sensors}
        project_alerts = [alert for alert in alerts if alert.sensor_id in project_sensor_ids]
        critical = sum(alert.severity == AlertSeverity.CRITICAL for alert in project_alerts)
        warnings = sum(alert.severity == AlertSeverity.WARNING for alert in project_alerts)
        offline_devices = sum(device.status == DeviceStatus.OFFLINE for device in project_devices)
        offline_sensors = sum(sensor.status.value == "OFFLINE" for sensor in project_sensors)
        out_of_range_sensors = len(
            {alert.sensor_id for alert in project_alerts if alert.alert_type in THRESHOLD_ALERTS}
        )
        latest = max(
            (latest_by_sensor.get(sensor.id) for sensor in project_sensors if latest_by_sensor.get(sensor.id)),
            default=None,
        )
        stale = latest is None or latest < now - timedelta(minutes=15)
        risk_score = min(
            100,
            critical * 30
            + warnings * 12
            + offline_devices * 15
            + offline_sensors * 6
            + out_of_range_sensors * 8
            + (10 if stale and project_sensors else 0),
        )
        owner = owners.get(project.owner_user_id)
        last_event = max(
            [alert.started_at for alert in project_alerts]
            + ([latest] if latest else [])
            + [project.updated_at]
        )
        access_role = (
            UserRole.ADMIN.value
            if actor.system_role == UserRole.ADMIN
            else UserRole.OWNER.value
            if project.owner_user_id == actor.id
            else UserRole.VIEWER.value
        )
        rows.append(
            {
                "id": project.id,
                "code": project.code,
                "name": project.name,
                "location": project.location,
                "project_status": project.status,
                "owner_user_id": project.owner_user_id,
                "customer_name": owner.full_name if owner else "Không xác định",
                "customer_email": owner.email if owner else None,
                "access_role": access_role,
                "risk_score": risk_score,
                "health_status": health_for(risk_score),
                "critical_alert_count": critical,
                "warning_alert_count": warnings,
                "open_alert_count": len(project_alerts),
                "offline_device_count": offline_devices,
                "online_device_count": sum(
                    device.status == DeviceStatus.ONLINE for device in project_devices
                ),
                "device_count": len(project_devices),
                "offline_sensor_count": offline_sensors,
                "online_sensor_count": sum(sensor.status.value == "ONLINE" for sensor in project_sensors),
                "out_of_range_sensor_count": out_of_range_sensors,
                # Backward-compatible field used by the Admin board.
                "abnormal_sensor_count": offline_sensors + out_of_range_sensors,
                "sensor_count": len(project_sensors),
                "last_telemetry_at": latest,
                "last_event_at": last_event,
                "stale": stale,
            }
        )
    return rows
