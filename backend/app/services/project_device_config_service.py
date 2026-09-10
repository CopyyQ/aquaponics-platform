from datetime import UTC, datetime

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.enums import UserStatus
from app.models.device import Device
from app.models.actuator import Actuator
from app.models.actuator_model import ActuatorModel
from app.models.project import Project
from app.models.sensor import Sensor
from app.models.sensor_model import SensorModel
from app.models.user import User
from app.schemas.project import (
    DeviceConfigDevice,
    DeviceConfigActuator,
    DeviceConfigMqtt,
    DeviceConfigAquaponicsSystem,
    DeviceConfigSensor,
    DeviceConfigTopics,
    AquaponicsSystemMqttConfigExport,
)


async def export_project_device_config(
    db: AsyncSession, *, project_id: int
) -> AquaponicsSystemMqttConfigExport:
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
    actuator_rows = list((await db.execute(select(Actuator, ActuatorModel.code).join(ActuatorModel, ActuatorModel.id == Actuator.actuator_model_id, isouter=True).where(Actuator.device_id.in_(device_ids), Actuator.is_deleted.is_(False), Actuator.removed_at.is_(None)).order_by(Actuator.device_id, Actuator.id))).all()) if device_ids else []
    actuators_by_device = {device_id: [] for device_id in device_ids}
    for actuator, model_code in actuator_rows:
        actuators_by_device[actuator.device_id].append(DeviceConfigActuator(id=actuator.public_id, code=actuator.code, name=actuator.name, actuator_model_code=model_code, is_enabled=actuator.is_enabled))
    sensor_rows = (
        list(
            (
                await db.execute(
                    select(Sensor, SensorModel.code, SensorModel.unit)
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
    for sensor, sensor_model_code, unit in sensor_rows:
        sensors_by_device[sensor.device_id].append(
            DeviceConfigSensor(
                id=sensor.public_id,
                sensor_code=sensor.code,
                sensor_model_code=sensor_model_code,
                name=sensor.name,
                unit=unit,
                is_enabled=sensor.is_enabled,
                status=sensor.status,
            )
        )
    exported_devices = [
        DeviceConfigDevice(
            id=device.public_id,
            code=device.code,
            name=device.name,
            is_enabled=device.is_enabled,
            status=device.status,
            location=device.location,
            topics=DeviceConfigTopics(
                telemetry=f"aquaponics/{device.code}/telemetry",
                status=f"aquaponics/{device.code}/status",
                command=f"aquaponics/{device.code}/command",
            ),
            sensors=sensors_by_device[device.id],
            actuators=actuators_by_device[device.id],
        )
        for device in devices
    ]
    return AquaponicsSystemMqttConfigExport(
        exported_at=datetime.now(UTC),
        aquaponics_system=DeviceConfigAquaponicsSystem(
            id=project.public_id,
            code=project.code,
            name=project.name,
        ),
        mqtt=DeviceConfigMqtt(
            host=public_host,
            port=settings.mqtt_public_port,
            authentication=settings.mqtt_authentication,
            tls=settings.mqtt_tls,
        ),
        devices=exported_devices,
    )
