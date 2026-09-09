"""Canonical ownership-scoped Aquaponics System API."""

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import require_permission
from app.core.enums import ActuatorThresholdMetric, AlertLifecycleStatus, AquaponicsSystemStatus, ThresholdMetricType
from app.db.session import get_db
from app.models.actuator import Actuator, ActuatorCommand, ActuatorReading
from app.models.actuator_model import ActuatorModel
from app.models.device import Device
from app.models.device_template import DeviceTemplate, DeviceTemplateActuator, DeviceTemplateSensor
from app.models.project import Project
from app.models.sensor import Sensor
from app.models.sensor_model import SensorModel
from app.models.telemetry import TelemetryReading
from app.models.operational_alert import OperationalIncident
from app.models.threshold_alert_config import ThresholdAlertConfig
from app.models.user import User
from app.services.access_service import require_project_access
from app.services.threshold_alert_config_service import apply_threshold_alert_config_update, ensure_threshold_delivery_defaults
from app.services.operational_incident_service import enqueue_incident_notification, reevaluate_latest_sensor_threshold
from app.services.project_device_config_service import export_project_device_config
from app.services.permission_service import has_permission
from app.schemas.project import AquaponicsSystemMqttConfigExport
from app.schemas.threshold_alert_config import ThresholdAlertConfigCreate, ThresholdAlertConfigRead, ThresholdAlertConfigUpdate
from app.schemas.actuator import ActuatorCommandCreate, ActuatorCommandRead, ActuatorReadingRead
from app.schemas.alert import AlertRead, AlertResolutionRequest
from app.schemas.telemetry import TelemetryReadingRead

router = APIRouter(prefix="/aquaponics-systems")


class AquaponicsSystemCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    code: str = Field(pattern=r"^[A-Z0-9_-]+$", min_length=3, max_length=80)
    name: str = Field(min_length=2, max_length=255)
    location: str | None = None
    description: str | None = None


class AquaponicsSystemUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    code: str | None = Field(default=None, pattern=r"^[A-Z0-9_-]+$", min_length=3, max_length=80)
    name: str | None = Field(default=None, min_length=2, max_length=255)
    location: str | None = None
    description: str | None = None


class AquaponicsSystemRead(AquaponicsSystemCreate):
    model_config = ConfigDict(from_attributes=True)
    id: int
    owner_user_id: int
    status: AquaponicsSystemStatus
    disabled_at: datetime | None = None
    disabled_reason: str | None = None


class DeviceInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    code: str = Field(pattern=r"^[A-Z0-9_-]+$", min_length=3, max_length=80)
    name: str = Field(min_length=2, max_length=255)
    description: str | None = None
    location: str | None = None
    device_template_id: int | None = None


class SensorInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    sensor_model_id: int = Field(gt=0)
    code: str = Field(pattern=r"^[A-Z0-9_-]+$", min_length=2, max_length=80)
    name: str = Field(min_length=2, max_length=255)
    installation_location: str | None = None
    description: str | None = None


class ActuatorInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    actuator_model_id: int = Field(gt=0)
    code: str = Field(pattern=r"^[A-Z0-9_-]+$", min_length=2, max_length=80)
    name: str = Field(min_length=2, max_length=255)
    location: str | None = None
    notes: str | None = None


class DeviceUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    code: str | None = Field(default=None, pattern=r"^[A-Z0-9_-]+$", min_length=3, max_length=80)
    name: str | None = Field(default=None, min_length=2, max_length=255)
    description: str | None = None
    location: str | None = None
    device_template_id: int | None = Field(default=None, gt=0)
    is_enabled: bool | None = None


class SensorUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    sensor_model_id: int | None = Field(default=None, gt=0)
    code: str | None = Field(default=None, pattern=r"^[A-Z0-9_-]+$", min_length=2, max_length=80)
    name: str | None = Field(default=None, min_length=2, max_length=255)
    installation_location: str | None = None
    description: str | None = None
    is_enabled: bool | None = None


class ActuatorUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    actuator_model_id: int | None = Field(default=None, gt=0)
    code: str | None = Field(default=None, pattern=r"^[A-Z0-9_-]+$", min_length=2, max_length=80)
    name: str | None = Field(default=None, min_length=2, max_length=255)
    location: str | None = None
    notes: str | None = None
    is_enabled: bool | None = None


class SensorRead(BaseModel):
    id: int
    device_id: int
    sensor_model_id: int
    code: str
    name: str
    installation_location: str | None
    description: str | None
    status: str
    is_enabled: bool


class ActuatorRead(BaseModel):
    id: int
    device_id: int
    actuator_model_id: int | None
    code: str
    name: str
    location: str | None
    notes: str | None
    is_enabled: bool
    desired_state: bool | None
    reported_state: bool | None
    voltage_v: float | None
    current_a: float | None


class DeviceRead(BaseModel):
    id: int
    aquaponics_system_id: int
    code: str
    name: str
    description: str | None
    location: str | None
    device_template_id: int | None
    status: str
    is_enabled: bool
    sensors: list[SensorRead]
    actuators: list[ActuatorRead]


def _sensor_read(sensor: Sensor) -> dict:
    return {"id": sensor.id, "device_id": sensor.device_id, "sensor_model_id": sensor.sensor_model_id, "code": sensor.code, "name": sensor.name, "installation_location": sensor.installation_location, "description": sensor.description, "status": sensor.status, "is_enabled": sensor.is_enabled}


def _actuator_read(actuator: Actuator) -> dict:
    return {"id": actuator.id, "device_id": actuator.device_id, "actuator_model_id": actuator.actuator_model_id, "code": actuator.code, "name": actuator.name, "location": actuator.location, "notes": actuator.notes, "is_enabled": actuator.is_enabled, "desired_state": actuator.desired_state, "reported_state": actuator.reported_state, "voltage_v": actuator.voltage_v, "current_a": actuator.current_a}


def _sensor_threshold_from_defaults(sensor_id: int, *, model: SensorModel, mapping: DeviceTemplateSensor | None = None) -> ThresholdAlertConfig | None:
    def pick(mapping_field: str, model_field: str):
        mapped = getattr(mapping, mapping_field) if mapping is not None else None
        return mapped if mapped is not None else getattr(model, model_field)

    lower = pick("default_lower_threshold", "default_lower_threshold")
    upper = pick("default_upper_threshold", "default_upper_threshold")
    below_message = pick("default_below_threshold_message", "default_below_threshold_message")
    above_message = pick("default_above_threshold_message", "default_above_threshold_message")
    below_risk = (mapping.default_below_risk_level if mapping and mapping.default_below_risk_level is not None else model.default_alert_risk_level)
    above_risk = (mapping.default_above_risk_level if mapping and mapping.default_above_risk_level is not None else model.default_alert_risk_level)
    enabled = (mapping.default_alerts_enabled if mapping and mapping.default_alerts_enabled is not None else model.default_warning_enabled)
    if all(value is None for value in (lower, upper, below_message, above_message, below_risk, above_risk)):
        return None
    config = ThresholdAlertConfig(
        sensor_id=sensor_id, actuator_id=None, metric_type="SENSOR_VALUE", enabled=bool(enabled),
        lower_threshold=lower, upper_threshold=upper,
        below_risk_level=below_risk, above_risk_level=above_risk,
        below_message=below_message, above_message=above_message,
        delay_seconds=0,
    )
    ensure_threshold_delivery_defaults(config)
    return config


def _device_read(device: Device) -> dict:
    return {"id": device.id, "aquaponics_system_id": device.project_id, "code": device.code, "name": device.name, "description": device.description, "location": device.location, "device_template_id": device.device_template_id, "status": device.status, "is_enabled": device.is_enabled, "sensors": [_sensor_read(item) for item in device.sensors], "actuators": [_actuator_read(item) for item in device.actuators]}


async def _device(db: AsyncSession, system_id: int, device_id: int, actor: User, *, manage: bool = False) -> Device:
    await require_project_access(db, system_id, actor, manage=manage)
    item = await db.scalar(select(Device).options(selectinload(Device.sensors), selectinload(Device.actuators)).where(Device.id == device_id, Device.project_id == system_id, Device.is_deleted.is_(False)))
    if item is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy Device trong Hệ thống Aquaponics")
    return item


async def _sensor(db: AsyncSession, system_id: int, device_id: int, sensor_id: int, actor: User, *, manage: bool = False) -> Sensor:
    await _device(db, system_id, device_id, actor, manage=manage)
    item = await db.scalar(select(Sensor).where(Sensor.id == sensor_id, Sensor.device_id == device_id, Sensor.is_deleted.is_(False)))
    if item is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy Sensor trong Device")
    return item


@router.get("", response_model=list[AquaponicsSystemRead], tags=["Aquaponics Systems"])
async def list_systems(db: AsyncSession = Depends(get_db), actor: User = Depends(require_permission("aquaponics_systems.read"))) -> list[Project]:
    query = select(Project).where(Project.is_deleted.is_(False)).order_by(Project.name)
    if not await has_permission(db, actor, "aquaponics_systems.read_all"):
        query = query.where((Project.owner_user_id == actor.id) | Project.members.any(user_id=actor.id))
    return list((await db.scalars(query)).all())


@router.post("", response_model=AquaponicsSystemRead, status_code=status.HTTP_201_CREATED, tags=["Aquaponics Systems"])
async def create_system(payload: AquaponicsSystemCreate, db: AsyncSession = Depends(get_db), actor: User = Depends(require_permission("aquaponics_systems.create"))) -> Project:
    if await db.scalar(select(Project.id).where(Project.code == payload.code)):
        raise HTTPException(status_code=409, detail="Mã Hệ thống Aquaponics đã tồn tại")
    item = Project(owner_user_id=actor.id, **payload.model_dump())
    db.add(item)
    await db.commit()
    await db.refresh(item)
    return item


@router.get("/{system_id}", response_model=AquaponicsSystemRead, tags=["Aquaponics Systems"])
async def get_system(system_id: int, db: AsyncSession = Depends(get_db), actor: User = Depends(require_permission("aquaponics_systems.read"))) -> Project:
    return await require_project_access(db, system_id, actor)


@router.patch("/{system_id}", response_model=AquaponicsSystemRead, tags=["Aquaponics Systems"])
async def update_system(system_id: int, payload: AquaponicsSystemUpdate, db: AsyncSession = Depends(get_db), actor: User = Depends(require_permission("aquaponics_systems.update"))) -> Project:
    item = await require_project_access(db, system_id, actor, manage=True)
    for field, value in payload.model_dump(exclude_unset=True).items(): setattr(item, field, value)
    await db.commit()
    await db.refresh(item)
    return item


@router.delete("/{system_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["Aquaponics Systems"])
async def delete_system(system_id: int, db: AsyncSession = Depends(get_db), actor: User = Depends(require_permission("aquaponics_systems.delete"))) -> None:
    item = await require_project_access(db, system_id, actor, manage=True)
    item.is_deleted = True
    await db.commit()


@router.get("/{system_id}/devices", response_model=list[DeviceRead], tags=["Devices"])
async def list_devices(system_id: int, db: AsyncSession = Depends(get_db), actor: User = Depends(require_permission("devices.read"))) -> list[dict]:
    await require_project_access(db, system_id, actor)
    rows = list((await db.scalars(select(Device).options(selectinload(Device.sensors), selectinload(Device.actuators)).where(Device.project_id == system_id, Device.is_deleted.is_(False)).order_by(Device.name))).all())
    return [_device_read(item) for item in rows]


@router.post("/{system_id}/devices", response_model=DeviceRead, status_code=status.HTTP_201_CREATED, tags=["Devices"])
async def create_device(system_id: int, payload: DeviceInput, db: AsyncSession = Depends(get_db), actor: User = Depends(require_permission("devices.create"))) -> dict:
    await require_project_access(db, system_id, actor, manage=True)
    if await db.scalar(select(Device.id).where(Device.code == payload.code)):
        raise HTTPException(status_code=409, detail="Mã Device đã tồn tại")
    template = None
    if payload.device_template_id is not None:
        template = await db.scalar(
            select(DeviceTemplate)
            .options(
                selectinload(DeviceTemplate.sensor_mappings).selectinload(DeviceTemplateSensor.sensor_model),
                selectinload(DeviceTemplate.actuator_mappings),
            )
            .where(
                DeviceTemplate.id == payload.device_template_id,
                DeviceTemplate.is_deleted.is_(False),
                DeviceTemplate.is_active.is_(True),
            )
        )
        if template is None:
            raise HTTPException(status_code=422, detail="DeviceTemplate không tồn tại hoặc không hoạt động")
    item = Device(project_id=system_id, **payload.model_dump())
    db.add(item)
    await db.flush()
    if template is not None:
        for mapping in template.sensor_mappings:
            sensor = Sensor(
                device_id=item.id,
                sensor_model_id=mapping.sensor_model_id,
                code=mapping.slot_code,
                name=mapping.display_name or mapping.slot_code,
                installation_location=mapping.default_location,
                is_enabled=True,
            )
            db.add(sensor)
            await db.flush()
            threshold_config = _sensor_threshold_from_defaults(sensor.id, model=mapping.sensor_model, mapping=mapping)
            if threshold_config is not None:
                db.add(threshold_config)
        for mapping in template.actuator_mappings:
            db.add(Actuator(
                device_id=item.id,
                actuator_model_id=mapping.actuator_model_id,
                code=mapping.code,
                name=mapping.default_name or mapping.code,
                location=mapping.default_location,
                notes=mapping.default_notes,
                is_enabled=mapping.is_enabled,
                desired_state=mapping.default_state,
            ))
    await db.commit()
    item = await db.scalar(
        select(Device)
        .options(selectinload(Device.sensors), selectinload(Device.actuators))
        .where(Device.id == item.id)
    )
    return _device_read(item)


@router.get("/{system_id}/devices/{device_id}", response_model=DeviceRead, tags=["Devices"])
async def get_device(system_id: int, device_id: int, db: AsyncSession = Depends(get_db), actor: User = Depends(require_permission("devices.read"))) -> dict:
    return _device_read(await _device(db, system_id, device_id, actor))


@router.patch("/{system_id}/devices/{device_id}", response_model=DeviceRead, tags=["Devices"])
async def update_device(system_id: int, device_id: int, payload: DeviceUpdate, db: AsyncSession = Depends(get_db), actor: User = Depends(require_permission("devices.update"))) -> dict:
    item = await _device(db, system_id, device_id, actor, manage=True)
    for field, value in payload.model_dump(exclude_unset=True).items(): setattr(item, field, value)
    await db.commit()
    await db.refresh(item, attribute_names=["sensors", "actuators"])
    return _device_read(item)


@router.delete("/{system_id}/devices/{device_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["Devices"])
async def delete_device(system_id: int, device_id: int, db: AsyncSession = Depends(get_db), actor: User = Depends(require_permission("devices.delete"))) -> None:
    item = await _device(db, system_id, device_id, actor, manage=True)
    item.is_deleted = True
    await db.commit()


@router.get("/{system_id}/devices/{device_id}/sensors", response_model=list[SensorRead], tags=["Sensors"])
async def list_sensors(system_id: int, device_id: int, db: AsyncSession = Depends(get_db), actor: User = Depends(require_permission("sensors.read"))) -> list[dict]:
    return [_sensor_read(item) for item in (await _device(db, system_id, device_id, actor)).sensors]


@router.post("/{system_id}/devices/{device_id}/sensors", response_model=SensorRead, status_code=status.HTTP_201_CREATED, tags=["Sensors"])
async def create_sensor(system_id: int, device_id: int, payload: SensorInput, db: AsyncSession = Depends(get_db), actor: User = Depends(require_permission("sensors.create"))) -> dict:
    await _device(db, system_id, device_id, actor, manage=True)
    model = await db.get(SensorModel, payload.sensor_model_id)
    if model is None:
        raise HTTPException(status_code=422, detail="Sensor model không tồn tại")
    if await db.scalar(select(Sensor.id).where(Sensor.code == payload.code)):
        raise HTTPException(status_code=409, detail="Mã Sensor đã tồn tại")
    item = Sensor(device_id=device_id, **payload.model_dump())
    db.add(item)
    await db.flush()
    threshold_config = _sensor_threshold_from_defaults(item.id, model=model)
    if threshold_config is not None:
        db.add(threshold_config)
    await db.commit()
    await db.refresh(item)
    return _sensor_read(item)


@router.get("/{system_id}/devices/{device_id}/sensors/{sensor_id}", response_model=SensorRead, tags=["Sensors"])
async def get_sensor(system_id: int, device_id: int, sensor_id: int, db: AsyncSession = Depends(get_db), actor: User = Depends(require_permission("sensors.read"))) -> dict:
    return _sensor_read(await _sensor(db, system_id, device_id, sensor_id, actor))


@router.patch("/{system_id}/devices/{device_id}/sensors/{sensor_id}", response_model=SensorRead, tags=["Sensors"])
async def update_sensor(system_id: int, device_id: int, sensor_id: int, payload: SensorUpdate, db: AsyncSession = Depends(get_db), actor: User = Depends(require_permission("sensors.update"))) -> dict:
    item = await _sensor(db, system_id, device_id, sensor_id, actor, manage=True)
    for field, value in payload.model_dump(exclude_unset=True).items(): setattr(item, field, value)
    await db.commit()
    await db.refresh(item)
    return _sensor_read(item)


@router.delete("/{system_id}/devices/{device_id}/sensors/{sensor_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["Sensors"])
async def delete_sensor(system_id: int, device_id: int, sensor_id: int, db: AsyncSession = Depends(get_db), actor: User = Depends(require_permission("sensors.delete"))) -> None:
    item = await _sensor(db, system_id, device_id, sensor_id, actor, manage=True)
    item.is_deleted = True
    await db.commit()


@router.get("/{system_id}/devices/{device_id}/actuators", response_model=list[ActuatorRead], tags=["Actuators"])
async def list_actuators(system_id: int, device_id: int, db: AsyncSession = Depends(get_db), actor: User = Depends(require_permission("actuators.read"))) -> list[dict]:
    return [_actuator_read(item) for item in (await _device(db, system_id, device_id, actor)).actuators]


@router.post("/{system_id}/devices/{device_id}/actuators", response_model=ActuatorRead, status_code=status.HTTP_201_CREATED, tags=["Actuators"])
async def create_actuator(system_id: int, device_id: int, payload: ActuatorInput, db: AsyncSession = Depends(get_db), actor: User = Depends(require_permission("actuators.create"))) -> dict:
    await _device(db, system_id, device_id, actor, manage=True)
    if await db.get(ActuatorModel, payload.actuator_model_id) is None:
        raise HTTPException(status_code=422, detail="Actuator model không tồn tại")
    if await db.scalar(select(Actuator.id).where(Actuator.code == payload.code)):
        raise HTTPException(status_code=409, detail="Mã Actuator đã tồn tại")
    sequence = int(await db.scalar(select(Actuator.sequence_number).where(Actuator.device_id == device_id).order_by(Actuator.sequence_number.desc()).limit(1)) or 0) + 1
    item = Actuator(device_id=device_id, sequence_number=sequence, **payload.model_dump())
    db.add(item)
    await db.commit()
    await db.refresh(item)
    return _actuator_read(item)


@router.get("/{system_id}/devices/{device_id}/actuators/{actuator_id}", response_model=ActuatorRead, tags=["Actuators"])
async def get_actuator(system_id: int, device_id: int, actuator_id: int, db: AsyncSession = Depends(get_db), actor: User = Depends(require_permission("actuators.read"))) -> dict:
    await _device(db, system_id, device_id, actor)
    item = await db.scalar(select(Actuator).where(Actuator.id == actuator_id, Actuator.device_id == device_id, Actuator.is_deleted.is_(False)))
    if item is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy Actuator trong Device")
    return _actuator_read(item)


@router.patch("/{system_id}/devices/{device_id}/actuators/{actuator_id}", response_model=ActuatorRead, tags=["Actuators"])
async def update_actuator(system_id: int, device_id: int, actuator_id: int, payload: ActuatorUpdate, db: AsyncSession = Depends(get_db), actor: User = Depends(require_permission("actuators.update"))) -> dict:
    await _device(db, system_id, device_id, actor, manage=True)
    item = await db.scalar(select(Actuator).where(Actuator.id == actuator_id, Actuator.device_id == device_id, Actuator.is_deleted.is_(False)))
    if item is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy Actuator trong Device")
    for field, value in payload.model_dump(exclude_unset=True).items(): setattr(item, field, value)
    await db.commit()
    await db.refresh(item)
    return _actuator_read(item)


@router.delete("/{system_id}/devices/{device_id}/actuators/{actuator_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["Actuators"])
async def delete_actuator(system_id: int, device_id: int, actuator_id: int, db: AsyncSession = Depends(get_db), actor: User = Depends(require_permission("actuators.delete"))) -> None:
    await _device(db, system_id, device_id, actor, manage=True)
    item = await db.scalar(select(Actuator).where(Actuator.id == actuator_id, Actuator.device_id == device_id, Actuator.is_deleted.is_(False)))
    if item is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy Actuator trong Device")
    item.is_deleted = True
    await db.commit()


@router.get("/{system_id}/devices/{device_id}/sensors/{sensor_id}/threshold-alert", response_model=ThresholdAlertConfigRead | None, tags=["Sensors"])
async def get_sensor_threshold(system_id: int, device_id: int, sensor_id: int, db: AsyncSession = Depends(get_db), actor: User = Depends(require_permission("sensors.thresholds.read"))) -> ThresholdAlertConfig | None:
    await _sensor(db, system_id, device_id, sensor_id, actor)
    return await db.scalar(select(ThresholdAlertConfig).where(ThresholdAlertConfig.sensor_id == sensor_id, ThresholdAlertConfig.metric_type == "SENSOR_VALUE"))


@router.post("/{system_id}/devices/{device_id}/sensors/{sensor_id}/threshold-alert", response_model=ThresholdAlertConfigRead, status_code=status.HTTP_201_CREATED, responses={409: {"description": "Threshold already configured"}}, tags=["Sensors"])
async def create_sensor_threshold(system_id: int, device_id: int, sensor_id: int, payload: ThresholdAlertConfigCreate, db: AsyncSession = Depends(get_db), actor: User = Depends(require_permission("sensors.thresholds.create"))) -> ThresholdAlertConfig:
    sensor = await _sensor(db, system_id, device_id, sensor_id, actor, manage=True)
    device = await db.get(Device, device_id)
    if await db.scalar(select(ThresholdAlertConfig.id).where(ThresholdAlertConfig.sensor_id == sensor_id)):
        raise HTTPException(status_code=409, detail="Threshold của Sensor đã tồn tại")
    item = ThresholdAlertConfig(sensor_id=sensor_id, actuator_id=None, metric_type="SENSOR_VALUE", **payload.model_dump())
    ensure_threshold_delivery_defaults(item)
    db.add(item)
    await db.flush()
    await reevaluate_latest_sensor_threshold(db, device=device, sensor=sensor)
    await db.commit()
    await db.refresh(item)
    return item


@router.patch("/{system_id}/devices/{device_id}/sensors/{sensor_id}/threshold-alert", response_model=ThresholdAlertConfigRead, tags=["Sensors"])
async def update_sensor_threshold(system_id: int, device_id: int, sensor_id: int, payload: ThresholdAlertConfigUpdate, db: AsyncSession = Depends(get_db), actor: User = Depends(require_permission("sensors.thresholds.update"))) -> ThresholdAlertConfig:
    sensor = await _sensor(db, system_id, device_id, sensor_id, actor, manage=True)
    device = await db.get(Device, device_id)
    item = await db.scalar(select(ThresholdAlertConfig).where(ThresholdAlertConfig.sensor_id == sensor_id))
    if item is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy Threshold của Sensor")
    apply_threshold_alert_config_update(item, payload.model_dump(exclude_unset=True))
    await db.flush()
    await reevaluate_latest_sensor_threshold(db, device=device, sensor=sensor)
    await db.commit()
    await db.refresh(item)
    return item


@router.delete("/{system_id}/devices/{device_id}/sensors/{sensor_id}/threshold-alert", status_code=status.HTTP_204_NO_CONTENT, tags=["Sensors"])
async def delete_sensor_threshold(system_id: int, device_id: int, sensor_id: int, db: AsyncSession = Depends(get_db), actor: User = Depends(require_permission("sensors.thresholds.delete"))) -> None:
    sensor = await _sensor(db, system_id, device_id, sensor_id, actor, manage=True)
    device = await db.get(Device, device_id)
    item = await db.scalar(select(ThresholdAlertConfig).where(ThresholdAlertConfig.sensor_id == sensor_id))
    if item is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy Threshold của Sensor")
    await db.delete(item)
    await db.flush()
    await reevaluate_latest_sensor_threshold(db, device=device, sensor=sensor)
    await db.commit()


@router.get("/{system_id}/devices/{device_id}/sensors/{sensor_id}/telemetry", response_model=list[TelemetryReadingRead], tags=["Sensors"])
async def sensor_telemetry(system_id: int, device_id: int, sensor_id: int, start: datetime | None = None, end: datetime | None = None, limit: int = Query(default=500, ge=1, le=5000), db: AsyncSession = Depends(get_db), actor: User = Depends(require_permission("sensors.telemetry.read"))) -> list[dict]:
    await _sensor(db, system_id, device_id, sensor_id, actor)
    query = select(TelemetryReading).where(TelemetryReading.sensor_id == sensor_id)
    if start is not None:
        query = query.where(TelemetryReading.recorded_at >= start)
    if end is not None:
        query = query.where(TelemetryReading.recorded_at <= end)
    rows = list((await db.scalars(query.order_by(TelemetryReading.recorded_at.desc()).limit(limit))).all())
    return rows


@router.get("/{system_id}/mqtt-config/export", response_model=AquaponicsSystemMqttConfigExport, tags=["Aquaponics Systems"])
async def export_mqtt_config(system_id: int, db: AsyncSession = Depends(get_db), actor: User = Depends(require_permission("mqtt_config.export"))) -> AquaponicsSystemMqttConfigExport:
    await require_project_access(db, system_id, actor)
    return await export_project_device_config(db, project_id=system_id)


@router.get("/{system_id}/devices/{device_id}/actuators/{actuator_id}/readings", response_model=list[ActuatorReadingRead], tags=["Actuators"])
async def actuator_readings(system_id: int, device_id: int, actuator_id: int, limit: int = Query(default=200, ge=1, le=1000), db: AsyncSession = Depends(get_db), actor: User = Depends(require_permission("actuators.readings.read"))) -> list[ActuatorReading]:
    await _device(db, system_id, device_id, actor)
    actuator = await db.scalar(select(Actuator).where(Actuator.id == actuator_id, Actuator.device_id == device_id, Actuator.is_deleted.is_(False), Actuator.removed_at.is_(None)))
    if actuator is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy Actuator trong Device")
    return list((await db.scalars(select(ActuatorReading).where(ActuatorReading.actuator_id == actuator_id).order_by(ActuatorReading.recorded_at.desc()).limit(limit))).all())


@router.get("/{system_id}/devices/{device_id}/actuators/{actuator_id}/commands", response_model=list[ActuatorCommandRead], tags=["Actuators"])
async def actuator_commands(system_id: int, device_id: int, actuator_id: int, limit: int = Query(default=100, ge=1, le=500), db: AsyncSession = Depends(get_db), actor: User = Depends(require_permission("actuators.commands.read"))) -> list[ActuatorCommand]:
    await _device(db, system_id, device_id, actor)
    rows = list((await db.scalars(select(ActuatorCommand).where(ActuatorCommand.actuator_id == actuator_id).order_by(ActuatorCommand.requested_at.desc()).limit(limit))).all())
    return [{"command_id": row.id, "actuator_id": row.actuator_id, "desired_state": row.desired_state, "reported_state": row.reported_state, "status": row.status, "requested_at": row.requested_at} for row in rows]


@router.post("/{system_id}/devices/{device_id}/actuators/{actuator_id}/commands", response_model=ActuatorCommandRead, status_code=status.HTTP_201_CREATED, tags=["Actuators"])
async def create_actuator_command(system_id: int, device_id: int, actuator_id: int, payload: ActuatorCommandCreate, db: AsyncSession = Depends(get_db), actor: User = Depends(require_permission("actuators.commands.create"))) -> dict:
    await _device(db, system_id, device_id, actor, manage=True)
    actuator = await db.scalar(select(Actuator).where(Actuator.id == actuator_id, Actuator.device_id == device_id, Actuator.is_deleted.is_(False), Actuator.removed_at.is_(None)))
    if actuator is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy Actuator trong Device")
    command = ActuatorCommand(actuator_id=actuator_id, desired_state=payload.desired_state, requested_by_user_id=actor.id, requested_at=datetime.now(UTC), status="PENDING")
    db.add(command)
    await db.commit()
    await db.refresh(command)
    return {"command_id": command.id, "actuator_id": command.actuator_id, "desired_state": command.desired_state, "reported_state": command.reported_state, "status": command.status, "requested_at": command.requested_at}


async def _actuator(db: AsyncSession, system_id: int, device_id: int, actuator_id: int, actor: User, *, manage: bool = False) -> Actuator:
    await _device(db, system_id, device_id, actor, manage=manage)
    item = await db.scalar(select(Actuator).where(Actuator.id == actuator_id, Actuator.device_id == device_id, Actuator.is_deleted.is_(False), Actuator.removed_at.is_(None)))
    if item is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy Actuator trong Device")
    return item


@router.get("/{system_id}/devices/{device_id}/actuators/{actuator_id}/threshold-alerts/{metric}", response_model=ThresholdAlertConfigRead | None, tags=["Actuators"])
async def get_actuator_threshold(system_id: int, device_id: int, actuator_id: int, metric: ActuatorThresholdMetric, db: AsyncSession = Depends(get_db), actor: User = Depends(require_permission("actuators.thresholds.read"))) -> ThresholdAlertConfig | None:
    await _actuator(db, system_id, device_id, actuator_id, actor)
    return await db.scalar(select(ThresholdAlertConfig).where(ThresholdAlertConfig.actuator_id == actuator_id, ThresholdAlertConfig.metric_type == metric))


@router.post("/{system_id}/devices/{device_id}/actuators/{actuator_id}/threshold-alerts/{metric}", response_model=ThresholdAlertConfigRead, status_code=status.HTTP_201_CREATED, responses={409: {"description": "Threshold already configured"}}, tags=["Actuators"])
async def create_actuator_threshold(system_id: int, device_id: int, actuator_id: int, metric: ActuatorThresholdMetric, payload: ThresholdAlertConfigCreate, db: AsyncSession = Depends(get_db), actor: User = Depends(require_permission("actuators.thresholds.create"))) -> ThresholdAlertConfig:
    await _actuator(db, system_id, device_id, actuator_id, actor, manage=True)
    if await db.scalar(select(ThresholdAlertConfig.id).where(ThresholdAlertConfig.actuator_id == actuator_id, ThresholdAlertConfig.metric_type == metric)):
        raise HTTPException(status_code=409, detail="Threshold của Actuator đã tồn tại")
    item = ThresholdAlertConfig(actuator_id=actuator_id, sensor_id=None, metric_type=metric, **payload.model_dump())
    ensure_threshold_delivery_defaults(item)
    db.add(item); await db.commit(); await db.refresh(item)
    return item


@router.patch("/{system_id}/devices/{device_id}/actuators/{actuator_id}/threshold-alerts/{metric}", response_model=ThresholdAlertConfigRead, tags=["Actuators"])
async def update_actuator_threshold(system_id: int, device_id: int, actuator_id: int, metric: ActuatorThresholdMetric, payload: ThresholdAlertConfigUpdate, db: AsyncSession = Depends(get_db), actor: User = Depends(require_permission("actuators.thresholds.update"))) -> ThresholdAlertConfig:
    await _actuator(db, system_id, device_id, actuator_id, actor, manage=True)
    item = await db.scalar(select(ThresholdAlertConfig).where(ThresholdAlertConfig.actuator_id == actuator_id, ThresholdAlertConfig.metric_type == metric))
    if item is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy Threshold của Actuator")
    apply_threshold_alert_config_update(item, payload.model_dump(exclude_unset=True)); await db.commit(); await db.refresh(item)
    return item


@router.delete("/{system_id}/devices/{device_id}/actuators/{actuator_id}/threshold-alerts/{metric}", status_code=status.HTTP_204_NO_CONTENT, tags=["Actuators"])
async def delete_actuator_threshold(system_id: int, device_id: int, actuator_id: int, metric: ActuatorThresholdMetric, db: AsyncSession = Depends(get_db), actor: User = Depends(require_permission("actuators.thresholds.delete"))) -> None:
    await _actuator(db, system_id, device_id, actuator_id, actor, manage=True)
    item = await db.scalar(select(ThresholdAlertConfig).where(ThresholdAlertConfig.actuator_id == actuator_id, ThresholdAlertConfig.metric_type == metric))
    if item is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy Threshold của Actuator")
    await db.delete(item); await db.commit()


async def _alert_read(db: AsyncSession, row: OperationalIncident) -> AlertRead:
    snapshot = row.trigger_snapshot or {}
    resolved_by = await db.get(User, row.resolved_by) if row.resolved_by else None
    resource_type = snapshot.get("resource_type") or ("ACTUATOR" if row.actuator_id else "SENSOR")
    return AlertRead(
        id=row.id, resource_type=resource_type, device_id=row.device_id, sensor_id=row.sensor_id,
        actuator_id=row.actuator_id, metric=str(snapshot.get("metric_type") or "SENSOR_VALUE"),
        direction=snapshot.get("threshold_direction"), alert_type=str(snapshot.get("incident_type") or "THRESHOLD"),
        severity=row.technical_severity, risk_level=row.business_risk_level_snapshot, status=row.status,
        message=str(snapshot.get("message") or snapshot.get("rule_name") or "Cảnh báo vận hành"),
        actual_value=snapshot.get("value"), threshold_value=snapshot.get("threshold"),
        started_at=row.started_at, last_triggered_at=row.last_triggered_at,
        occurrence_count=row.occurrence_count, acknowledged_at=row.acknowledged_at,
        acknowledged_by=row.acknowledged_by, condition_active=row.status not in {"NORMALIZED", "RESOLVED"},
        normalized_at=row.normalized_at, resolved_at=row.resolved_at, resolved_by_user_id=row.resolved_by,
        resolved_by_name=resolved_by.full_name if resolved_by else None, resolution_note=row.resolution_note,
        created_at=row.created_at, updated_at=row.updated_at,
    )


async def _alert(db: AsyncSession, system_id: int, alert_id: int, actor: User) -> OperationalIncident:
    await require_project_access(db, system_id, actor)
    row = await db.scalar(select(OperationalIncident).where(OperationalIncident.id == alert_id, OperationalIncident.project_id == system_id))
    if row is None: raise HTTPException(status_code=404, detail="Không tìm thấy cảnh báo")
    return row


@router.get("/{system_id}/alerts", response_model=list[AlertRead], tags=["Alerts"])
async def list_system_alerts(system_id: int, status_filter: AlertLifecycleStatus | None = Query(default=None, alias="status"), db: AsyncSession = Depends(get_db), actor: User = Depends(require_permission("incidents.read"))) -> list[AlertRead]:
    await require_project_access(db, system_id, actor)
    query = select(OperationalIncident).where(OperationalIncident.project_id == system_id)
    if status_filter is not None: query = query.where(OperationalIncident.status == status_filter)
    rows = (await db.scalars(query.order_by(OperationalIncident.started_at.desc()).limit(500))).all()
    return [await _alert_read(db, row) for row in rows]


@router.get("/{system_id}/alerts/{alert_id}", response_model=AlertRead, tags=["Alerts"])
async def get_system_alert(system_id: int, alert_id: int, db: AsyncSession = Depends(get_db), actor: User = Depends(require_permission("incidents.read"))) -> AlertRead:
    return await _alert_read(db, await _alert(db, system_id, alert_id, actor))


@router.post("/{system_id}/alerts/{alert_id}/acknowledge", response_model=AlertRead, tags=["Alerts"])
async def acknowledge_system_alert(system_id: int, alert_id: int, db: AsyncSession = Depends(get_db), actor: User = Depends(require_permission("incidents.acknowledge"))) -> AlertRead:
    row = await _alert(db, system_id, alert_id, actor)
    if row.status == "RESOLVED": raise HTTPException(status_code=409, detail="Cảnh báo đã được xử lý")
    row.status = "ACKNOWLEDGED"; row.acknowledged_at = datetime.now(UTC); row.acknowledged_by = actor.id
    await db.commit(); await db.refresh(row); return await _alert_read(db, row)


@router.post("/{system_id}/alerts/{alert_id}/resolve", response_model=AlertRead, tags=["Alerts"])
async def resolve_system_alert(system_id: int, alert_id: int, payload: AlertResolutionRequest, db: AsyncSession = Depends(get_db), actor: User = Depends(require_permission("incidents.resolve"))) -> AlertRead:
    row = await _alert(db, system_id, alert_id, actor)
    if row.status == "RESOLVED": raise HTTPException(status_code=409, detail="Cảnh báo đã được xử lý")
    row.status = "RESOLVED"; row.resolved_at = datetime.now(UTC); row.resolved_by = actor.id; row.resolution_note = payload.resolution_note
    await enqueue_incident_notification(db, row, "RESOLVED")
    await db.commit(); await db.refresh(row); return await _alert_read(db, row)
