from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import require_roles
from app.db.session import get_db
from app.core.enums import UserRole
from app.models.device import Device
from app.models.device_template import DeviceTemplate, DeviceTemplateActuator, DeviceTemplateSensor
from app.models.actuator_model import ActuatorModel
from app.models.sensor import SensorModel
from app.models.user import User
from app.models.operational_alert import AlertRule, AlertRuleActuatorModelProfile, AlertRuleProfile
from app.schemas.device_template import (
    DeviceTemplateCreate, DeviceTemplateList, DeviceTemplateRead, DeviceTemplateUpdate,
    ActuatorCurrentProfileRead, TemplateSensorInput, TemplateSensorRead, TemplateSensorUpdate,
    TemplateActuatorInput, TemplateActuatorRead, TemplateActuatorUpdate,
)
from app.services.audit_service import write_audit
from app.services.energy_monitor_service import (
    ENERGY_MONITOR_KIND,
    ENERGY_SENSOR_SPEC_BY_MODEL,
    EnergyTemplateValidationError,
    add_missing_energy_sensor_mappings,
    reload_template,
    validate_energy_template,
)

router = APIRouter(prefix="/admin/device-templates", tags=["Admin device templates"])


def serialize_mapping(mapping: DeviceTemplateSensor) -> TemplateSensorRead:
    model = mapping.sensor_model
    return TemplateSensorRead(
        id=mapping.id, sensor_model_id=mapping.sensor_model_id,
        display_name=mapping.display_name, default_location=mapping.default_location,
        default_lower_threshold=mapping.default_lower_threshold,
        default_upper_threshold=mapping.default_upper_threshold, sort_order=mapping.sort_order,
        default_warning_enabled=mapping.default_warning_enabled,
        default_below_threshold_message=mapping.default_below_threshold_message,
        default_above_threshold_message=mapping.default_above_threshold_message,
        default_alert_risk_level=mapping.default_alert_risk_level,
        is_required=mapping.is_required,
        model_code=model.code, model_name=model.name, unit=model.unit,
        value_type=model.value_type, chart_type=model.chart_type,
        measurement_semantics=model.measurement_semantics,
    )


def serialize_template(item: DeviceTemplate) -> DeviceTemplateRead:
    return DeviceTemplateRead(
        id=item.id, code=item.code, name=item.name, description=item.description,
        notes=item.notes, device_kind=item.device_kind,
        nominal_output_voltage_v=item.nominal_output_voltage_v,
        is_active=item.is_active, created_at=item.created_at,
        updated_at=item.updated_at,
        sensors=[serialize_mapping(mapping) for mapping in item.sensor_mappings],
        actuators=[TemplateActuatorRead(
            id=mapping.id, actuator_model_id=mapping.actuator_model_id, code=mapping.code,
            default_name=mapping.default_name, default_location=mapping.default_location,
            default_notes=mapping.default_notes, actuator_type=mapping.actuator_type,
            default_state=mapping.default_state, command_capability=mapping.command_capability,
            monitor_current=mapping.monitor_current, electrical_profile_id=mapping.electrical_profile_id,
            electrical_profile_code=mapping.electrical_profile.code if mapping.electrical_profile else None,
            electrical_profile_name=mapping.electrical_profile.name if mapping.electrical_profile else None,
            sort_order=mapping.sort_order, is_required=mapping.is_required,
            is_enabled=mapping.is_enabled, model_code=mapping.actuator_model.code,
            model_name=mapping.actuator_model.name,
        ) for mapping in item.actuator_mappings],
    )


async def get_template(db: AsyncSession, template_id: int) -> DeviceTemplate:
    item = await db.scalar(
        select(DeviceTemplate)
        .options(
            selectinload(DeviceTemplate.sensor_mappings).selectinload(DeviceTemplateSensor.sensor_model),
            selectinload(DeviceTemplate.actuator_mappings).selectinload(DeviceTemplateActuator.actuator_model),
            selectinload(DeviceTemplate.actuator_mappings).selectinload(DeviceTemplateActuator.electrical_profile),
        )
        .where(DeviceTemplate.id == template_id, DeviceTemplate.is_deleted.is_(False))
    )
    if item is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy mẫu thiết bị")
    return item


@router.get("", response_model=DeviceTemplateList)
async def list_templates(
    q: str = Query(default="", max_length=255), is_active: bool | None = None,
    page: int = Query(default=1, ge=1), page_size: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db), _: User = Depends(require_roles(UserRole.ADMIN)),
) -> DeviceTemplateList:
    query = select(DeviceTemplate).where(DeviceTemplate.is_deleted.is_(False))
    if q.strip():
        pattern = f"%{q.strip()}%"
        query = query.where(or_(DeviceTemplate.code.ilike(pattern), DeviceTemplate.name.ilike(pattern), DeviceTemplate.description.ilike(pattern)))
    if is_active is not None:
        query = query.where(DeviceTemplate.is_active.is_(is_active))
    total = int(await db.scalar(select(func.count()).select_from(query.subquery())) or 0)
    items = list(
        (
            await db.scalars(
                query.options(
                    selectinload(DeviceTemplate.sensor_mappings).selectinload(
                        DeviceTemplateSensor.sensor_model
                    ),
                    selectinload(DeviceTemplate.actuator_mappings).selectinload(
                        DeviceTemplateActuator.actuator_model
                    ),
                    selectinload(DeviceTemplate.actuator_mappings).selectinload(
                        DeviceTemplateActuator.electrical_profile
                    ),
                )
                .order_by(DeviceTemplate.name)
                .offset((page - 1) * page_size)
                .limit(page_size)
            )
        )
        .unique()
        .all()
    )
    return DeviceTemplateList(items=[serialize_template(item) for item in items], total=total, page=page, page_size=page_size)


@router.post("", response_model=DeviceTemplateRead, status_code=201)
async def create_template(payload: DeviceTemplateCreate, db: AsyncSession = Depends(get_db), actor: User = Depends(require_roles(UserRole.ADMIN))) -> DeviceTemplateRead:
    if await db.scalar(select(DeviceTemplate.id).where(DeviceTemplate.code == payload.code)):
        raise HTTPException(status_code=409, detail="Mã mẫu thiết bị đã tồn tại")
    if payload.device_kind == ENERGY_MONITOR_KIND and payload.is_active:
        raise HTTPException(
            status_code=422,
            detail={
                "code": "ENERGY_TEMPLATE_INCOMPLETE",
                "message": "Tạo mẫu năng lượng ở trạng thái tạm ẩn, thêm sáu cảm biến mặc định rồi kích hoạt.",
                "missing_sensor_models": list(ENERGY_SENSOR_SPEC_BY_MODEL),
            },
        )
    item = DeviceTemplate(**payload.model_dump())
    db.add(item)
    await db.flush()
    await write_audit(db, user_id=actor.id, action="CREATE_DEVICE_TEMPLATE", entity_type="DEVICE_TEMPLATE", entity_id=item.id, new_data=payload.model_dump())
    await db.commit()
    return serialize_template(await get_template(db, item.id))


@router.get("/actuator-current-profiles", response_model=list[ActuatorCurrentProfileRead])
async def list_actuator_current_profiles(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_roles(UserRole.ADMIN)),
) -> list[ActuatorCurrentProfileRead]:
    rows = (
        await db.execute(
            select(AlertRuleProfile, AlertRuleActuatorModelProfile.actuator_model_id)
            .join(AlertRule, AlertRule.id == AlertRuleProfile.rule_id)
            .join(AlertRuleActuatorModelProfile, AlertRuleActuatorModelProfile.profile_id == AlertRuleProfile.id)
            .where(AlertRuleProfile.is_enabled.is_(True), AlertRule.evaluator_type.in_(("ACTUATOR_FEEDBACK", "SCHEDULE_FEEDBACK")))
            .order_by(AlertRuleProfile.name, AlertRuleActuatorModelProfile.actuator_model_id)
        )
    ).all()
    grouped: dict[int, ActuatorCurrentProfileRead] = {}
    for profile, actuator_model_id in rows:
        item = grouped.setdefault(profile.id, ActuatorCurrentProfileRead(id=profile.id, code=profile.code, name=profile.name, actuator_model_ids=[]))
        item.actuator_model_ids.append(actuator_model_id)
    return list(grouped.values())


@router.get("/{template_id}", response_model=DeviceTemplateRead)
async def read_template(template_id: int, db: AsyncSession = Depends(get_db), _: User = Depends(require_roles(UserRole.ADMIN))) -> DeviceTemplateRead:
    return serialize_template(await get_template(db, template_id))


@router.patch("/{template_id}", response_model=DeviceTemplateRead)
async def update_template(template_id: int, payload: DeviceTemplateUpdate, db: AsyncSession = Depends(get_db), actor: User = Depends(require_roles(UserRole.ADMIN))) -> DeviceTemplateRead:
    item = await get_template(db, template_id)
    changes = payload.model_dump(exclude_unset=True)
    if "code" in changes and await db.scalar(select(DeviceTemplate.id).where(DeviceTemplate.code == changes["code"], DeviceTemplate.id != item.id)):
        raise HTTPException(status_code=409, detail="Mã mẫu thiết bị đã tồn tại")
    if "device_kind" in changes and changes["device_kind"] != item.device_kind:
        used = await db.scalar(
            select(func.count(Device.id)).where(
                Device.device_template_id == item.id,
                Device.is_deleted.is_(False),
            )
        )
        if used:
            raise HTTPException(
                status_code=409,
                detail={
                    "code": "DEVICE_KIND_IN_USE",
                    "message": "Không thể đổi loại mẫu đang được thiết bị sử dụng.",
                },
            )
    for key, value in changes.items():
        setattr(item, key, value)
    if item.is_active and item.device_kind == ENERGY_MONITOR_KIND:
        try:
            validate_energy_template(item)
        except EnergyTemplateValidationError as exc:
            raise HTTPException(status_code=422, detail=exc.detail) from exc
    await write_audit(db, user_id=actor.id, action="UPDATE_DEVICE_TEMPLATE", entity_type="DEVICE_TEMPLATE", entity_id=item.id, new_data=changes)
    await db.commit()
    return serialize_template(await get_template(db, item.id))


@router.delete("/{template_id}", status_code=204)
async def delete_template(template_id: int, db: AsyncSession = Depends(get_db), actor: User = Depends(require_roles(UserRole.ADMIN))) -> Response:
    item = await get_template(db, template_id)
    item.is_deleted = True
    item.deleted_at = datetime.now(UTC)
    await write_audit(db, user_id=actor.id, action="DELETE_DEVICE_TEMPLATE", entity_type="DEVICE_TEMPLATE", entity_id=item.id)
    await db.commit()
    return Response(status_code=204)


@router.post("/{template_id}/sensors", response_model=TemplateSensorRead, status_code=201)
async def add_template_sensor(template_id: int, payload: TemplateSensorInput, db: AsyncSession = Depends(get_db), actor: User = Depends(require_roles(UserRole.ADMIN))) -> TemplateSensorRead:
    await get_template(db, template_id)
    model = await db.scalar(select(SensorModel).where(SensorModel.id == payload.sensor_model_id, SensorModel.is_deleted.is_(False)))
    if model is None:
        raise HTTPException(status_code=404, detail="Sensor model không tồn tại hoặc đã bị vô hiệu hóa.")
    if not model.is_active:
        raise HTTPException(status_code=404, detail="Sensor model không tồn tại hoặc đã bị vô hiệu hóa.")
    if await db.scalar(select(DeviceTemplateSensor.id).where(DeviceTemplateSensor.device_template_id == template_id, DeviceTemplateSensor.sensor_model_id == payload.sensor_model_id)):
        raise HTTPException(status_code=409, detail=f"SensorModel {model.code} đã được thêm vào mẫu thiết bị này.")
    template = await get_template(db, template_id)
    if template.device_kind == ENERGY_MONITOR_KIND:
        spec = ENERGY_SENSOR_SPEC_BY_MODEL.get(model.code)
        if spec is None:
            raise HTTPException(status_code=422, detail="Mẫu ENERGY_MONITOR chỉ hỗ trợ sáu phép đo chuẩn.")
        payload = payload.model_copy(
            update={
                "display_name": spec.name,
                "sort_order": spec.sort_order,
                "is_required": True,
            }
        )
    mapping = DeviceTemplateSensor(device_template_id=template_id, **payload.model_dump())
    db.add(mapping)
    await db.flush()
    await write_audit(db, user_id=actor.id, action="ADD_TEMPLATE_SENSOR", entity_type="DEVICE_TEMPLATE", entity_id=template_id, new_data=payload.model_dump())
    await db.commit()
    mapping = await db.scalar(select(DeviceTemplateSensor).options(selectinload(DeviceTemplateSensor.sensor_model)).where(DeviceTemplateSensor.id == mapping.id))
    return serialize_mapping(mapping)


@router.patch("/{template_id}/sensors/{mapping_id}", response_model=TemplateSensorRead)
async def update_template_sensor(template_id: int, mapping_id: int, payload: TemplateSensorUpdate, db: AsyncSession = Depends(get_db), actor: User = Depends(require_roles(UserRole.ADMIN))) -> TemplateSensorRead:
    mapping = await db.scalar(select(DeviceTemplateSensor).options(selectinload(DeviceTemplateSensor.sensor_model)).where(DeviceTemplateSensor.id == mapping_id, DeviceTemplateSensor.device_template_id == template_id))
    if mapping is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy cảm biến trong mẫu")
    changes = payload.model_dump(exclude_unset=True)
    resolved_lower = changes.get("default_lower_threshold", mapping.default_lower_threshold)
    resolved_upper = changes.get("default_upper_threshold", mapping.default_upper_threshold)
    if (
        resolved_lower is not None
        and resolved_upper is not None
        and resolved_lower >= resolved_upper
    ):
        raise HTTPException(status_code=422, detail="Ngưỡng dưới phải nhỏ hơn ngưỡng trên")
    template = await get_template(db, template_id)
    if template.device_kind == ENERGY_MONITOR_KIND:
        spec = ENERGY_SENSOR_SPEC_BY_MODEL.get(mapping.sensor_model.code)
        if spec is None:
            raise HTTPException(status_code=422, detail="Mapping Energy Monitor không thuộc bộ sáu phép đo chuẩn.")
        if (
            ("is_required" in changes and not changes["is_required"])
            or ("display_name" in changes and changes["display_name"] != spec.name)
            or ("sort_order" in changes and changes["sort_order"] != spec.sort_order)
        ):
            raise HTTPException(
                status_code=422,
                detail="Tên, thứ tự và trạng thái bắt buộc của phép đo chuẩn Energy Monitor không thể thay đổi.",
            )
    for key, value in changes.items():
        setattr(mapping, key, value)
    await write_audit(db, user_id=actor.id, action="UPDATE_TEMPLATE_SENSOR", entity_type="DEVICE_TEMPLATE", entity_id=template_id, new_data={"mapping_id": mapping_id, **changes})
    await db.commit()
    await db.refresh(mapping)
    return serialize_mapping(mapping)


@router.delete("/{template_id}/sensors/{mapping_id}", status_code=204)
async def delete_template_sensor(template_id: int, mapping_id: int, db: AsyncSession = Depends(get_db), actor: User = Depends(require_roles(UserRole.ADMIN))) -> Response:
    template = await get_template(db, template_id)
    mapping = next((item for item in template.sensor_mappings if item.id == mapping_id), None)
    if mapping is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy cảm biến trong mẫu")
    if (
        template.device_kind == ENERGY_MONITOR_KIND
        and mapping.sensor_model.code in ENERGY_SENSOR_SPEC_BY_MODEL
    ):
        raise HTTPException(
            status_code=422,
            detail={
                "code": "ENERGY_TEMPLATE_INCOMPLETE",
                "message": "Không thể xóa phép đo bắt buộc của ENERGY_MONITOR_12V.",
                "missing_sensor_models": [mapping.sensor_model.code],
            },
        )
    await db.delete(mapping)
    await write_audit(db, user_id=actor.id, action="DELETE_TEMPLATE_SENSOR", entity_type="DEVICE_TEMPLATE", entity_id=template_id, old_data={"mapping_id": mapping_id})
    await db.commit()
    return Response(status_code=204)


@router.post(
    "/{template_id}/energy-default-sensors",
    response_model=DeviceTemplateRead,
)
async def add_energy_default_sensors(
    template_id: int,
    db: AsyncSession = Depends(get_db),
    actor: User = Depends(require_roles(UserRole.ADMIN)),
) -> DeviceTemplateRead:
    template = await get_template(db, template_id)
    if template.device_kind != ENERGY_MONITOR_KIND:
        raise HTTPException(status_code=422, detail="Chỉ áp dụng cho mẫu thiết bị năng lượng")
    created = await add_missing_energy_sensor_mappings(db, template)
    await write_audit(
        db,
        user_id=actor.id,
        action="ADD_ENERGY_TEMPLATE_DEFAULT_SENSORS",
        entity_type="DEVICE_TEMPLATE",
        entity_id=template.id,
        new_data={
            "device_kind": ENERGY_MONITOR_KIND,
            "sensor_model_codes": [
                mapping.sensor_model_id for mapping in created
            ],
        },
    )
    await db.commit()
    refreshed = await reload_template(db, template.id)
    if refreshed is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy mẫu thiết bị")
    return serialize_template(refreshed)


@router.post("/{template_id}/actuators", response_model=TemplateActuatorRead, status_code=201)
async def add_template_actuator(template_id: int, payload: TemplateActuatorInput, db: AsyncSession = Depends(get_db), actor: User = Depends(require_roles(UserRole.ADMIN))) -> TemplateActuatorRead:
    await get_template(db, template_id)
    model = await db.scalar(select(ActuatorModel).where(
        ActuatorModel.id == payload.actuator_model_id,
        ActuatorModel.is_deleted.is_(False), ActuatorModel.is_active.is_(True),
    ))
    if model is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy mẫu cơ cấu chấp hành đang hoạt động")
    duplicate = await db.scalar(select(DeviceTemplateActuator.id).where(
        DeviceTemplateActuator.device_template_id == template_id,
        DeviceTemplateActuator.code == payload.code,
    ))
    if duplicate is not None:
        raise HTTPException(status_code=409, detail="Mã cơ cấu chấp hành đã tồn tại trong mẫu thiết bị")
    await _validate_actuator_profile(db, payload.actuator_model_id, payload.monitor_current, payload.electrical_profile_id)
    mapping = DeviceTemplateActuator(device_template_id=template_id, **payload.model_dump())
    db.add(mapping)
    await db.flush()
    await write_audit(db, user_id=actor.id, action="ADD_TEMPLATE_ACTUATOR", entity_type="DEVICE_TEMPLATE", entity_id=template_id, new_data=payload.model_dump())
    await db.commit()
    return _serialize_actuator_mapping(await _actuator_mapping(db, template_id, mapping.id))


def _serialize_actuator_mapping(mapping: DeviceTemplateActuator, model: ActuatorModel | None = None) -> TemplateActuatorRead:
    model = model or mapping.actuator_model
    return TemplateActuatorRead(
        id=mapping.id, actuator_model_id=mapping.actuator_model_id, code=mapping.code,
        default_name=mapping.default_name, default_location=mapping.default_location,
        default_notes=mapping.default_notes, actuator_type=mapping.actuator_type,
        default_state=mapping.default_state, command_capability=mapping.command_capability,
        monitor_current=mapping.monitor_current, electrical_profile_id=mapping.electrical_profile_id,
        electrical_profile_code=mapping.electrical_profile.code if mapping.electrical_profile else None,
        electrical_profile_name=mapping.electrical_profile.name if mapping.electrical_profile else None,
        sort_order=mapping.sort_order, is_required=mapping.is_required, is_enabled=mapping.is_enabled,
        model_code=model.code, model_name=model.name,
    )


async def _actuator_mapping(db: AsyncSession, template_id: int, mapping_id: int) -> DeviceTemplateActuator:
    mapping = await db.scalar(
        select(DeviceTemplateActuator)
        .options(
            selectinload(DeviceTemplateActuator.actuator_model),
            selectinload(DeviceTemplateActuator.electrical_profile),
        )
        .where(DeviceTemplateActuator.id == mapping_id, DeviceTemplateActuator.device_template_id == template_id)
    )
    if mapping is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy cơ cấu chấp hành trong mẫu thiết bị")
    return mapping


async def _validate_actuator_profile(db: AsyncSession, actuator_model_id: int, monitor_current: bool, profile_id: int | None) -> None:
    if profile_id is None:
        return
    if not monitor_current:
        raise HTTPException(status_code=422, detail="Chỉ chọn Profile điện khi bật giám sát dòng điện")
    profile = await db.scalar(
        select(AlertRuleProfile.id)
        .join(AlertRule, AlertRule.id == AlertRuleProfile.rule_id)
        .join(AlertRuleActuatorModelProfile, AlertRuleActuatorModelProfile.profile_id == AlertRuleProfile.id)
        .where(
            AlertRuleProfile.id == profile_id,
            AlertRuleProfile.is_enabled.is_(True),
            AlertRuleActuatorModelProfile.actuator_model_id == actuator_model_id,
            AlertRule.evaluator_type.in_(("ACTUATOR_FEEDBACK", "SCHEDULE_FEEDBACK")),
        )
    )
    if profile is None:
        raise HTTPException(status_code=422, detail="Profile điện không hợp lệ với Model cơ cấu chấp hành đã chọn")


@router.get("/{template_id}/actuators", response_model=list[TemplateActuatorRead])
async def list_template_actuators(template_id: int, db: AsyncSession = Depends(get_db), _: User = Depends(require_roles(UserRole.ADMIN))) -> list[TemplateActuatorRead]:
    template = await get_template(db, template_id)
    return [_serialize_actuator_mapping(mapping) for mapping in template.actuator_mappings]


@router.get("/{template_id}/actuators/{mapping_id}", response_model=TemplateActuatorRead)
async def read_template_actuator(template_id: int, mapping_id: int, db: AsyncSession = Depends(get_db), _: User = Depends(require_roles(UserRole.ADMIN))) -> TemplateActuatorRead:
    return _serialize_actuator_mapping(await _actuator_mapping(db, template_id, mapping_id))


@router.patch("/{template_id}/actuators/{mapping_id}", response_model=TemplateActuatorRead)
async def update_template_actuator(template_id: int, mapping_id: int, payload: TemplateActuatorUpdate, db: AsyncSession = Depends(get_db), actor: User = Depends(require_roles(UserRole.ADMIN))) -> TemplateActuatorRead:
    mapping = await _actuator_mapping(db, template_id, mapping_id)
    changes = payload.model_dump(exclude_unset=True)
    if "code" in changes and await db.scalar(select(DeviceTemplateActuator.id).where(DeviceTemplateActuator.device_template_id == template_id, DeviceTemplateActuator.code == changes["code"], DeviceTemplateActuator.id != mapping_id)):
        raise HTTPException(status_code=409, detail="Mã cơ cấu chấp hành đã tồn tại trong mẫu thiết bị")
    monitor_current = changes.get("monitor_current", mapping.monitor_current)
    profile_id = changes.get("electrical_profile_id", mapping.electrical_profile_id)
    await _validate_actuator_profile(db, mapping.actuator_model_id, monitor_current, profile_id)
    if not monitor_current:
        changes["electrical_profile_id"] = None
    for field, value in changes.items():
        setattr(mapping, field, value)
    await write_audit(db, user_id=actor.id, action="UPDATE_TEMPLATE_ACTUATOR", entity_type="DEVICE_TEMPLATE", entity_id=template_id, new_data={"mapping_id": mapping_id, **changes})
    await db.commit()
    return _serialize_actuator_mapping(await _actuator_mapping(db, template_id, mapping_id))


@router.delete("/{template_id}/actuators/{mapping_id}", status_code=204)
async def delete_template_actuator(template_id: int, mapping_id: int, db: AsyncSession = Depends(get_db), actor: User = Depends(require_roles(UserRole.ADMIN))) -> Response:
    mapping = await _actuator_mapping(db, template_id, mapping_id)
    await db.delete(mapping)
    await write_audit(db, user_id=actor.id, action="DELETE_TEMPLATE_ACTUATOR", entity_type="DEVICE_TEMPLATE", entity_id=template_id, old_data={"mapping_id": mapping_id, "code": mapping.code})
    await db.commit()
    return Response(status_code=204)
