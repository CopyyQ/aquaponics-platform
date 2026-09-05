from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_current_operational_user, require_roles
from app.core.enums import UserRole
from app.db.session import get_db
from app.models.actuator_model import ActuatorModel, ActuatorModelFeedbackDefinition
from app.models.sensor_model import SensorModel
from app.models.user import User
from app.schemas.actuator_model import ActuatorModelCreate, ActuatorModelFeedbackInput, ActuatorModelFeedbackRead, ActuatorModelRead, ActuatorModelUpdate
from app.services.audit_service import write_audit

router = APIRouter(prefix="/admin/actuator-models", tags=["Admin actuator models"])


async def _get(db: AsyncSession, model_id: int, include_deleted: bool = False) -> ActuatorModel:
    query = select(ActuatorModel).options(selectinload(ActuatorModel.feedback_definitions).selectinload(ActuatorModelFeedbackDefinition.sensor_model)).where(ActuatorModel.id == model_id)
    if not include_deleted:
        query = query.where(ActuatorModel.is_deleted.is_(False))
    model = await db.scalar(query)
    if model is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy mẫu cơ cấu chấp hành")
    return model


def _serialize(model: ActuatorModel) -> ActuatorModelRead:
    return ActuatorModelRead(
        id=model.id, code=model.code, name=model.name, description=model.description,
        data_type=model.data_type, default_state=model.default_state, is_active=model.is_active,
        sort_order=model.sort_order, is_deleted=model.is_deleted,
        created_at=model.created_at, updated_at=model.updated_at,
        feedbacks=[ActuatorModelFeedbackRead(
            id=item.id, feedback_role=item.feedback_role, sensor_model_id=item.sensor_model_id,
            value_key=item.value_key, unit=item.unit, data_type=item.data_type,
            default_lower_threshold=item.default_lower_threshold,
            default_upper_threshold=item.default_upper_threshold,
            is_required=item.is_required, is_enabled=item.is_enabled, display_order=item.display_order,
            sensor_model_code=item.sensor_model.code, sensor_model_name=item.sensor_model.name,
        ) for item in model.feedback_definitions],
    )


async def _validate_feedbacks(db: AsyncSession, feedbacks: list[ActuatorModelFeedbackInput]) -> None:
    roles = [item.feedback_role for item in feedbacks]
    if len(roles) != len(set(roles)):
        raise HTTPException(status_code=422, detail="Mỗi loại dữ liệu phản hồi chỉ được cấu hình một lần")
    for item in feedbacks:
        sensor_model = await db.scalar(select(SensorModel).where(SensorModel.id == item.sensor_model_id, SensorModel.is_active.is_(True), SensorModel.is_deleted.is_(False)))
        if sensor_model is None:
            raise HTTPException(status_code=422, detail="Sensor Model phản hồi không khả dụng")
        required_unit = {"RUNNING_CURRENT": "A", "SUPPLY_VOLTAGE": "V"}[item.feedback_role]
        if sensor_model.unit != required_unit or sensor_model.value_type != "NUMBER" or sensor_model.measurement_semantics != "GAUGE":
            label = "Dòng điện hoạt động" if item.feedback_role == "RUNNING_CURRENT" else "Điện áp cấp"
            raise HTTPException(status_code=422, detail=f"{label} cần Sensor Model số thực dạng GAUGE, đơn vị {required_unit}")
        if item.unit != sensor_model.unit:
            raise HTTPException(status_code=422, detail=f"Đơn vị phải khớp Sensor Model ({sensor_model.unit})")


async def _default_electrical_feedbacks(db: AsyncSession) -> list[ActuatorModelFeedbackInput]:
    models = {
        item.code: item
        for item in (await db.scalars(select(SensorModel).where(
            SensorModel.code.in_(("OUTPUT_VOLTAGE_V", "LOAD_CURRENT_A")),
            SensorModel.is_active.is_(True),
            SensorModel.is_deleted.is_(False),
        ))).all()
    }
    if set(models) != {"OUTPUT_VOLTAGE_V", "LOAD_CURRENT_A"}:
        raise HTTPException(status_code=422, detail="Thiếu mẫu cảm biến điện áp hoặc dòng điện chuẩn")
    return [
        ActuatorModelFeedbackInput(feedback_role="SUPPLY_VOLTAGE", sensor_model_id=models["OUTPUT_VOLTAGE_V"].id, value_key="voltage_v", unit="V", display_order=0),
        ActuatorModelFeedbackInput(feedback_role="RUNNING_CURRENT", sensor_model_id=models["LOAD_CURRENT_A"].id, value_key="current_a", unit="A", display_order=1),
    ]


@router.get("", response_model=list[ActuatorModelRead])
async def list_models(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_operational_user),
) -> list[ActuatorModelRead]:
    models = list((await db.scalars(select(ActuatorModel).options(selectinload(ActuatorModel.feedback_definitions).selectinload(ActuatorModelFeedbackDefinition.sensor_model)).where(ActuatorModel.is_deleted.is_(False)).order_by(ActuatorModel.sort_order, ActuatorModel.name))).all())
    return [_serialize(model) for model in models]


@router.post("", response_model=ActuatorModelRead, status_code=201)
async def create_model(
    payload: ActuatorModelCreate,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_roles(UserRole.ADMIN)),
) -> ActuatorModelRead:
    if await db.scalar(select(ActuatorModel.id).where(ActuatorModel.code == payload.code, ActuatorModel.is_deleted.is_(False))):
        raise HTTPException(status_code=409, detail="Mã mẫu cơ cấu chấp hành đã tồn tại")
    feedbacks = payload.feedbacks if "feedbacks" in payload.model_fields_set else await _default_electrical_feedbacks(db)
    await _validate_feedbacks(db, feedbacks)
    model = ActuatorModel(**payload.model_dump(exclude={"feedbacks"}))
    db.add(model)
    await db.flush()
    db.add_all(
        ActuatorModelFeedbackDefinition(
            actuator_model_id=model.id,
            **item.model_dump(),
        )
        for item in feedbacks
    )
    await write_audit(db, user_id=admin.id, action="CREATE_ACTUATOR_MODEL", entity_type="ACTUATOR_MODEL", entity_id=model.id, new_data=payload.model_dump())
    await db.commit()
    return _serialize(await _get(db, model.id))


@router.get("/{model_id}", response_model=ActuatorModelRead)
async def get_model(model_id: int, db: AsyncSession = Depends(get_db), _: User = Depends(get_current_operational_user)) -> ActuatorModelRead:
    return _serialize(await _get(db, model_id))


@router.patch("/{model_id}", response_model=ActuatorModelRead)
async def update_model(
    model_id: int,
    payload: ActuatorModelUpdate,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_roles(UserRole.ADMIN)),
) -> ActuatorModelRead:
    model = await _get(db, model_id)
    changes = payload.model_dump(exclude_unset=True)
    feedback_values = changes.pop("feedbacks", None)
    for key, value in changes.items():
        setattr(model, key, value)
    if feedback_values is not None:
        feedbacks = [ActuatorModelFeedbackInput.model_validate(item) for item in feedback_values]
        await _validate_feedbacks(db, feedbacks)
        model.feedback_definitions.clear()
        await db.flush()
        model.feedback_definitions.extend(ActuatorModelFeedbackDefinition(**item.model_dump()) for item in feedbacks)
    await write_audit(db, user_id=admin.id, action="UPDATE_ACTUATOR_MODEL", entity_type="ACTUATOR_MODEL", entity_id=model.id, new_data=payload.model_dump(exclude_unset=True))
    await db.commit()
    return _serialize(await _get(db, model.id))


@router.post("/{model_id}/disable", status_code=204)
async def disable_model(model_id: int, db: AsyncSession = Depends(get_db), admin: User = Depends(require_roles(UserRole.ADMIN))) -> Response:
    model = await _get(db, model_id)
    model.is_active = False
    await db.commit()
    return Response(status_code=204)


@router.post("/{model_id}/activate", status_code=204)
async def activate_model(model_id: int, db: AsyncSession = Depends(get_db), admin: User = Depends(require_roles(UserRole.ADMIN))) -> Response:
    model = await _get(db, model_id, include_deleted=True)
    model.is_deleted = False
    model.deleted_at = None
    model.is_active = True
    await db.commit()
    return Response(status_code=204)
