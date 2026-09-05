import asyncio
from collections import defaultdict
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_admin
from app.core.enums import DeviceStatus, ProjectStatus
from app.db.session import get_db
from app.models.actuator import Actuator, ActuatorCommand
from app.models.actuator_model import ActuatorModel, ActuatorModelFeedbackDefinition
from app.models.device import Device
from app.models.operational_alert import ActuatorFeedbackBinding
from app.models.project import Project
from app.models.sensor import Sensor
from app.models.sensor_model import SensorModel
from app.models.user import User
from app.mqtt.publisher import publish_actuator_command
from app.schemas.actuator import (
    ActuatorCommandCreate,
    ActuatorCommandRead,
    ActuatorCreate,
    ActuatorRead,
    ActuatorUpdate,
)
from app.schemas.common import DisableReasonRequest
from app.schemas.operational_alert import FeedbackBindingCreate, FeedbackBindingRead, FeedbackSensorOptionRead
from app.services.actuator_identity_service import generate_actuator_identity
from app.services.audit_service import write_audit
from app.services.actuator_electrical_feedback_service import ensure_actuator_electrical_feedback
from app.services.project_activity_service import dispatch_project_activity, record_project_activity
from app.services.project_notification_service import dispatch_actuator_command_transition
from app.queries.monitoring_queries import latest_project_actuator_electrical_rows
from app.services.monitoring_service import _actuator_electrical_payload

router = APIRouter(tags=["Actuators"])


async def _context(
    db: AsyncSession, project_id: int, device_id: int, actuator_id: int | None = None
) -> tuple[Project, Device, Actuator | None]:
    row = (
        await db.execute(
            select(Project, Device)
            .join(Device, Device.project_id == Project.id)
            .where(
                Project.id == project_id,
                Project.status == ProjectStatus.ACTIVE,
                Project.is_deleted.is_(False),
                Project.deleted_at.is_(None),
                Device.id == device_id,
                Device.is_deleted.is_(False),
                Device.deleted_at.is_(None),
            )
        )
    ).first()
    if row is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy Device trong Project")
    project, device = row
    actuator = None
    if actuator_id is not None:
        actuator = await db.scalar(
            select(Actuator).where(
                Actuator.id == actuator_id,
                Actuator.device_id == device.id,
                Actuator.is_deleted.is_(False),
                Actuator.removed_at.is_(None),
            )
        )
        if actuator is None:
            raise HTTPException(status_code=404, detail="Không tìm thấy Actuator trong Device")
    return project, device, actuator


@router.get(
    "/projects/{project_id}/devices/{device_id}/actuators/{actuator_id}/feedback-binding",
    response_model=FeedbackBindingRead | None,
)
async def get_feedback_binding(
    project_id: int, device_id: int, actuator_id: int,
    feedback_role: str = Query("RUNNING_CURRENT", pattern="^(SUPPLY_VOLTAGE|RUNNING_CURRENT)$"),
    db: AsyncSession = Depends(get_db), admin: User = Depends(require_admin),
) -> ActuatorFeedbackBinding | None:
    del admin
    await _context(db, project_id, device_id, actuator_id)
    binding = await db.scalar(select(ActuatorFeedbackBinding).where(ActuatorFeedbackBinding.actuator_id == actuator_id, ActuatorFeedbackBinding.feedback_role == feedback_role))
    if binding is None:
        return None
    definition = await db.get(ActuatorModelFeedbackDefinition, binding.model_feedback_id) if binding.model_feedback_id else None
    binding.effective_lower_threshold = binding.lower_threshold if binding.lower_threshold is not None else definition.default_lower_threshold if definition else None
    binding.effective_upper_threshold = binding.upper_threshold if binding.upper_threshold is not None else definition.default_upper_threshold if definition else None
    binding.default_lower_threshold = definition.default_lower_threshold if definition else None
    binding.default_upper_threshold = definition.default_upper_threshold if definition else None
    binding.threshold_source = "ACTUATOR_OVERRIDE" if binding.lower_threshold is not None or binding.upper_threshold is not None else "MODEL_DEFAULT" if definition and (definition.default_lower_threshold is not None or definition.default_upper_threshold is not None) else "NONE"
    return binding


@router.get(
    "/projects/{project_id}/devices/{device_id}/actuators/{actuator_id}/feedback-sensors",
    response_model=list[FeedbackSensorOptionRead],
)
async def list_feedback_sensors(
    project_id: int, device_id: int, actuator_id: int,
    feedback_role: str = Query("RUNNING_CURRENT", pattern="^(SUPPLY_VOLTAGE|RUNNING_CURRENT)$"),
    db: AsyncSession = Depends(get_db), admin: User = Depends(require_admin),
) -> list[FeedbackSensorOptionRead]:
    del admin
    await _context(db, project_id, device_id, actuator_id)
    rows = (
        await db.execute(
            select(Sensor, SensorModel, Device)
            .join(SensorModel, SensorModel.id == Sensor.sensor_model_id)
            .join(Device, Device.id == Sensor.device_id)
            .where(
                Device.project_id == project_id,
                Device.is_deleted.is_(False),
                Sensor.is_enabled.is_(True),
                Sensor.is_deleted.is_(False),
                SensorModel.is_active.is_(True),
                SensorModel.is_deleted.is_(False),
                SensorModel.unit == ("V" if feedback_role == "SUPPLY_VOLTAGE" else "A"),
                SensorModel.value_type == "NUMBER",
                SensorModel.measurement_semantics == "GAUGE",
            )
            .order_by(Device.name, Sensor.name)
        )
    ).all()
    return [
        FeedbackSensorOptionRead(
            id=sensor.id, code=sensor.code, name=sensor.name,
            device_id=sensor_device.id, device_code=sensor_device.code, device_name=sensor_device.name,
            sensor_model_id=model.id, sensor_model_code=model.code, sensor_model_name=model.name,
            unit=model.unit, data_type="FLOAT",
        )
        for sensor, model, sensor_device in rows
    ]


@router.put(
    "/projects/{project_id}/devices/{device_id}/actuators/{actuator_id}/feedback-binding",
    response_model=FeedbackBindingRead,
)
async def set_feedback_binding(
    project_id: int, device_id: int, actuator_id: int, payload: FeedbackBindingCreate,
    db: AsyncSession = Depends(get_db), admin: User = Depends(require_admin),
) -> ActuatorFeedbackBinding:
    _, _, actuator = await _context(db, project_id, device_id, actuator_id)
    assert actuator is not None
    sensor_row = (
        await db.execute(
            select(Sensor, SensorModel, Device)
            .join(SensorModel, SensorModel.id == Sensor.sensor_model_id)
            .join(Device, Device.id == Sensor.device_id)
            .where(Sensor.id == payload.sensor_id, Sensor.is_enabled.is_(True), Sensor.is_deleted.is_(False))
        )
    ).first()
    if sensor_row is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy cảm biến phản hồi")
    sensor, sensor_model, sensor_device = sensor_row
    if sensor_device.project_id != project_id:
        raise HTTPException(status_code=409, detail="Cảm biến và cơ cấu chấp hành phải thuộc cùng dự án")
    required_unit = "V" if payload.feedback_role == "SUPPLY_VOLTAGE" else "A"
    if sensor_model.unit != required_unit or sensor_model.value_type != "NUMBER" or sensor_model.measurement_semantics != "GAUGE":
        raise HTTPException(status_code=409, detail=f"Chỉ có thể liên kết Sensor Model số thực dạng GAUGE, đơn vị {required_unit}")
    definition = await db.scalar(select(ActuatorModelFeedbackDefinition).where(
        ActuatorModelFeedbackDefinition.actuator_model_id == actuator.actuator_model_id,
        ActuatorModelFeedbackDefinition.feedback_role == payload.feedback_role,
        ActuatorModelFeedbackDefinition.is_enabled.is_(True),
    ))
    if definition is not None and definition.sensor_model_id != sensor.sensor_model_id:
        raise HTTPException(status_code=409, detail="Mẫu cảm biến không tương thích với dữ liệu phản hồi của mẫu cơ cấu chấp hành")
    binding = await db.scalar(select(ActuatorFeedbackBinding).where(ActuatorFeedbackBinding.actuator_id == actuator.id, ActuatorFeedbackBinding.feedback_role == payload.feedback_role))
    if binding is None:
        binding = ActuatorFeedbackBinding(actuator_id=actuator.id, sensor_id=sensor.id, feedback_role=payload.feedback_role, model_feedback_id=definition.id if definition else None, value_key=payload.value_key, unit=sensor_model.unit, data_type="FLOAT", lower_threshold=payload.lower_threshold, upper_threshold=payload.upper_threshold, is_enabled=True, created_by=admin.id, updated_by=admin.id)
        db.add(binding)
    else:
        binding.sensor_id = sensor.id
        binding.is_enabled = True
        binding.value_key = payload.value_key
        binding.unit = sensor_model.unit
        binding.data_type = "FLOAT"
        binding.model_feedback_id = definition.id if definition else binding.model_feedback_id
        binding.lower_threshold = payload.lower_threshold
        binding.upper_threshold = payload.upper_threshold
        binding.updated_by = admin.id
    await write_audit(db, user_id=admin.id, action="ACTUATOR_CURRENT_BINDING_UPDATED", entity_type="ACTUATOR", entity_id=actuator.id, new_data={"project_id": project_id, "actuator_id": actuator.id, "sensor_id": sensor.id, "feedback_role": payload.feedback_role})
    await db.commit()
    await db.refresh(binding)
    binding.effective_lower_threshold = binding.lower_threshold if binding.lower_threshold is not None else definition.default_lower_threshold if definition else None
    binding.effective_upper_threshold = binding.upper_threshold if binding.upper_threshold is not None else definition.default_upper_threshold if definition else None
    binding.default_lower_threshold = definition.default_lower_threshold if definition else None
    binding.default_upper_threshold = definition.default_upper_threshold if definition else None
    binding.threshold_source = "ACTUATOR_OVERRIDE" if binding.lower_threshold is not None or binding.upper_threshold is not None else "MODEL_DEFAULT" if definition and (definition.default_lower_threshold is not None or definition.default_upper_threshold is not None) else "NONE"
    return binding


@router.delete(
    "/projects/{project_id}/devices/{device_id}/actuators/{actuator_id}/feedback-binding",
    status_code=204,
)
async def delete_feedback_binding(
    project_id: int, device_id: int, actuator_id: int,
    feedback_role: str = Query("RUNNING_CURRENT", pattern="^(SUPPLY_VOLTAGE|RUNNING_CURRENT)$"),
    db: AsyncSession = Depends(get_db), admin: User = Depends(require_admin),
) -> Response:
    await _context(db, project_id, device_id, actuator_id)
    binding = await db.scalar(select(ActuatorFeedbackBinding).where(ActuatorFeedbackBinding.actuator_id == actuator_id, ActuatorFeedbackBinding.feedback_role == feedback_role))
    if binding is not None:
        await write_audit(db, user_id=admin.id, action="ACTUATOR_CURRENT_BINDING_REMOVED", entity_type="ACTUATOR", entity_id=actuator_id, new_data={"project_id": project_id, "sensor_id": binding.sensor_id})
        await db.delete(binding)
        await db.commit()
    return Response(status_code=204)


@router.get("/projects/{project_id}/devices/{device_id}/actuators", response_model=list[ActuatorRead])
async def list_actuators(
    project_id: int,
    device_id: int,
    include_disabled: bool = Query(True),
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
) -> list[Actuator]:
    del admin
    await _context(db, project_id, device_id)
    query = select(Actuator).where(
        Actuator.device_id == device_id,
        Actuator.is_deleted.is_(False),
        Actuator.removed_at.is_(None),
    )
    if not include_disabled:
        query = query.where(Actuator.is_enabled.is_(True))
    actuators = list((await db.scalars(query.order_by(Actuator.name))).all())
    electrical_rows = await latest_project_actuator_electrical_rows(db, project_id, include_disabled=include_disabled)
    electrical_by_actuator: dict[int, list] = defaultdict(list)
    for row in electrical_rows:
        electrical_by_actuator[row._mapping["id"]].append(row)
    now = datetime.now(UTC)
    for actuator in actuators:
        electrical = _actuator_electrical_payload(electrical_by_actuator.get(actuator.id, []), now)
        electrical.pop("active_incident", None)
        actuator.electrical_feedbacks = electrical
    return actuators


@router.post(
    "/projects/{project_id}/devices/{device_id}/actuators",
    response_model=ActuatorRead,
    status_code=201,
)
async def create_actuator(
    project_id: int,
    device_id: int,
    payload: ActuatorCreate,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
) -> Actuator:
    project, device, _ = await _context(db, project_id, device_id)
    actuator_model = await db.scalar(
        select(ActuatorModel).where(
            ActuatorModel.id == payload.actuator_model_id,
            ActuatorModel.is_active.is_(True),
            ActuatorModel.is_deleted.is_(False),
            ActuatorModel.deleted_at.is_(None),
        )
    )
    if actuator_model is None:
        raise HTTPException(
            status_code=404,
            detail="Không tìm thấy mẫu cơ cấu chấp hành đang hoạt động",
        )
    identity = await generate_actuator_identity(
        db,
        project=project,
        device=device,
        actuator_model=actuator_model,
    )
    actuator = Actuator(
        device_id=device.id,
        actuator_model_id=actuator_model.id,
        sequence_number=identity.sequence_number,
        code=identity.code,
        name=identity.display_name,
        location=payload.location,
        notes=payload.notes,
        is_enabled=True,
        desired_state=actuator_model.default_state,
        reported_state=None,
        last_command_at=None,
        last_reported_at=None,
        removed_at=None,
    )
    db.add(actuator)
    await db.flush()
    await ensure_actuator_electrical_feedback(db, actuator=actuator, actor_id=admin.id)
    await write_audit(
        db,
        user_id=admin.id,
        action="ACTUATOR_CREATED",
        entity_type="ACTUATOR",
        entity_id=actuator.id,
        new_data={
            "project_id": project.id,
            "device_id": device.id,
            "actuator_id": actuator.id,
            "actuator_code": actuator.code,
            "actuator_model_code": actuator_model.code,
            "generated_name": actuator.name,
            "actor_user_id": admin.id,
        },
    )
    await db.commit()
    await db.refresh(actuator)
    return actuator


@router.patch(
    "/projects/{project_id}/devices/{device_id}/actuators/{actuator_id}",
    response_model=ActuatorRead,
)
async def update_actuator(
    project_id: int,
    device_id: int,
    actuator_id: int,
    payload: ActuatorUpdate,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
) -> Actuator:
    _, _, actuator = await _context(db, project_id, device_id, actuator_id)
    assert actuator is not None
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(actuator, key, value)
    await write_audit(
        db,
        user_id=admin.id,
        action="ACTUATOR_UPDATED",
        entity_type="ACTUATOR",
        entity_id=actuator.id,
        new_data={
            "project_id": project_id,
            "device_id": device_id,
            "actuator_id": actuator.id,
            "actuator_code": actuator.code,
            "actor_user_id": admin.id,
            **payload.model_dump(exclude_unset=True),
        },
    )
    await db.commit()
    await db.refresh(actuator)
    return actuator


@router.post(
    "/projects/{project_id}/devices/{device_id}/actuators/{actuator_id}/disable",
    status_code=204,
)
async def disable_actuator(
    project_id: int,
    device_id: int,
    actuator_id: int,
    payload: DisableReasonRequest,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
) -> Response:
    _, _, actuator = await _context(db, project_id, device_id, actuator_id)
    assert actuator is not None
    actuator.is_enabled = False
    actuator.disabled_at = datetime.now(UTC)
    actuator.disabled_by_user_id = admin.id
    actuator.disabled_reason = payload.reason.strip() or None
    await write_audit(
        db, user_id=admin.id, action="ACTUATOR_DISABLED", entity_type="ACTUATOR",
        entity_id=actuator.id, new_data={"is_enabled": False, "reason": actuator.disabled_reason}
    )
    await db.commit()
    return Response(status_code=204)


@router.post(
    "/projects/{project_id}/devices/{device_id}/actuators/{actuator_id}/activate",
    status_code=204,
)
async def activate_actuator(
    project_id: int,
    device_id: int,
    actuator_id: int,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
) -> Response:
    _, _, actuator = await _context(db, project_id, device_id, actuator_id)
    assert actuator is not None
    actuator.is_enabled = True
    actuator.disabled_at = None
    actuator.disabled_by_user_id = None
    actuator.disabled_reason = None
    await write_audit(
        db, user_id=admin.id, action="ACTUATOR_ACTIVATED", entity_type="ACTUATOR",
        entity_id=actuator.id, new_data={"is_enabled": True}
    )
    await db.commit()
    return Response(status_code=204)


@router.delete(
    "/projects/{project_id}/devices/{device_id}/actuators/{actuator_id}",
    status_code=204,
)
async def remove_actuator(
    project_id: int,
    device_id: int,
    actuator_id: int,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
) -> Response:
    project, device, actuator = await _context(
        db,
        project_id,
        device_id,
        actuator_id,
    )
    assert actuator is not None
    active_command = await db.scalar(
        select(ActuatorCommand.id).where(
            ActuatorCommand.actuator_id == actuator.id,
            ActuatorCommand.status.in_(("PENDING", "PUBLISHED")),
        )
    )
    if active_command is not None:
        raise HTTPException(
            status_code=409,
            detail=(
                "Không thể xóa cơ cấu chấp hành khi đang có lệnh điều khiển "
                "chưa hoàn tất."
            ),
        )
    now = datetime.now(UTC)
    actuator.is_enabled = False
    actuator.removed_at = now
    actuator.removed_by_user_id = admin.id
    actuator.removed_reason = None
    await write_audit(
        db,
        user_id=admin.id,
        action="ACTUATOR_REMOVED_FROM_DEVICE",
        entity_type="ACTUATOR",
        entity_id=actuator.id,
        new_data={
            "project_id": project.id,
            "device_id": device.id,
            "actuator_id": actuator.id,
            "actuator_code": actuator.code,
            "actor_user_id": admin.id,
            "reason": actuator.removed_reason,
        },
    )
    await db.commit()
    return Response(status_code=204)


@router.post(
    "/projects/{project_id}/devices/{device_id}/actuators/{actuator_id}/commands",
    response_model=ActuatorCommandRead,
    status_code=202,
)
async def command_actuator(
    project_id: int,
    device_id: int,
    actuator_id: int,
    payload: ActuatorCommandCreate,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
) -> ActuatorCommandRead:
    _, device, actuator = await _context(db, project_id, device_id, actuator_id)
    assert actuator is not None
    if not device.is_enabled or device.status != DeviceStatus.ONLINE:
        raise HTTPException(status_code=409, detail="Device đang offline hoặc đã vô hiệu hóa")
    if not actuator.is_enabled:
        raise HTTPException(status_code=409, detail="Actuator đã vô hiệu hóa")
    active = await db.scalar(select(ActuatorCommand.id).where(
        ActuatorCommand.actuator_id == actuator.id,
        ActuatorCommand.status.in_(("PENDING", "PUBLISHED")),
    ))
    if active is not None:
        raise HTTPException(status_code=409, detail="Actuator đang có lệnh chờ xử lý")
    now = datetime.now(UTC)
    actuator.desired_state = payload.desired_state
    actuator.last_command_at = now
    command = ActuatorCommand(
        actuator_id=actuator.id,
        desired_state=payload.desired_state,
        status="PENDING",
        requested_by_user_id=admin.id,
        requested_at=now,
    )
    db.add(command)
    await db.flush()
    activity = await record_project_activity(db, project_id=project_id, actor=admin, action="ACTUATOR_COMMAND_REQUESTED", entity_type="ACTUATOR", entity_id=actuator.id, entity_name=actuator.name, changes={"desired_state": {"before": actuator.reported_state, "after": payload.desired_state}, "command_status": {"before": None, "after": "PENDING"}})
    await db.commit()
    await dispatch_project_activity(db, activity_id=activity.id)
    try:
        await asyncio.to_thread(
            publish_actuator_command,
            device.code,
            command.id,
            actuator.code,
            command.desired_state,
            command.requested_at.isoformat(),
        )
        command.published_at = datetime.now(UTC)
        command.status = "PUBLISHED"
        await db.commit()
    except Exception as exc:
        command.failed_at = datetime.now(UTC)
        command.failure_reason = str(exc)[:500]
        command.status = "FAILED"
        await write_audit(
            db,
            user_id=admin.id,
            project_id=project_id,
            action="ACTUATOR_COMMAND_FAILED",
            entity_type="ACTUATOR",
            entity_id=actuator.id,
            description="Không thể gửi lệnh điều khiển tới MQTT Broker",
            new_data={"display_name": actuator.name, "desired_state": command.desired_state, "reported_state": actuator.reported_state, "status": "FAILED"},
        )
        await db.commit()
        await dispatch_actuator_command_transition(db, command_id=command.id, transition="FAILED")
        raise HTTPException(status_code=502, detail="Không thể gửi lệnh tới MQTT Broker") from exc
    return ActuatorCommandRead(
        command_id=command.id,
        actuator_id=command.actuator_id,
        desired_state=command.desired_state,
        reported_state=actuator.reported_state,
        status=command.status,
        requested_at=command.requested_at,
    )


@router.get(
    "/projects/{project_id}/devices/{device_id}/actuators/{actuator_id}/commands",
    response_model=list[ActuatorCommandRead],
)
async def list_commands(
    project_id: int,
    device_id: int,
    actuator_id: int,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
) -> list[ActuatorCommandRead]:
    _, _, actuator = await _context(db, project_id, device_id, actuator_id)
    assert actuator is not None
    commands = list((await db.scalars(select(ActuatorCommand).where(ActuatorCommand.actuator_id == actuator.id).order_by(ActuatorCommand.requested_at.desc()).limit(50))).all())
    return [ActuatorCommandRead(command_id=item.id, actuator_id=item.actuator_id, desired_state=item.desired_state, reported_state=item.reported_state, status=item.status, requested_at=item.requested_at) for item in commands]
