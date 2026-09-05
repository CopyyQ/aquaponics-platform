from datetime import UTC, datetime

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.enums import UserStatus
from app.models.device import Device
from app.models.project import Project
from app.models.sensor import Sensor
from app.models.sensor_model import SensorModel
from app.models.user import User
from app.schemas.project import (
    DeviceConfigDevice,
    DeviceConfigMqtt,
    DeviceConfigOwner,
    DeviceConfigProject,
    DeviceConfigSensor,
    DeviceConfigSummary,
    DeviceConfigTopics,
    ProjectDeviceConfig,
)


async def export_project_device_config(
    db: AsyncSession, *, project_id: int
) -> ProjectDeviceConfig:
    context = (
        await db.execute(
            select(Project, User)
            .join(User, User.id == Project.owner_user_id)
            .where(
                Project.id == project_id,
                Project.is_deleted.is_(False),
                Project.deleted_at.is_(None),
            )
        )
    ).first()
    if context is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy dự án")
    project, owner = context
    if owner.status != UserStatus.ACTIVE or owner.is_deleted or owner.deleted_at is not None:
        raise HTTPException(
            status_code=409,
            detail={
                "code": "PROJECT_OWNER_NOT_ACTIVE",
                "detail": "Chủ dự án không ở trạng thái hoạt động.",
            },
        )
    public_host = settings.mqtt_public_host.strip()
    if public_host.lower() in {"localhost", "127.0.0.1", "::1", "mqtt", "mosquitto"}:
        raise HTTPException(
            status_code=500,
            detail={
                "code": "MQTT_PUBLIC_HOST_INVALID",
                "detail": "MQTT_PUBLIC_HOST phải là địa chỉ mà thiết bị trong mạng LAN truy cập được.",
            },
        )
    devices = list(
        (
            await db.scalars(
                select(Device)
                .where(
                    Device.project_id == project_id,
                    Device.is_deleted.is_(False),
                    Device.deleted_at.is_(None),
                )
                .order_by(Device.id)
            )
        ).all()
    )
    device_ids = [device.id for device in devices]
    sensor_rows = (
        list(
            (
                await db.execute(
                    select(Sensor, SensorModel.unit)
                    .join(SensorModel, SensorModel.id == Sensor.sensor_model_id)
                    .where(
                        Sensor.device_id.in_(device_ids),
                        Sensor.is_deleted.is_(False),
                        Sensor.deleted_at.is_(None),
                    )
                    .order_by(Sensor.device_id, Sensor.id)
                )
            ).all()
        )
        if device_ids
        else []
    )
    sensors_by_device: dict[int, list[DeviceConfigSensor]] = {
        device_id: [] for device_id in device_ids
    }
    for sensor, unit in sensor_rows:
        sensors_by_device[sensor.device_id].append(
            DeviceConfigSensor(
                id=sensor.id,
                sensor_code=sensor.code,
                name=sensor.name,
                unit=unit,
                is_enabled=sensor.is_enabled,
                status=sensor.status,
                lower_threshold=sensor.lower_threshold,
                upper_threshold=sensor.upper_threshold,
            )
        )
    exported_devices = [
        DeviceConfigDevice(
            id=device.id,
            code=device.code,
            name=device.name,
            is_enabled=device.is_enabled,
            status=device.status,
            location=device.location,
            topics=DeviceConfigTopics(
                telemetry=f"aquaponics/{device.code}/telemetry",
                status=f"aquaponics/{device.code}/status",
            ),
            sensors=sensors_by_device[device.id],
        )
        for device in devices
    ]
    exported_sensors = [sensor for device in exported_devices for sensor in device.sensors]
    return ProjectDeviceConfig(
        exported_at=datetime.now(UTC),
        project=DeviceConfigProject(
            id=project.id,
            code=project.code,
            name=project.name,
            owner=DeviceConfigOwner(id=owner.id, full_name=owner.full_name),
        ),
        mqtt=DeviceConfigMqtt(
            host=public_host,
            port=settings.mqtt_public_port,
            authentication=settings.mqtt_authentication,
            tls=settings.mqtt_tls,
        ),
        devices=exported_devices,
        summary=DeviceConfigSummary(
            device_count=len(exported_devices),
            enabled_device_count=sum(device.is_enabled for device in exported_devices),
            disabled_device_count=sum(not device.is_enabled for device in exported_devices),
            sensor_count=len(exported_sensors),
            enabled_sensor_count=sum(sensor.is_enabled for sensor in exported_sensors),
            disabled_sensor_count=sum(not sensor.is_enabled for sensor in exported_sensors),
        ),
    )
