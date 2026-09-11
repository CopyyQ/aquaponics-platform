from datetime import UTC, datetime
import hashlib
import json
import re

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.enums import DeviceStatus, ProjectStatus, UserStatus
from app.models.actuator import Actuator
from app.models.actuator_model import ActuatorModel
from app.models.device import Device
from app.models.device_template import DeviceTemplate, DeviceTemplateSensor
from app.models.project import Project
from app.models.sensor import Sensor
from app.models.sensor_model import SensorModel
from app.models.user import User

_UNSAFE_FILENAME = re.compile(r"[^A-Za-z0-9_-]+")


def _device_topic(configured_topic: str, device_code: str, suffix: str) -> str:
    if "{device_code}" in configured_topic:
        return configured_topic.format(device_code=device_code)
    if "+" in configured_topic:
        return configured_topic.replace("+", device_code, 1)
    return f"aquaponics/{device_code}/{suffix}"


def mqtt_config_filename(project_code: str, device_code: str) -> str:
    safe_project = _UNSAFE_FILENAME.sub("-", project_code).strip("-_")
    safe_device = _UNSAFE_FILENAME.sub("-", device_code).strip("-_")
    return f"{safe_project}-{safe_device}-mqtt-config.json"


async def build_mqtt_connection_config(
    db: AsyncSession,
    *,
    project_id: int,
    device_id: int,
) -> tuple[dict[str, object], Project, Device]:
    context = (
        await db.execute(
            select(Project, Device, User)
            .join(Device, Device.project_id == Project.id)
            .join(User, User.id == Project.owner_user_id)
            .where(
                Project.id == project_id,
                Project.is_deleted.is_(False),
                Project.deleted_at.is_(None),
                Device.id == device_id,
                Device.is_deleted.is_(False),
                Device.deleted_at.is_(None),
            )
        )
    ).first()
    if context is None:
        raise HTTPException(
            status_code=404,
            detail="Không tìm thấy thiết bị trong dự án",
        )
    project, device, owner = context
    if (
        project.status != ProjectStatus.ACTIVE
    ):
        raise HTTPException(
            status_code=409,
            detail={
                "code": "PROJECT_INACTIVE",
                "detail": "Dự án hoặc thiết bị không hoạt động.",
            },
        )
    if (
        owner.status != UserStatus.ACTIVE
        or owner.is_deleted
        or owner.deleted_at is not None
    ):
        raise HTTPException(
            status_code=409,
            detail={
                "code": "PROJECT_OWNER_INACTIVE",
                "detail": "Tài khoản chủ dự án không hoạt động.",
            },
        )

    sensor_rows = list(
        (
            await db.execute(
                select(Sensor, SensorModel)
                .join(SensorModel, SensorModel.id == Sensor.sensor_model_id)
                .where(
                    Sensor.device_id == device.id,
                    Sensor.is_enabled.is_(True),
                    Sensor.is_deleted.is_(False),
                    Sensor.deleted_at.is_(None),
                    SensorModel.is_deleted.is_(False),
                )
                .order_by(Sensor.name, Sensor.id)
            )
        ).all()
    )
    template = (
        await db.scalar(
            select(DeviceTemplate)
            .where(DeviceTemplate.id == device.device_template_id)
        )
        if device.device_template_id is not None
        else None
    )
    required_model_ids = set()
    if template is not None:
        required_model_ids = set(
            (
                await db.scalars(
                    select(DeviceTemplateSensor.sensor_model_id).where(
                        DeviceTemplateSensor.device_template_id == template.id,
                        DeviceTemplateSensor.is_required.is_(True),
                    )
                )
            ).all()
        )
    actuator_rows = list(
        (
            await db.execute(
                select(Actuator, ActuatorModel)
                .join(
                    ActuatorModel,
                    ActuatorModel.id == Actuator.actuator_model_id,
                )
                .where(
                    Actuator.device_id == device.id,
                    Actuator.is_enabled.is_(True),
                    Actuator.removed_at.is_(None),
                    Actuator.is_deleted.is_(False),
                    Actuator.deleted_at.is_(None),
                    ActuatorModel.is_deleted.is_(False),
                )
                .order_by(Actuator.name, Actuator.id)
            )
        ).all()
    )
    telemetry_topic = f"aquaponics/{device.code}/telemetry"
    status_topic = f"aquaponics/{device.code}/status"
    command_topic = _device_topic(
        settings.mqtt_command_topic,
        device.code,
        "commands",
    )
    command_ack_topic = _device_topic(
        settings.mqtt_ack_topic,
        device.code,
        "command-ack",
    )
    generated_at = datetime.now(UTC).isoformat().replace("+00:00", "Z")
    sensors = [
        {
            "sensor_code": sensor.code,
            "sensor_model_code": model.code,
            "code": sensor.code,
            "model_code": model.code,
            "name": sensor.name,
            "data_type": model.value_type,
            "value_type": model.value_type,
            "unit": model.unit,
            "measurement_semantics": model.measurement_semantics,
            "location": sensor.installation_location,
            "is_enabled": True,
            "enabled": True,
            "required": model.id in required_model_ids,
        }
        for sensor, model in sensor_rows
    ]
    actuators = [
        {
            "id": actuator.id,
            "actuator_code": actuator.code,
            "actuator_model_code": model.code,
            "name": actuator.name,
            "data_type": model.data_type,
            "state_encoding": {"off": False, "on": True},
            "default_state": model.default_state,
            "location": actuator.location,
            "is_enabled": True,
            "electrical": {
                "voltage_v": actuator.voltage_v,
                "current_a": actuator.current_a,
                "alerts_enabled": actuator.electrical_alerts_enabled,
                "voltage_lower_threshold": actuator.voltage_lower_threshold,
                "voltage_upper_threshold": actuator.voltage_upper_threshold,
                "current_lower_threshold": actuator.current_lower_threshold,
                "current_upper_threshold": actuator.current_upper_threshold,
            },
        }
        for actuator, model in actuator_rows
    ]
    example_actuator_code = (
        actuators[0]["actuator_code"] if actuators else "{actuator_code}"
    )
    normalized_config: dict[str, object] = {
        "schema_version": "2.0",
        "project": {"id": project.id, "code": project.code, "name": project.name},
        "device": {
            "id": device.id,
            "code": device.code,
            "name": device.name,
            "device_type": device.device_type,
            "enabled": device.is_enabled,
            "status": device.status.value,
            "template": (
                {
                    "id": template.id,
                    "code": template.code,
                    "name": template.name,
                    "nominal_output_voltage_v": template.nominal_output_voltage_v,
                }
                if template
                else None
            ),
        },
        "mqtt": {
            "host": settings.mqtt_public_host,
            "port": settings.mqtt_public_port,
            "client_id": device.code,
            "qos": settings.mqtt_qos,
            "topics": {
                "telemetry": telemetry_topic,
                "status": status_topic,
                "commands": command_topic,
                "command_ack": command_ack_topic,
            },
            "broker_host": settings.mqtt_public_host,
            "broker_port": settings.mqtt_public_port,
            "telemetry_topic": telemetry_topic,
            "status_topic": status_topic,
            "command_topic": command_topic,
            "command_ack_topic": command_ack_topic,
            "retain": False,
        },
        "telemetry": {
            "payload_version": "1",
            "timestamp_format": "ISO-8601",
            "readings_field": "readings",
            "recorded_at_source": "device",
            "received_at_source": "server",
        },
        "sensors": sensors,
        "actuators": actuators,
        "payload_contracts": {
            "telemetry": {
                "topic": telemetry_topic,
                "payload": {
                    "sent_at": generated_at,
                    "readings": [{"sensor_code": sensors[0]["sensor_code"] if sensors else "{sensor_code}", "value": 1.24, "recorded_at": generated_at}],
                },
            },
            "command": {
                "topic": command_topic,
                "payload": {
                    "command_id": 123,
                    "actuator_code": example_actuator_code,
                    "desired_state": True,
                    "requested_at": generated_at,
                },
            },
            "command_ack": {
                "topic": command_ack_topic,
                "payload": {
                    "command_id": 123,
                    "actuator_code": example_actuator_code,
                    "reported_state": True,
                    "status": "ACKNOWLEDGED",
                    "sent_at": generated_at,
                },
            },
            "status": {
                "topic": status_topic,
                "payload": {
                    "status": "ONLINE",
                    "sent_at": generated_at,
                    "actuators": [
                        {
                            "actuator_code": actuator["actuator_code"],
                            "state": actuator["default_state"],
                            "voltage_v": 12.41,
                            "current_a": 1.25,
                            "recorded_at": generated_at,
                        }
                        for actuator in actuators
                    ],
                },
            },
        },
    }
    canonical = json.dumps(
        normalized_config,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    configuration_hash = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    config = {
        **normalized_config,
        "generated_at": generated_at,
        "config_version": configuration_hash[:12],
        "configuration_hash": configuration_hash,
    }
    return config, project, device
