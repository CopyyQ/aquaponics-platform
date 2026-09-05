from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_operational_user, require_roles
from app.db.session import get_db
from app.core.enums import DeviceStatus, ProjectStatus, UserRole, UserStatus
from app.core.config import settings
from app.models.device import Device
from app.models.device_template import DeviceTemplate
from app.models.project import Project
from app.models.sensor import Sensor, SensorModel
from app.models.user import User
from app.schemas.common import MessageResponse
from app.schemas.device import DeviceRead, DeviceUpdate
from pydantic import BaseModel
from app.services.audit_service import write_audit
from app.services.access_service import active_project_clause, require_device_access, scope_devices

router = APIRouter(prefix="/devices", tags=["Devices"])


class DeviceProjectUpdate(BaseModel):
    project_id: int


async def get_device_or_404(db: AsyncSession, device_id: int, include_deleted: bool = False) -> Device:
    query = select(Device).join(Project, Project.id == Device.project_id).where(Device.id == device_id)
    if not include_deleted:
        query = query.where(Device.is_deleted.is_(False), active_project_clause(Project))
    device = await db.scalar(query)
    if device is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy thiết bị")
    return device


@router.get("", response_model=list[DeviceRead])
async def list_devices(
    db: AsyncSession = Depends(get_db),
    actor: User = Depends(get_current_operational_user),
) -> list[Device]:
    query = select(Device).where(Device.is_deleted.is_(False)).order_by(Device.created_at.desc())
    return list(
        (await db.scalars(scope_devices(query, actor))).all()
    )


@router.get("/{device_id}", response_model=DeviceRead)
async def get_device(
    device_id: int,
    db: AsyncSession = Depends(get_db),
    actor: User = Depends(get_current_operational_user),
) -> Device:
    return await require_device_access(db, device_id, actor)


@router.get("/{device_id}/overview")
async def device_overview(
    device_id: int,
    db: AsyncSession = Depends(get_db),
    actor: User = Depends(get_current_operational_user),
) -> dict:
    device = await require_device_access(
        db, device_id, actor, allow_disabled=actor.system_role == UserRole.ADMIN
    )
    sensors = list(
        (
            await db.scalars(
                select(Sensor)
                .where(
                    Sensor.device_id == device.id,
                    Sensor.is_enabled.is_(True),
                    Sensor.is_deleted.is_(False),
                    Sensor.deleted_at.is_(None),
                )
                .order_by(Sensor.name)
            )
        ).all()
    )
    project = await db.get(Project, device.project_id)
    template = await db.get(DeviceTemplate, device.device_template_id) if device.device_template_id else None
    owner = await db.get(User, project.owner_user_id) if project else None
    return {
        "device": {
            **DeviceRead.model_validate(device).model_dump(mode="json"),
            "device_kind": template.device_kind if template else "GENERIC",
            "template_code": template.code if template else None,
            "template_name": template.name if template else None,
            "nominal_output_voltage_v": template.nominal_output_voltage_v if template else None,
        },
        "owner": {"id": owner.id, "full_name": owner.full_name} if owner else None,
        "project": {"id": project.id, "name": project.name} if project else None,
        "sensors": [
            {
                "id": sensor.id,
                "code": sensor.code,
                "name": sensor.name,
                "status": sensor.status,
                "last_seen_at": sensor.last_seen_at,
                "lower_threshold": sensor.lower_threshold,
                "upper_threshold": sensor.upper_threshold,
            }
            for sensor in sensors
        ],
        "last_received_at": device.last_seen_at,
    }


@router.get("/{device_id}/mqtt-config")
async def mqtt_config(
    device_id: int,
    db: AsyncSession = Depends(get_db),
    actor: User = Depends(get_current_operational_user),
) -> dict:
    if actor.system_role == UserRole.ADMIN:
        context_row = (
            await db.execute(
                select(Device, Project, User)
                .join(Project, Project.id == Device.project_id)
                .join(User, User.id == Project.owner_user_id)
                .where(Device.id == device_id)
            )
        ).first()
        if context_row is not None:
            context_device, context_project, context_owner = context_row
            if (
                context_owner.status != UserStatus.ACTIVE
                or context_owner.is_deleted
                or context_owner.deleted_at is not None
            ):
                raise HTTPException(
                    status_code=409,
                    detail={
                        "code": "PROJECT_OWNER_INACTIVE",
                        "detail": "Không thể tải cấu hình vì tài khoản chủ dự án không hoạt động.",
                    },
                )
            if (
                context_project.status != ProjectStatus.ACTIVE
                or context_project.is_deleted
                or context_project.deleted_at is not None
                or context_device.status == DeviceStatus.DISABLED
            ):
                raise HTTPException(
                    status_code=409,
                    detail={
                        "code": "PROJECT_INACTIVE",
                        "detail": "Không thể tải cấu hình MQTT vì dự án hoặc thiết bị không hoạt động.",
                    },
                )
    device = await require_device_access(db, device_id, actor)
    project = await db.get(Project, device.project_id)
    if project is None or project.status != ProjectStatus.ACTIVE:
        raise HTTPException(status_code=400, detail="Không thể tải cấu hình MQTT vì dự án không hoạt động")
    owner = await db.get(User, project.owner_user_id)
    sensors = list((await db.execute(select(Sensor, SensorModel).join(SensorModel, SensorModel.id == Sensor.sensor_model_id).where(Sensor.device_id == device.id, Sensor.is_deleted.is_(False), Sensor.deleted_at.is_(None), Sensor.is_enabled.is_(True)).order_by(Sensor.name))).all())
    return {
        "project": {"id": project.id, "code": project.code, "name": project.name, "owner": {"id": owner.id, "full_name": owner.full_name} if owner else None},
        "device": {"id": device.id, "code": device.code, "name": device.name},
        "mqtt": {
            "host": settings.mqtt_public_host, "port": settings.mqtt_port,
            "authentication": False, "tls": False,
            "telemetry_topic": f"aquaponics/{device.code}/telemetry",
            "status_topic": f"aquaponics/{device.code}/status",
        },
        "topics": {"telemetry": f"aquaponics/{device.code}/telemetry", "status": f"aquaponics/{device.code}/status"},
        "sensors": [{"sensor_code": sensor.code, "name": sensor.name, "unit": model.unit} for sensor, model in sensors],
    }


@router.patch("/{device_id}/project", response_model=DeviceRead)
async def move_device_project(
    device_id: int,
    payload: DeviceProjectUpdate,
    db: AsyncSession = Depends(get_db),
    actor: User = Depends(require_roles(UserRole.ADMIN)),
) -> Device:
    device = await get_device_or_404(db, device_id)
    project = await db.scalar(
        select(Project).where(
            Project.id == payload.project_id,
            active_project_clause(Project),
        )
    )
    if project is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy Project đích")
    old_project_id = device.project_id
    device.project_id = project.id
    await write_audit(db, user_id=actor.id, action="MOVE_DEVICE_PROJECT", entity_type="DEVICE", entity_id=device.id, old_data={"project_id": old_project_id}, new_data={"project_id": project.id})
    await db.commit()
    await db.refresh(device)
    return device


@router.patch("/{device_id}", response_model=DeviceRead)
async def update_device(
    device_id: int,
    payload: DeviceUpdate,
    db: AsyncSession = Depends(get_db),
    actor: User = Depends(require_roles(UserRole.ADMIN)),
) -> Device:
    device = await get_device_or_404(db, device_id)
    changes = payload.model_dump(exclude_unset=True)
    if "project_id" in changes:
        project = await db.scalar(
            select(Project).where(
                Project.id == changes["project_id"], active_project_clause(Project)
            )
        )
        if project is None:
            raise HTTPException(status_code=404, detail="Không tìm thấy dự án đích")
    old_data = {"name": device.name, "description": device.description, "status": device.status.value}
    for key, value in changes.items():
        setattr(device, key, value)
    await write_audit(
        db,
        user_id=actor.id,
        action="UPDATE_DEVICE",
        entity_type="DEVICE",
        entity_id=device.id,
        old_data=old_data,
        new_data=payload.model_dump(exclude_unset=True, mode="json"),
    )
    await db.commit()
    await db.refresh(device)
    return device


@router.delete("/{device_id}", status_code=204)
async def delete_device(
    device_id: int,
    db: AsyncSession = Depends(get_db),
    actor: User = Depends(require_roles(UserRole.ADMIN)),
) -> Response:
    device = await get_device_or_404(db, device_id)
    device.is_deleted = True
    device.deleted_at = datetime.now(UTC)
    await write_audit(db, user_id=actor.id, action="DELETE_DEVICE", entity_type="DEVICE", entity_id=device.id)
    await db.commit()
    return Response(status_code=204)


@router.post("/{device_id}/restore", response_model=MessageResponse)
async def restore_device(
    device_id: int,
    db: AsyncSession = Depends(get_db),
    actor: User = Depends(require_roles(UserRole.ADMIN)),
) -> MessageResponse:
    device = await get_device_or_404(db, device_id, include_deleted=True)
    device.is_deleted = False
    device.deleted_at = None
    await write_audit(db, user_id=actor.id, action="RESTORE_DEVICE", entity_type="DEVICE", entity_id=device.id)
    await db.commit()
    return MessageResponse(message="Đã khôi phục thiết bị")
