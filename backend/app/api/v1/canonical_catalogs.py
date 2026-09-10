"""Typed global catalog and User endpoints for the canonical API."""

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import require_permission
from app.core.enums import UserStatus
from app.db.session import get_db
from app.models.actuator_model import ActuatorModel
from app.models.device_template import DeviceTemplate, DeviceTemplateActuator, DeviceTemplateSensor
from app.models.sensor_model import SensorModel
from app.models.user import User
from app.services.public_identity_service import PublicIdentityNotFoundError, get_user_by_public_id

router = APIRouter()


class DeviceTemplateCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    code: str = Field(pattern=r"^[A-Z0-9_-]+$", min_length=2, max_length=80)
    name: str = Field(min_length=2, max_length=255)
    description: str | None = None


class DeviceTemplateUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str | None = Field(default=None, min_length=2, max_length=255)
    description: str | None = None
    is_active: bool | None = None


class TemplateSensorSlotCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    sensor_model_id: int = Field(gt=0)
    code: str = Field(min_length=2, max_length=80)
    sort_order: int = 0
    is_required: bool = False


class TemplateSensorSlotUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    sensor_model_id: int | None = Field(default=None, gt=0)
    code: str | None = Field(default=None, min_length=2, max_length=80)
    sort_order: int | None = None
    is_required: bool | None = None


class TemplateSensorSlotRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    template_id: int
    code: str
    sensor_model_id: int
    sensor_model_name: str
    sort_order: int
    is_required: bool


class TemplateActuatorSlotCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    actuator_model_id: int = Field(gt=0)
    code: str = Field(pattern=r"^[A-Z0-9_-]+$", min_length=2, max_length=80)
    sort_order: int = 0
    is_required: bool = False


class TemplateActuatorSlotUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    actuator_model_id: int | None = Field(default=None, gt=0)
    code: str | None = Field(default=None, pattern=r"^[A-Z0-9_-]+$", min_length=2, max_length=80)
    sort_order: int | None = None
    is_required: bool | None = None


class TemplateActuatorSlotRead(BaseModel):
    id: int
    template_id: int
    code: str
    actuator_model_id: int
    actuator_model_name: str
    sort_order: int
    is_required: bool


class DeviceTemplateRead(DeviceTemplateCreate):
    id: int
    is_active: bool
    sensors: list[TemplateSensorSlotRead]
    actuators: list[TemplateActuatorSlotRead]


class ActuatorModelCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    code: str = Field(pattern=r"^[A-Z0-9_-]+$", min_length=2, max_length=80)
    name: str = Field(min_length=2, max_length=255)
    description: str | None = None
    data_type: str = "BOOLEAN"
    default_state: bool = False
    sort_order: int = 0
    nominal_voltage_v: float | None = Field(default=None, gt=0)
    voltage_tolerance_v: float | None = Field(default=None, ge=0)
    zero_voltage_max_v: float | None = Field(default=None, ge=0)
    minimum_running_current_a: float | None = Field(default=None, ge=0)
    maximum_running_current_a: float | None = Field(default=None, ge=0)


class ActuatorModelUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str | None = Field(default=None, min_length=2, max_length=255)
    description: str | None = None
    data_type: str | None = None
    default_state: bool | None = None
    sort_order: int | None = None
    is_active: bool | None = None
    nominal_voltage_v: float | None = Field(default=None, gt=0)
    voltage_tolerance_v: float | None = Field(default=None, ge=0)
    zero_voltage_max_v: float | None = Field(default=None, ge=0)
    minimum_running_current_a: float | None = Field(default=None, ge=0)
    maximum_running_current_a: float | None = Field(default=None, ge=0)


class ActuatorModelRead(ActuatorModelCreate):
    model_config = ConfigDict(from_attributes=True)
    id: int
    is_active: bool
    created_at: datetime
    updated_at: datetime


class UserRead(BaseModel):
    id: UUID
    username: str
    full_name: str
    email: str
    phone_number: str
    role_id: int | None
    role_code: str | None
    role_name: str | None
    status: UserStatus
    last_login_at: datetime | None
    created_at: datetime
    updated_at: datetime


def _sensor_slot(row: DeviceTemplateSensor) -> TemplateSensorSlotRead:
    return TemplateSensorSlotRead(id=row.id, template_id=row.device_template_id, code=row.code,
        sensor_model_id=row.sensor_model_id, sensor_model_name=row.sensor_model.name,
        sort_order=row.sort_order, is_required=row.is_required)


def _actuator_slot(row: DeviceTemplateActuator) -> TemplateActuatorSlotRead:
    return TemplateActuatorSlotRead(id=row.id, template_id=row.device_template_id, code=row.code,
        actuator_model_id=row.actuator_model_id, actuator_model_name=row.actuator_model.name,
        sort_order=row.sort_order, is_required=row.is_required)


def _template_read(row: DeviceTemplate) -> DeviceTemplateRead:
    return DeviceTemplateRead(id=row.id, code=row.code, name=row.name, description=row.description,
        is_active=row.is_active, sensors=[_sensor_slot(x) for x in row.sensor_mappings],
        actuators=[_actuator_slot(x) for x in row.actuator_mappings])


def _user_read(row: User) -> UserRead:
    return UserRead(id=row.public_id, username=row.username, full_name=row.full_name, email=row.email,
        phone_number=row.phone_number, role_id=row.role_id, role_code=row.role.code if row.role else None,
        role_name=row.role.name if row.role else None, status=row.status, last_login_at=row.last_login_at,
        created_at=row.created_at, updated_at=row.updated_at)


async def _template(db: AsyncSession, template_id: int) -> DeviceTemplate:
    row = await db.scalar(select(DeviceTemplate).options(selectinload(DeviceTemplate.sensor_mappings).selectinload(DeviceTemplateSensor.sensor_model), selectinload(DeviceTemplate.actuator_mappings).selectinload(DeviceTemplateActuator.actuator_model)).where(DeviceTemplate.id == template_id, DeviceTemplate.is_deleted.is_(False)))
    if row is None: raise HTTPException(404, "Không tìm thấy DeviceTemplate")
    return row


async def _sensor_mapping(db: AsyncSession, template_id: int, mapping_id: int) -> DeviceTemplateSensor:
    row = await db.scalar(select(DeviceTemplateSensor).options(selectinload(DeviceTemplateSensor.sensor_model)).where(DeviceTemplateSensor.id == mapping_id, DeviceTemplateSensor.device_template_id == template_id))
    if row is None: raise HTTPException(404, "Không tìm thấy Sensor slot")
    return row


async def _actuator_mapping(db: AsyncSession, template_id: int, mapping_id: int) -> DeviceTemplateActuator:
    row = await db.scalar(select(DeviceTemplateActuator).options(selectinload(DeviceTemplateActuator.actuator_model)).where(DeviceTemplateActuator.id == mapping_id, DeviceTemplateActuator.device_template_id == template_id))
    if row is None: raise HTTPException(404, "Không tìm thấy Actuator slot")
    return row


@router.get("/users", response_model=list[UserRead], tags=["Users"])
async def list_users(db: AsyncSession = Depends(get_db), _: User = Depends(require_permission("users.read"))) -> list[UserRead]:
    rows = (await db.scalars(select(User).options(selectinload(User.role)).where(User.is_deleted.is_(False)).order_by(User.full_name))).all()
    return [_user_read(row) for row in rows]


@router.get("/users/{user_id}", response_model=UserRead, tags=["Users"])
async def get_user(user_id: UUID, db: AsyncSession = Depends(get_db), _: User = Depends(require_permission("users.read"))) -> UserRead:
    try:
        row = await get_user_by_public_id(db, user_id)
    except PublicIdentityNotFoundError as exc:
        raise HTTPException(404, str(exc)) from exc
    await db.refresh(row, attribute_names=["role"])
    return _user_read(row)


@router.get("/device-templates", response_model=list[DeviceTemplateRead], tags=["Device Templates"])
async def list_device_templates(db: AsyncSession = Depends(get_db), _: User = Depends(require_permission("device_templates.read"))) -> list[DeviceTemplateRead]:
    rows = (await db.scalars(select(DeviceTemplate).options(selectinload(DeviceTemplate.sensor_mappings).selectinload(DeviceTemplateSensor.sensor_model), selectinload(DeviceTemplate.actuator_mappings).selectinload(DeviceTemplateActuator.actuator_model)).where(DeviceTemplate.is_deleted.is_(False)).order_by(DeviceTemplate.name))).unique().all()
    return [_template_read(row) for row in rows]


@router.post("/device-templates", response_model=DeviceTemplateRead, status_code=201, tags=["Device Templates"])
async def create_device_template(payload: DeviceTemplateCreate, db: AsyncSession = Depends(get_db), _: User = Depends(require_permission("device_templates.create"))) -> DeviceTemplateRead:
    if await db.scalar(select(DeviceTemplate.id).where(DeviceTemplate.code == payload.code)): raise HTTPException(409, "Mã DeviceTemplate đã tồn tại")
    row = DeviceTemplate(**payload.model_dump()); db.add(row); await db.commit()
    return _template_read(await _template(db, row.id))


@router.get("/device-templates/{template_id}", response_model=DeviceTemplateRead, tags=["Device Templates"])
async def get_device_template(template_id: int, db: AsyncSession = Depends(get_db), _: User = Depends(require_permission("device_templates.read"))) -> DeviceTemplateRead:
    return _template_read(await _template(db, template_id))


@router.patch("/device-templates/{template_id}", response_model=DeviceTemplateRead, tags=["Device Templates"])
async def update_device_template(template_id: int, payload: DeviceTemplateUpdate, db: AsyncSession = Depends(get_db), _: User = Depends(require_permission("device_templates.update"))) -> DeviceTemplateRead:
    row = await _template(db, template_id)
    for key, value in payload.model_dump(exclude_unset=True).items(): setattr(row, key, value)
    await db.commit(); return _template_read(await _template(db, template_id))


@router.delete("/device-templates/{template_id}", status_code=204, tags=["Device Templates"])
async def delete_device_template(template_id: int, db: AsyncSession = Depends(get_db), _: User = Depends(require_permission("device_templates.delete"))) -> None:
    row = await _template(db, template_id); row.is_deleted = True; await db.commit()


@router.get("/device-templates/{template_id}/sensors", response_model=list[TemplateSensorSlotRead], tags=["Device Templates"])
async def list_template_sensors(template_id: int, db: AsyncSession = Depends(get_db), _: User = Depends(require_permission("device_templates.read"))) -> list[TemplateSensorSlotRead]:
    return [_sensor_slot(x) for x in (await _template(db, template_id)).sensor_mappings]


@router.post("/device-templates/{template_id}/sensors", response_model=TemplateSensorSlotRead, status_code=201, tags=["Device Templates"])
async def add_template_sensor(template_id: int, payload: TemplateSensorSlotCreate, db: AsyncSession = Depends(get_db), _: User = Depends(require_permission("device_templates.update"))) -> TemplateSensorSlotRead:
    await _template(db, template_id)
    if await db.get(SensorModel, payload.sensor_model_id) is None: raise HTTPException(422, "SensorModel không tồn tại")
    row = DeviceTemplateSensor(device_template_id=template_id, **payload.model_dump()); db.add(row); await db.commit()
    return _sensor_slot(await _sensor_mapping(db, template_id, row.id))


@router.get("/device-templates/{template_id}/sensors/{mapping_id}", response_model=TemplateSensorSlotRead, tags=["Device Templates"])
async def get_template_sensor(template_id: int, mapping_id: int, db: AsyncSession = Depends(get_db), _: User = Depends(require_permission("device_templates.read"))) -> TemplateSensorSlotRead:
    return _sensor_slot(await _sensor_mapping(db, template_id, mapping_id))


@router.patch("/device-templates/{template_id}/sensors/{mapping_id}", response_model=TemplateSensorSlotRead, tags=["Device Templates"])
async def update_template_sensor(template_id: int, mapping_id: int, payload: TemplateSensorSlotUpdate, db: AsyncSession = Depends(get_db), _: User = Depends(require_permission("device_templates.update"))) -> TemplateSensorSlotRead:
    row = await _sensor_mapping(db, template_id, mapping_id)
    for key, value in payload.model_dump(exclude_unset=True).items(): setattr(row, key, value)
    await db.commit(); return _sensor_slot(await _sensor_mapping(db, template_id, mapping_id))


@router.delete("/device-templates/{template_id}/sensors/{mapping_id}", status_code=204, tags=["Device Templates"])
async def delete_template_sensor(template_id: int, mapping_id: int, db: AsyncSession = Depends(get_db), _: User = Depends(require_permission("device_templates.update"))) -> None:
    await db.delete(await _sensor_mapping(db, template_id, mapping_id)); await db.commit()


@router.get("/device-templates/{template_id}/actuators", response_model=list[TemplateActuatorSlotRead], tags=["Device Templates"])
async def list_template_actuators(template_id: int, db: AsyncSession = Depends(get_db), _: User = Depends(require_permission("device_templates.read"))) -> list[TemplateActuatorSlotRead]:
    return [_actuator_slot(x) for x in (await _template(db, template_id)).actuator_mappings]


@router.post("/device-templates/{template_id}/actuators", response_model=TemplateActuatorSlotRead, status_code=201, tags=["Device Templates"])
async def add_template_actuator(template_id: int, payload: TemplateActuatorSlotCreate, db: AsyncSession = Depends(get_db), _: User = Depends(require_permission("device_templates.update"))) -> TemplateActuatorSlotRead:
    await _template(db, template_id)
    if await db.get(ActuatorModel, payload.actuator_model_id) is None: raise HTTPException(422, "ActuatorModel không tồn tại")
    row = DeviceTemplateActuator(device_template_id=template_id, **payload.model_dump()); db.add(row); await db.commit()
    return _actuator_slot(await _actuator_mapping(db, template_id, row.id))


@router.get("/device-templates/{template_id}/actuators/{mapping_id}", response_model=TemplateActuatorSlotRead, tags=["Device Templates"])
async def get_template_actuator(template_id: int, mapping_id: int, db: AsyncSession = Depends(get_db), _: User = Depends(require_permission("device_templates.read"))) -> TemplateActuatorSlotRead:
    return _actuator_slot(await _actuator_mapping(db, template_id, mapping_id))


@router.patch("/device-templates/{template_id}/actuators/{mapping_id}", response_model=TemplateActuatorSlotRead, tags=["Device Templates"])
async def update_template_actuator(template_id: int, mapping_id: int, payload: TemplateActuatorSlotUpdate, db: AsyncSession = Depends(get_db), _: User = Depends(require_permission("device_templates.update"))) -> TemplateActuatorSlotRead:
    row = await _actuator_mapping(db, template_id, mapping_id)
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(row, key, value)
    await db.commit(); return _actuator_slot(await _actuator_mapping(db, template_id, mapping_id))


@router.delete("/device-templates/{template_id}/actuators/{mapping_id}", status_code=204, tags=["Device Templates"])
async def delete_template_actuator(template_id: int, mapping_id: int, db: AsyncSession = Depends(get_db), _: User = Depends(require_permission("device_templates.update"))) -> None:
    await db.delete(await _actuator_mapping(db, template_id, mapping_id)); await db.commit()


@router.get("/actuator-models", response_model=list[ActuatorModelRead], tags=["Actuator Models"])
async def list_actuator_models(db: AsyncSession = Depends(get_db), _: User = Depends(require_permission("actuator_models.read"))) -> list[ActuatorModel]:
    return list((await db.scalars(select(ActuatorModel).where(ActuatorModel.is_deleted.is_(False)).order_by(ActuatorModel.name))).all())


@router.post("/actuator-models", response_model=ActuatorModelRead, status_code=201, tags=["Actuator Models"])
async def create_actuator_model(payload: ActuatorModelCreate, db: AsyncSession = Depends(get_db), _: User = Depends(require_permission("actuator_models.create"))) -> ActuatorModel:
    if await db.scalar(select(ActuatorModel.id).where(ActuatorModel.code == payload.code)): raise HTTPException(409, "Mã ActuatorModel đã tồn tại")
    row = ActuatorModel(**payload.model_dump()); db.add(row); await db.commit(); await db.refresh(row); return row


async def _actuator_model(db: AsyncSession, model_id: int) -> ActuatorModel:
    row = await db.scalar(select(ActuatorModel).where(ActuatorModel.id == model_id, ActuatorModel.is_deleted.is_(False)))
    if row is None: raise HTTPException(404, "Không tìm thấy ActuatorModel")
    return row


@router.get("/actuator-models/{model_id}", response_model=ActuatorModelRead, tags=["Actuator Models"])
async def get_actuator_model(model_id: int, db: AsyncSession = Depends(get_db), _: User = Depends(require_permission("actuator_models.read"))) -> ActuatorModel:
    return await _actuator_model(db, model_id)


@router.patch("/actuator-models/{model_id}", response_model=ActuatorModelRead, tags=["Actuator Models"])
async def update_actuator_model(model_id: int, payload: ActuatorModelUpdate, db: AsyncSession = Depends(get_db), _: User = Depends(require_permission("actuator_models.update"))) -> ActuatorModel:
    row = await _actuator_model(db, model_id)
    for key, value in payload.model_dump(exclude_unset=True).items(): setattr(row, key, value)
    await db.commit(); await db.refresh(row); return row


@router.delete("/actuator-models/{model_id}", status_code=204, tags=["Actuator Models"])
async def delete_actuator_model(model_id: int, db: AsyncSession = Depends(get_db), _: User = Depends(require_permission("actuator_models.delete"))) -> None:
    row = await _actuator_model(db, model_id); row.is_deleted = True; await db.commit()
