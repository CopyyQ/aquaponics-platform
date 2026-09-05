import logging
import json
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy import func, or_, select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased, selectinload

from app.api.deps import get_current_operational_user, require_admin, require_roles
from app.core.config import settings
from app.db.session import get_db
from app.core.enums import AlertStatus, DeviceStatus, ProjectStatus, SensorPurpose, UserRole, UserStatus
from app.models.alert import SensorAlert
from app.models.sensor import Sensor, SensorModel
from app.models.telemetry import TelemetryReading
from app.models.device import Device
from app.models.actuator import Actuator
from app.models.actuator_model import ActuatorModel, ActuatorModelFeedbackDefinition
from app.models.device_template import DeviceTemplateActuator
from app.models.device_template import DeviceTemplate, DeviceTemplateSensor
from app.models.project import Project, ProjectMember
from app.models.operational_alert import ActuatorFeedbackBinding
from app.models.user import User
from app.schemas.common import DisableReasonRequest
from app.schemas.device import DeviceCreate, DeviceRead, DeviceUpdate
from app.schemas.project import (
    DeviceFromTemplateRequest,
    DeviceListResponse,
    DeviceConfigDevice,
    DeviceConfigActuator,
    DeviceConfigActuatorFeedback,
    DeviceConfigFeedbackMqtt,
    DeviceConfigMqtt,
    DeviceConfigOwner,
    DeviceConfigProject,
    DeviceConfigSensor,
    DeviceConfigSummary,
    DeviceConfigTopics,
    ProjectDeviceConfig,
    ProjectCreate,
    ProjectDisableRequest,
    ProjectMemberCreate,
    ProjectMemberListResponse,
    ProjectMemberRead,
    ProjectRead,
    ProjectUpdate,
)
from app.services.access_service import active_project_clause, accessible_project_clause, require_project_access
from app.queries.project_queries import existing_project_clause
from app.services.audit_service import write_audit
from app.services.project_activity_service import dispatch_project_activity, record_project_activity
from app.services.actuator_identity_service import generate_actuator_identity
from app.services.mqtt_connection_config_service import (
    build_mqtt_connection_config,
    mqtt_config_filename,
)
from app.services.energy_monitor_service import (
    ENERGY_MONITOR_KIND,
    ENERGY_SENSOR_SPEC_BY_MODEL,
    EnergyTemplateValidationError,
    validate_energy_template,
)
from app.services.actuator_electrical_feedback_service import ensure_actuator_electrical_feedback, ensure_device_actuator_electrical_feedback
from app.services.monitoring_service import get_project_monitoring_summary
from app.services.energy_monitor_read_service import (
    get_energy_monitor_overview,
    get_energy_power_series,
)
from app.schemas.energy_monitor import EnergyOverviewResponse, EnergyPowerSeriesResponse
from app.schemas.project_overview import ProjectOverviewResponse
from app.core.enums import MonitoringRange

router = APIRouter(prefix="/projects", tags=["Projects"])
ACTIVE_ALERTS = [AlertStatus.PENDING, AlertStatus.OPEN, AlertStatus.ACKNOWLEDGED]
logger = logging.getLogger("uvicorn.error")


@router.get("", response_model=list[ProjectRead])
async def list_projects(
    db: AsyncSession = Depends(get_db), actor: User = Depends(get_current_operational_user)
) -> list[Project]:
    visibility = existing_project_clause(Project) if actor.system_role == UserRole.ADMIN else active_project_clause(Project)
    query = select(Project).where(visibility, accessible_project_clause(actor)).order_by(Project.name)
    return list((await db.scalars(query)).all())


@router.post("", response_model=ProjectRead, status_code=201)
async def create_project(
    payload: ProjectCreate,
    db: AsyncSession = Depends(get_db),
    actor: User = Depends(require_roles(UserRole.ADMIN)),
) -> Project:
    owner = await db.scalar(
        select(User).where(
            User.id == payload.owner_user_id,
            User.system_role == UserRole.OWNER,
            User.status == UserStatus.ACTIVE,
            User.is_deleted.is_(False),
        )
    )
    if owner is None:
        raise HTTPException(status_code=400, detail="Chủ dự án phải là Owner đang hoạt động")
    if await db.scalar(select(Project.id).where(Project.code == payload.code)):
        raise HTTPException(status_code=409, detail="Mã dự án đã tồn tại")
    project = Project(**payload.model_dump())
    db.add(project)
    await db.flush()
    activity = await record_project_activity(db, project_id=project.id, actor=actor, action="PROJECT_CREATED", entity_type="PROJECT", entity_id=project.id, entity_name=project.name, changes={"created": True})
    await db.commit()
    await db.refresh(project)
    await dispatch_project_activity(db, activity_id=activity.id)
    return project


@router.get("/{project_id}", response_model=ProjectRead)
async def get_project(
    project_id: int,
    db: AsyncSession = Depends(get_db),
    actor: User = Depends(get_current_operational_user),
) -> Project:
    return await require_project_access(db, project_id, actor)


@router.patch("/{project_id}", response_model=ProjectRead)
async def update_project(
    project_id: int,
    payload: ProjectUpdate,
    db: AsyncSession = Depends(get_db),
    actor: User = Depends(get_current_operational_user),
) -> Project:
    project = await require_project_access(db, project_id, actor, manage=True)
    changes = payload.model_dump(exclude_unset=True)
    if "status" in changes:
        raise HTTPException(status_code=409, detail="Hãy dùng thao tác vòng đời để thay đổi trạng thái dự án")
    before = {key: getattr(project, key) for key in changes}
    for key, value in changes.items():
        setattr(project, key, value)
    changed = {key: {"before": before[key], "after": value} for key, value in changes.items() if before[key] != value}
    if not changed:
        return project
    activity = await record_project_activity(db, project_id=project.id, actor=actor, action="PROJECT_UPDATED", entity_type="PROJECT", entity_id=project.id, entity_name=project.name, changes=changed)
    await db.commit()
    await db.refresh(project)
    await dispatch_project_activity(db, activity_id=activity.id)
    return project


@router.get("/{project_id}/overview", response_model=ProjectOverviewResponse)
async def project_overview(
    project_id: int,
    db: AsyncSession = Depends(get_db),
    actor: User = Depends(get_current_operational_user),
) -> dict:
    project = await require_project_access(db, project_id, actor)
    health = await get_project_monitoring_summary(db, project_id, project_status=project.status)
    owner = await db.get(User, project.owner_user_id)
    devices = list((await db.scalars(select(Device).where(Device.project_id == project_id, Device.is_enabled.is_(True), Device.is_deleted.is_(False)).order_by(Device.name))).all())
    energy_devices = list((await db.execute(
        select(Device.id, Device.name, Device.status)
        .join(DeviceTemplate, DeviceTemplate.id == Device.device_template_id)
        .where(Device.project_id == project_id, Device.is_deleted.is_(False), DeviceTemplate.device_kind == ENERGY_MONITOR_KIND)
        .order_by(Device.name)
    )).all())
    member_count = health["inventory"]["members_total"]
    return {
        "project": ProjectRead.model_validate(project).model_dump(mode="json"),
        "owner": {"id": owner.id, "full_name": owner.full_name, "email": owner.email} if owner else None,
        "member_count": member_count,
        "device_count": health["inventory"]["devices_total"],
        "online_device_count": health["inventory"]["devices_online"],
        "offline_device_count": health["inventory"]["devices_offline"],
        "sensor_count": health["inventory"]["sensors_total"],
        "offline_sensor_count": health["inventory"]["sensors_offline"],
        "open_alert_count": health["alerts"]["open_total"],
        "last_telemetry_at": health["freshness"]["last_received_at"],
        "health": health["health"], "inventory": health["inventory"],
        "alerts": health["alerts"], "freshness": health["freshness"],
        "attention": health["attention"], "measurement_groups": health["measurement_groups"],
        "device_health": health["device_health"], "recent_alerts": health["recent_alerts"],
        "actuators": health["actuators"],
        "actuator_inventory": health["actuator_inventory"],
        "critical_issues": [{"message": item["message"]} for item in health["health"]["reasons"]],
        "devices_summary": [DeviceRead.model_validate(item).model_dump(mode="json") for item in devices],
        "energy_devices_summary": {
            "count": len(energy_devices),
            "items": [{"id": device_id, "name": name, "status": status} for device_id, name, status in energy_devices],
        },
    }


@router.get(
    "/{project_id}/devices/{device_id}/energy-overview",
    response_model=EnergyOverviewResponse,
)
async def energy_monitor_overview(
    project_id: int,
    device_id: int,
    db: AsyncSession = Depends(get_db),
    actor: User = Depends(get_current_operational_user),
) -> dict:
    await require_project_access(db, project_id, actor)
    return await get_energy_monitor_overview(db, project_id=project_id, device_id=device_id)


@router.get(
    "/{project_id}/devices/{device_id}/energy-power-series",
    response_model=EnergyPowerSeriesResponse,
)
async def energy_monitor_power_series(
    project_id: int,
    device_id: int,
    range: MonitoringRange = Query(default=MonitoringRange.TWENTY_FOUR_HOURS),
    db: AsyncSession = Depends(get_db),
    actor: User = Depends(get_current_operational_user),
) -> dict:
    await require_project_access(db, project_id, actor)
    return await get_energy_power_series(
        db, project_id=project_id, device_id=device_id, monitoring_range=range
    )


@router.get("/{project_id}/devices", response_model=DeviceListResponse)
async def list_project_devices(
    project_id: int,
    include_disabled: bool = Query(default=False),
    device_kind: str | None = Query(default=None, pattern="^(GENERIC|ENERGY_MONITOR)$"),
    db: AsyncSession = Depends(get_db),
    actor: User = Depends(get_current_operational_user),
) -> DeviceListResponse:
    await require_project_access(db, project_id, actor)
    if include_disabled and actor.system_role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Chỉ Admin được xem thiết bị đã tắt")
    query = select(Device).where(
        Device.project_id == project_id,
        Device.is_deleted.is_(False),
        Device.deleted_at.is_(None),
    )
    if device_kind is not None:
        query = query.join(DeviceTemplate).where(DeviceTemplate.device_kind == device_kind)
    if not include_disabled:
        query = query.where(Device.is_enabled.is_(True))
    sensor_count = (
        select(func.count(Sensor.id))
        .where(
            Sensor.device_id == Device.id,
            Sensor.is_enabled.is_(True),
            Sensor.is_deleted.is_(False),
            Sensor.deleted_at.is_(None),
            Sensor.purpose == SensorPurpose.GENERAL,
        )
        .correlate(Device)
        .scalar_subquery()
    )
    actuator_count = (
        select(func.count(Actuator.id))
        .where(
            Actuator.device_id == Device.id,
            Actuator.is_deleted.is_(False),
            Actuator.deleted_at.is_(None),
            Actuator.removed_at.is_(None),
        )
        .correlate(Device)
        .scalar_subquery()
    )
    rows = (
        await db.execute(
            query.options(selectinload(Device.device_template)).add_columns(
                sensor_count.label("sensor_count"),
                actuator_count.label("actuator_count"),
            ).order_by(Device.created_at.desc())
        )
    ).all()
    items = [
        {
            **DeviceRead.model_validate(device).model_dump(),
            "device_kind": device.device_template.device_kind if device.device_template else "GENERIC",
            "template_code": device.device_template.code if device.device_template else None,
            "template_name": device.device_template.name if device.device_template else None,
            "nominal_output_voltage_v": device.device_template.nominal_output_voltage_v if device.device_template else None,
            "sensor_count": int(device_sensor_count),
            "actuator_count": int(device_actuator_count),
        }
        for device, device_sensor_count, device_actuator_count in rows
    ]
    return DeviceListResponse(items=items, total=len(items))


@router.get(
    "/{project_id}/devices/{device_id}/mqtt-connection-config",
    response_class=Response,
)
async def download_mqtt_connection_config(
    project_id: int,
    device_id: int,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
) -> Response:
    config, project, device = await build_mqtt_connection_config(
        db,
        project_id=project_id,
        device_id=device_id,
    )
    await write_audit(
        db,
        user_id=admin.id,
        action="MQTT_CONNECTION_CONFIG_DOWNLOADED",
        entity_type="DEVICE",
        entity_id=device.id,
        new_data={
            "project_id": project.id,
            "device_id": device.id,
            "actor_user_id": admin.id,
            "configuration_hash": config["configuration_hash"],
        },
    )
    await db.commit()
    filename = (
        f"energy-monitor-{device.code}-config.json"
        if config.get("device", {}).get("kind") == ENERGY_MONITOR_KIND
        else mqtt_config_filename(project.code, device.code)
    )
    return Response(
        content=json.dumps(config, ensure_ascii=False, indent=2),
        media_type="application/json",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Cache-Control": "no-store",
        },
    )


@router.get("/{project_id}/device-config", response_model=ProjectDeviceConfig, deprecated=True)
@router.get("/{project_id}/device-config/export", response_model=ProjectDeviceConfig)
async def export_project_device_config(
    project_id: int,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
) -> ProjectDeviceConfig:
    project_context = (
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
    if project_context is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy dự án")

    project, owner = project_context
    if (
        owner.status != UserStatus.ACTIVE
        or owner.is_deleted
        or owner.deleted_at is not None
    ):
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
    for device in devices:
        await ensure_device_actuator_electrical_feedback(db, device_id=device.id, actor_id=admin.id)
    await db.commit()
    device_ids = [device.id for device in devices]

    sensor_rows = []
    if device_ids:
        sensor_rows = list(
            (
                await db.execute(
                    select(Sensor, SensorModel)
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

    sensors_by_device: dict[int, list[DeviceConfigSensor]] = {
        device_id: [] for device_id in device_ids
    }
    for sensor, sensor_model in sensor_rows:
        sensors_by_device[sensor.device_id].append(
            DeviceConfigSensor(
                id=sensor.id,
                sensor_code=sensor.code,
                sensor_model_code=sensor_model.code,
                name=sensor.name,
                unit=sensor_model.unit,
                is_enabled=sensor.is_enabled,
                status=sensor.status,
                lower_threshold=sensor.lower_threshold,
                upper_threshold=sensor.upper_threshold,
            )
        )

    actuator_rows = []
    feedback_rows = []
    if device_ids:
        actuator_rows = list(
            (
                await db.execute(
                    select(Actuator, ActuatorModel)
                    .outerjoin(ActuatorModel, ActuatorModel.id == Actuator.actuator_model_id)
                    .where(
                        Actuator.device_id.in_(device_ids),
                        Actuator.is_deleted.is_(False),
                        Actuator.removed_at.is_(None),
                    )
                    .order_by(Actuator.device_id, Actuator.id)
                )
            ).all()
        )
        feedback_rows = list(
            (
                await db.execute(
                    select(ActuatorFeedbackBinding, Actuator, Sensor, SensorModel, Device, ActuatorModelFeedbackDefinition)
                    .join(Actuator, Actuator.id == ActuatorFeedbackBinding.actuator_id)
                    .join(Sensor, Sensor.id == ActuatorFeedbackBinding.sensor_id)
                    .join(SensorModel, SensorModel.id == Sensor.sensor_model_id)
                    .join(Device, Device.id == Sensor.device_id)
                    .outerjoin(ActuatorModelFeedbackDefinition, ActuatorModelFeedbackDefinition.id == ActuatorFeedbackBinding.model_feedback_id)
                    .where(
                        Actuator.device_id.in_(device_ids),
                        ActuatorFeedbackBinding.is_enabled.is_(True),
                        Sensor.is_enabled.is_(True),
                        Sensor.is_deleted.is_(False),
                        Device.project_id == project_id,
                    )
                    .order_by(Actuator.id, ActuatorFeedbackBinding.id)
                )
            ).all()
        )

    feedbacks_by_actuator: dict[int, list[DeviceConfigActuatorFeedback]] = {}
    for binding, actuator, sensor, sensor_model, source_device, definition in feedback_rows:
        topic = f"aquaponics/{source_device.code}/telemetry"
        feedbacks_by_actuator.setdefault(actuator.id, []).append(
            DeviceConfigActuatorFeedback(
                role=binding.feedback_role,
                sensor_id=sensor.id,
                sensor_code=sensor.code,
                sensor_model_code=sensor_model.code,
                value_key=binding.value_key,
                unit=binding.unit,
                data_type=binding.data_type,
                lower_threshold=binding.lower_threshold if binding.lower_threshold is not None else definition.default_lower_threshold if definition else None,
                upper_threshold=binding.upper_threshold if binding.upper_threshold is not None else definition.default_upper_threshold if definition else None,
                mqtt=DeviceConfigFeedbackMqtt(
                    topic=topic,
                    payload={
                        "sent_at": "<ISO-8601>",
                        "readings": [{"sensor_code": sensor.code, "value": f"<{binding.value_key}>", "recorded_at": "<ISO-8601>"}],
                    },
                ),
            )
        )
    actuators_by_device: dict[int, list[DeviceConfigActuator]] = {device_id: [] for device_id in device_ids}
    for actuator, actuator_model in actuator_rows:
        actuators_by_device[actuator.device_id].append(
            DeviceConfigActuator(
                id=actuator.id,
                code=actuator.code,
                name=actuator.name,
                actuator_model_code=actuator_model.code if actuator_model else None,
                is_enabled=actuator.is_enabled,
                feedbacks=feedbacks_by_actuator.get(actuator.id, []),
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
            actuators=actuators_by_device[device.id],
        )
        for device in devices
    ]
    exported_sensors = [sensor for device in exported_devices for sensor in device.sensors]
    exported_actuators = [actuator for device in exported_devices for actuator in device.actuators]

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
            actuator_count=len(exported_actuators),
            enabled_actuator_count=sum(actuator.is_enabled for actuator in exported_actuators),
            feedback_count=sum(len(actuator.feedbacks) for actuator in exported_actuators),
        ),
    )


async def _device_lifecycle_context(db: AsyncSession, project_id: int, device_id: int) -> tuple[Project, Device]:
    context = (await db.execute(
        select(Project, Device).join(Device, Device.project_id == Project.id).where(
            Project.id == project_id, Project.is_deleted.is_(False), Project.deleted_at.is_(None),
            Device.id == device_id, Device.is_deleted.is_(False), Device.deleted_at.is_(None),
        )
    )).first()
    if context is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy thiết bị trong dự án")
    project, device = context
    if project.status != ProjectStatus.ACTIVE:
        raise HTTPException(status_code=409, detail={"code": "PROJECT_NOT_ACTIVE", "detail": "Dự án không ở trạng thái hoạt động."})
    return project, device


@router.post("/{project_id}/devices/{device_id}/disable", status_code=204)
async def disable_project_device(
    project_id: int,
    device_id: int,
    payload: DisableReasonRequest,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
) -> Response:
    project, device = await _device_lifecycle_context(db, project_id, device_id)
    old_data = {"is_enabled": device.is_enabled}
    device.is_enabled = False
    device.disabled_at = datetime.now(UTC)
    device.disabled_by_user_id = admin.id
    device.disabled_reason = payload.reason.strip() or None
    activity = await record_project_activity(db, project_id=project.id, actor=admin, action="DEVICE_DISABLED", entity_type="DEVICE", entity_id=device.id, entity_name=device.name, changes={"is_enabled": {"before": old_data["is_enabled"], "after": False}})
    await db.commit()
    await dispatch_project_activity(db, activity_id=activity.id)
    return Response(status_code=204)


@router.post("/{project_id}/devices/{device_id}/activate", status_code=204)
async def activate_project_device(
    project_id: int, device_id: int, db: AsyncSession = Depends(get_db), admin: User = Depends(require_admin)
) -> Response:
    project, device = await _device_lifecycle_context(db, project_id, device_id)
    old_data = {"is_enabled": device.is_enabled, "disabled_reason": device.disabled_reason}
    device.is_enabled = True
    device.disabled_at = None
    device.disabled_by_user_id = None
    device.disabled_reason = None
    device.status = DeviceStatus.WAITING_CONNECTION
    activity = await record_project_activity(db, project_id=project.id, actor=admin, action="DEVICE_ENABLED", entity_type="DEVICE", entity_id=device.id, entity_name=device.name, changes={"is_enabled": {"before": old_data["is_enabled"], "after": True}})
    await db.commit()
    await dispatch_project_activity(db, activity_id=activity.id)
    return Response(status_code=204)


@router.patch("/{project_id}/devices/{device_id}", response_model=DeviceRead)
async def update_project_device(
    project_id: int,
    device_id: int,
    payload: DeviceUpdate,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
) -> Device:
    project, device = await _device_lifecycle_context(db, project_id, device_id)
    values = payload.model_dump(exclude_unset=True)
    before = {key: getattr(device, key) for key in values}
    for key, value in values.items():
        setattr(device, key, value)
    changes = {key: {"before": before[key], "after": value} for key, value in values.items() if before[key] != value}
    if not changes:
        return device
    activity = await record_project_activity(db, project_id=project.id, actor=admin, action="DEVICE_UPDATED", entity_type="DEVICE", entity_id=device.id, entity_name=device.name, changes=changes)
    await db.commit()
    await db.refresh(device)
    await dispatch_project_activity(db, activity_id=activity.id)
    return device


@router.post("/{project_id}/devices", response_model=DeviceRead, status_code=201)
async def create_project_device(
    project_id: int,
    payload: DeviceCreate,
    db: AsyncSession = Depends(get_db),
    actor: User = Depends(get_current_operational_user),
) -> Device:
    await require_project_access(db, project_id, actor, manage=True)
    # Thiết bị là hạ tầng: Owner quản lý project/member, Admin tạo và chuyển thiết bị.
    if actor.system_role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Chỉ Admin được thêm thiết bị")
    if await db.scalar(select(Device.id).where(Device.code == payload.code)):
        raise HTTPException(status_code=409, detail="Mã thiết bị đã tồn tại")
    template = None
    if payload.device_template_id is not None:
        template = await db.scalar(
            select(DeviceTemplate)
            .options(
                selectinload(DeviceTemplate.sensor_mappings).selectinload(
                    DeviceTemplateSensor.sensor_model
                )
            )
            .where(
                DeviceTemplate.id == payload.device_template_id,
                DeviceTemplate.is_deleted.is_(False),
                DeviceTemplate.is_active.is_(True),
            )
        )
        if template is None:
            raise HTTPException(status_code=404, detail="Không tìm thấy mẫu thiết bị khả dụng")
    device = Device(
        project_id=project_id,
        device_template_id=payload.device_template_id,
        code=payload.code,
        name=payload.name,
        description=payload.notes if payload.notes is not None else payload.description,
        location=(
            payload.installation_location
            if payload.installation_location is not None
            else payload.location
        ),
        status=DeviceStatus.WAITING_CONNECTION,
    )
    db.add(device)
    await db.flush()
    if template is not None and payload.create_default_sensors:
        if template.device_kind == ENERGY_MONITOR_KIND:
            try:
                validate_energy_template(template)
            except EnergyTemplateValidationError as exc:
                raise HTTPException(status_code=422, detail=exc.detail) from exc
        for index, mapping in enumerate(template.sensor_mappings, start=1):
            energy_spec = ENERGY_SENSOR_SPEC_BY_MODEL.get(mapping.sensor_model.code)
            db.add(
                Sensor(
                    device_id=device.id,
                    sensor_model_id=mapping.sensor_model_id,
                    code=(energy_spec.sensor_code if template.device_kind == ENERGY_MONITOR_KIND and energy_spec else f"{device.code}-{mapping.sensor_model.code}-{index}"[:80]),
                    name=mapping.display_name or mapping.sensor_model.name,
                    installation_location=mapping.default_location,
                    lower_threshold=(
                        mapping.default_lower_threshold
                        if mapping.default_lower_threshold is not None
                        else mapping.sensor_model.default_lower_threshold
                    ),
                    upper_threshold=(
                        mapping.default_upper_threshold
                        if mapping.default_upper_threshold is not None
                        else mapping.sensor_model.default_upper_threshold
                    ),
                    warning_enabled=(mapping.default_warning_enabled if mapping.default_warning_enabled is not None else mapping.sensor_model.default_warning_enabled),
                    below_threshold_message=(mapping.default_below_threshold_message if mapping.default_below_threshold_message is not None else mapping.sensor_model.default_below_threshold_message),
                    above_threshold_message=(mapping.default_above_threshold_message if mapping.default_above_threshold_message is not None else mapping.sensor_model.default_above_threshold_message),
                    alert_risk_level=(mapping.default_alert_risk_level if mapping.default_alert_risk_level is not None else mapping.sensor_model.default_alert_risk_level),
                )
            )
    activity = await record_project_activity(db, project_id=project_id, actor=actor, action="DEVICE_ADDED", entity_type="DEVICE", entity_id=device.id, entity_name=device.name, changes={"created": True})
    await db.commit()
    await db.refresh(device)
    await dispatch_project_activity(db, activity_id=activity.id)
    return device


def _next_instance_code(prefix: str, existing_codes: list[str]) -> str:
    used = {
        int(code.removeprefix(f"{prefix}-"))
        for code in existing_codes
        if code.removeprefix(f"{prefix}-").isdigit()
    }
    sequence = 1
    while sequence in used:
        sequence += 1
    return f"{prefix}-{sequence:02d}"[:80]


@router.post("/{project_id}/devices/from-template", response_model=DeviceRead, status_code=201)
async def create_device_from_template(
    project_id: int,
    payload: DeviceFromTemplateRequest,
    db: AsyncSession = Depends(get_db),
    actor: User = Depends(require_roles(UserRole.ADMIN)),
) -> Device:
    project = await require_project_access(db, project_id, actor, manage=True)
    if project.status != ProjectStatus.ACTIVE:
        raise HTTPException(status_code=400, detail="Chỉ có thể thêm thiết bị vào dự án đang hoạt động")
    template = await db.scalar(
        select(DeviceTemplate)
        .options(
            selectinload(DeviceTemplate.sensor_mappings).selectinload(DeviceTemplateSensor.sensor_model),
            selectinload(DeviceTemplate.actuator_mappings).selectinload(DeviceTemplateActuator.actuator_model),
            selectinload(DeviceTemplate.actuator_mappings).selectinload(DeviceTemplateActuator.actuator_model).selectinload(ActuatorModel.feedback_definitions).selectinload(ActuatorModelFeedbackDefinition.sensor_model),
        )
        .where(DeviceTemplate.id == payload.device_template_id, DeviceTemplate.is_active.is_(True), DeviceTemplate.is_deleted.is_(False))
    )
    if template is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy mẫu thiết bị đang khả dụng")
    if template.device_kind == ENERGY_MONITOR_KIND:
        try:
            validate_energy_template(template)
        except EnergyTemplateValidationError as exc:
            raise HTTPException(status_code=422, detail=exc.detail) from exc
    requested_code = payload.code.strip().upper() if payload.code else None
    if requested_code and await db.scalar(select(Device.id).where(Device.code == requested_code)):
        raise HTTPException(status_code=409, detail="Mã thiết bị đã tồn tại")
    if db.bind and db.bind.dialect.name == "postgresql":
        await db.execute(text("SELECT pg_advisory_xact_lock(hashtext(:key))"), {"key": f"device-code:{project.id}:{template.id}"})
    prefix = f"{project.code}-{template.code}"[:77]
    existing_codes = list((await db.scalars(select(Device.code).where(Device.code.like(f"{prefix}-%")))).all())
    device = Device(
        project_id=project.id, device_template_id=template.id,
        code=requested_code or _next_instance_code(prefix, existing_codes),
        name=payload.name or template.name,
        description=payload.description if payload.description is not None else template.description,
        location=payload.location,
        status=DeviceStatus.WAITING_CONNECTION,
    )
    db.add(device)
    await db.flush()
    sensors_by_model: dict[int, list[Sensor]] = {}
    for index, mapping in enumerate(sorted(template.sensor_mappings, key=lambda item: item.sort_order), start=1):
        model = mapping.sensor_model
        energy_spec = ENERGY_SENSOR_SPEC_BY_MODEL.get(model.code)
        sensor = Sensor(
            device_id=device.id, sensor_model_id=model.id,
            code=(
                energy_spec.sensor_code
                if template.device_kind == ENERGY_MONITOR_KIND and energy_spec
                else f"{device.code}-{model.code}-{index:02d}"[:80]
            ),
            name=mapping.display_name or model.name,
            installation_location=mapping.default_location,
            lower_threshold=mapping.default_lower_threshold if mapping.default_lower_threshold is not None else model.default_lower_threshold,
            upper_threshold=mapping.default_upper_threshold if mapping.default_upper_threshold is not None else model.default_upper_threshold,
            warning_enabled=mapping.default_warning_enabled if mapping.default_warning_enabled is not None else model.default_warning_enabled,
            below_threshold_message=mapping.default_below_threshold_message if mapping.default_below_threshold_message is not None else model.default_below_threshold_message,
            above_threshold_message=mapping.default_above_threshold_message if mapping.default_above_threshold_message is not None else model.default_above_threshold_message,
            alert_risk_level=mapping.default_alert_risk_level if mapping.default_alert_risk_level is not None else model.default_alert_risk_level,
        )
        db.add(sensor)
        await db.flush()
        sensors_by_model.setdefault(model.id, []).append(sensor)
    for mapping in sorted(
        template.actuator_mappings,
        key=lambda item: item.sort_order,
    ):
        model = mapping.actuator_model
        identity = await generate_actuator_identity(
            db,
            project=project,
            device=device,
            actuator_model=model,
        )
        actuator = Actuator(
                device_id=device.id,
                actuator_model_id=model.id,
                sequence_number=identity.sequence_number,
                code=identity.code,
                name=mapping.default_name or identity.display_name,
                location=mapping.default_location,
                notes=mapping.default_notes,
                is_enabled=mapping.is_enabled,
                desired_state=mapping.default_state if mapping.default_state is not None else model.default_state,
                reported_state=None,
                last_command_at=None,
                last_reported_at=None,
                removed_at=None,
            )
        db.add(actuator)
        await db.flush()
        await ensure_actuator_electrical_feedback(db, actuator=actuator, actor_id=actor.id)
    activity = await record_project_activity(db, project_id=project.id, actor=actor, action="DEVICE_ADDED", entity_type="DEVICE", entity_id=device.id, entity_name=device.name, changes={"device_template": template.code})
    await db.commit()
    await db.refresh(device)
    await dispatch_project_activity(db, activity_id=activity.id)
    return {
        **DeviceRead.model_validate(device).model_dump(),
        "device_kind": template.device_kind,
        "template_code": template.code,
        "template_name": template.name,
        "nominal_output_voltage_v": template.nominal_output_voltage_v,
    }


@router.post("/{project_id}/devices/{device_id}/sync-template-sensors")
async def sync_device_template_sensors(
    project_id: int,
    device_id: int,
    db: AsyncSession = Depends(get_db),
    actor: User = Depends(require_roles(UserRole.ADMIN)),
) -> dict:
    await require_project_access(db, project_id, actor, manage=True)
    device = await db.scalar(
        select(Device)
        .options(
            selectinload(Device.sensors).selectinload(Sensor.sensor_model),
            selectinload(Device.device_template)
            .selectinload(DeviceTemplate.sensor_mappings)
            .selectinload(DeviceTemplateSensor.sensor_model),
        )
        .where(
            Device.id == device_id,
            Device.project_id == project_id,
            Device.is_deleted.is_(False),
        )
    )
    if device is None or device.device_template is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy thiết bị có mẫu trong dự án")
    template = device.device_template
    if template.device_kind == ENERGY_MONITOR_KIND:
        try:
            validate_energy_template(template)
        except EnergyTemplateValidationError as exc:
            raise HTTPException(status_code=422, detail=exc.detail) from exc
    existing_model_ids = {
        sensor.sensor_model_id for sensor in device.sensors if not sensor.is_deleted
    }
    added: list[str] = []
    for index, mapping in enumerate(
        sorted(template.sensor_mappings, key=lambda item: item.sort_order), start=1
    ):
        if mapping.sensor_model_id in existing_model_ids:
            continue
        model = mapping.sensor_model
        energy_spec = ENERGY_SENSOR_SPEC_BY_MODEL.get(model.code)
        sensor_code = (
            energy_spec.sensor_code
            if template.device_kind == ENERGY_MONITOR_KIND and energy_spec
            else f"{device.code}-{model.code}-{index:02d}"[:80]
        )
        db.add(
            Sensor(
                device_id=device.id,
                sensor_model_id=model.id,
                code=sensor_code,
                name=mapping.display_name or model.name,
                installation_location=mapping.default_location,
                lower_threshold=mapping.default_lower_threshold
                if mapping.default_lower_threshold is not None
                else model.default_lower_threshold,
                upper_threshold=mapping.default_upper_threshold
                if mapping.default_upper_threshold is not None
                else model.default_upper_threshold,
                warning_enabled=mapping.default_warning_enabled if mapping.default_warning_enabled is not None else model.default_warning_enabled,
                below_threshold_message=mapping.default_below_threshold_message if mapping.default_below_threshold_message is not None else model.default_below_threshold_message,
                above_threshold_message=mapping.default_above_threshold_message if mapping.default_above_threshold_message is not None else model.default_above_threshold_message,
                alert_risk_level=mapping.default_alert_risk_level if mapping.default_alert_risk_level is not None else model.default_alert_risk_level,
            )
        )
        added.append(model.code)
    await write_audit(
        db,
        user_id=actor.id,
        action="SYNC_DEVICE_TEMPLATE_SENSORS",
        entity_type="DEVICE",
        entity_id=device.id,
        new_data={"project_id": project_id, "added_sensor_models": added},
    )
    await db.commit()
    return {
        "device_id": device.id,
        "added_sensor_models": added,
        "added_count": len(added),
        "preserved_existing_sensors": len(existing_model_ids),
    }
