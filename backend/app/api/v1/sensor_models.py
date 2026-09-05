from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_operational_user, require_roles
from app.db.session import get_db
from app.core.enums import UserRole
from app.models.sensor import Sensor, SensorModel
from app.models.user import User
from app.schemas.common import MessageResponse
from app.schemas.sensor import SensorModelCreate, SensorModelRead, SensorModelUpdate
from app.services.audit_service import write_audit

router = APIRouter(prefix="/sensor-models", tags=["Sensor models"])


async def get_model_or_404(
    db: AsyncSession, model_id: int, include_deleted: bool = False
) -> SensorModel:
    query = select(SensorModel).where(SensorModel.id == model_id)
    if not include_deleted:
        query = query.where(SensorModel.is_deleted.is_(False))
    model = await db.scalar(query)
    if model is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy mẫu cảm biến")
    return model


@router.get("", response_model=list[SensorModelRead])
async def list_sensor_models(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_operational_user),
) -> list[SensorModel]:
    return list(
        (
            await db.scalars(
                select(SensorModel)
                .where(SensorModel.is_deleted.is_(False))
                .order_by(SensorModel.name)
            )
        ).all()
    )


@router.post("", response_model=SensorModelRead, status_code=201)
async def create_sensor_model(
    payload: SensorModelCreate,
    db: AsyncSession = Depends(get_db),
    actor: User = Depends(require_roles(UserRole.ADMIN)),
) -> SensorModel:
    exists = await db.scalar(select(SensorModel.id).where(SensorModel.code == payload.code))
    if exists:
        raise HTTPException(status_code=409, detail="Mã mẫu cảm biến đã tồn tại")
    model = SensorModel(**payload.model_dump())
    db.add(model)
    await db.flush()
    await write_audit(
        db,
        user_id=actor.id,
        action="CREATE_SENSOR_MODEL",
        entity_type="SENSOR_MODEL",
        entity_id=model.id,
        new_data=payload.model_dump(),
    )
    await db.commit()
    await db.refresh(model)
    return model


@router.get("/{model_id}", response_model=SensorModelRead)
async def get_sensor_model(
    model_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_operational_user),
) -> SensorModel:
    return await get_model_or_404(db, model_id)


@router.patch("/{model_id}", response_model=SensorModelRead)
async def update_sensor_model(
    model_id: int,
    payload: SensorModelUpdate,
    db: AsyncSession = Depends(get_db),
    actor: User = Depends(require_roles(UserRole.ADMIN)),
) -> SensorModel:
    model = await get_model_or_404(db, model_id)
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(model, key, value)
    await write_audit(
        db,
        user_id=actor.id,
        action="UPDATE_SENSOR_MODEL",
        entity_type="SENSOR_MODEL",
        entity_id=model.id,
        new_data=payload.model_dump(exclude_unset=True),
    )
    await db.commit()
    await db.refresh(model)
    return model


@router.delete("/{model_id}", status_code=204)
async def delete_sensor_model(
    model_id: int,
    db: AsyncSession = Depends(get_db),
    actor: User = Depends(require_roles(UserRole.ADMIN)),
) -> Response:
    model = await get_model_or_404(db, model_id)
    sensor_count = await db.scalar(
        select(func.count(Sensor.id)).where(
            Sensor.sensor_model_id == model.id,
            Sensor.is_deleted.is_(False),
        )
    )
    if sensor_count:
        raise HTTPException(status_code=409, detail="Mẫu đang được sử dụng bởi cảm biến")
    model.is_deleted = True
    model.deleted_at = datetime.now(UTC)
    await write_audit(
        db,
        user_id=actor.id,
        action="DELETE_SENSOR_MODEL",
        entity_type="SENSOR_MODEL",
        entity_id=model.id,
    )
    await db.commit()
    return Response(status_code=204)


@router.post("/{model_id}/restore", response_model=MessageResponse)
async def restore_sensor_model(
    model_id: int,
    db: AsyncSession = Depends(get_db),
    actor: User = Depends(require_roles(UserRole.ADMIN)),
) -> MessageResponse:
    model = await get_model_or_404(db, model_id, include_deleted=True)
    model.is_deleted = False
    model.deleted_at = None
    await write_audit(
        db,
        user_id=actor.id,
        action="RESTORE_SENSOR_MODEL",
        entity_type="SENSOR_MODEL",
        entity_id=model.id,
    )
    await db.commit()
    return MessageResponse(message="Đã khôi phục mẫu cảm biến")
