from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import DeviceStatus, DeviceType
from app.models.actuator import Actuator, ActuatorCommand
from app.models.operational_alert import OperationalIncident
from app.models.device import Device
from app.models.project import Project
from app.models.scada_dashboard import ScadaDashboard
from app.models.sensor import Sensor
from app.models.telemetry import TelemetryReading
from app.models.user import User
from app.queries.scada_runtime_queries import (
    latest_actuator_commands,
    latest_scada_dashboard,
    latest_sensor_readings,
    next_scada_dashboard_version,
    open_project_alerts,
    project_scada_devices,
)
from app.schemas.scada import (
    ScadaBinding,
    ScadaConnection,
    ScadaDashboardInfo,
    ScadaInventory,
    ScadaInventoryActuator,
    ScadaInventoryDevice,
    ScadaInventorySensor,
    ScadaIssue,
    ScadaLayout,
    ScadaLayoutMutationResponse,
    ScadaRuntimeActuator,
    ScadaRuntimeAlert,
    ScadaRuntimeDevice,
    ScadaRuntimeResponse,
    ScadaRuntimeSensor,
    ScadaRuntimeState,
    ScadaSummary,
    ScadaSymbol,
    ScadaUnplacedEntity,
)
from app.services.measurement_quality import classify_measurement_quality
from app.services.project_activity_service import dispatch_project_activity, record_project_activity


STALE_AFTER = timedelta(minutes=5)
SEVERITY_ORDER = {"CRITICAL": 0, "HIGH": 1, "WARNING": 2, "INFO": 3}


class ScadaLayoutValidationError(ValueError):
    pass


class ScadaDraftNotFoundError(ValueError):
    pass


def _value(value: object) -> str:
    return str(getattr(value, "value", value))


def _is_live_device(device: Device) -> bool:
    return bool(device.is_enabled and not device.is_deleted and device.deleted_at is None)


def _is_live_sensor(sensor: Sensor, device: Device) -> bool:
    return bool(
        _is_live_device(device)
        and sensor.is_enabled
        and not sensor.is_deleted
        and sensor.deleted_at is None
    )


def _is_live_actuator(actuator: Actuator, device: Device) -> bool:
    return bool(
        _is_live_device(device)
        and actuator.is_enabled
        and not actuator.is_deleted
        and actuator.deleted_at is None
        and actuator.removed_at is None
    )


def _connectivity(device: Device) -> str:
    status = _value(device.status)
    if status == DeviceStatus.ONLINE.value:
        return "ONLINE"
    if status == DeviceStatus.WAITING_CONNECTION.value:
        return "WAITING_CONNECTION"
    if status == DeviceStatus.OFFLINE.value:
        return "OFFLINE"
    return "UNKNOWN"


def _sensor_symbol_type(code: str) -> str:
    normalized = code.upper()
    mapping = {
        "PH": "PH_SENSOR",
        "TEMP": "WATER_TEMPERATURE_SENSOR",
        "WATER_TEMPERATURE": "WATER_TEMPERATURE_SENSOR",
        "AIR_TEMPERATURE": "ENVIRONMENT_TEMPERATURE_SENSOR",
        "ENVIRONMENT_TEMPERATURE": "ENVIRONMENT_TEMPERATURE_SENSOR",
        "AIR_HUMIDITY": "HUMIDITY_SENSOR",
        "HUMIDITY": "HUMIDITY_SENSOR",
        "DO": "DISSOLVED_OXYGEN_SENSOR",
        "DISSOLVED_OXYGEN": "DISSOLVED_OXYGEN_SENSOR",
        "EC": "EC_SENSOR",
        "TDS": "TDS_SENSOR",
        "TDS_01": "TDS_SENSOR",
        "WATER_LEVEL": "WATER_LEVEL_SENSOR",
        "ILLUMINANCE": "LIGHT_SENSOR",
        "LIGHT": "LIGHT_SENSOR",
        "AIR_PRESSURE": "AIR_PRESSURE_SENSOR",
    }
    return mapping.get(normalized, "GENERIC_SENSOR")


def _actuator_symbol_type(code: str | None) -> str:
    normalized = (code or "").upper()
    if "AIR" in normalized and "PUMP" in normalized:
        return "AIR_PUMP"
    if "PUMP" in normalized or "MIST" in normalized:
        return "WATER_PUMP"
    if "VALVE" in normalized:
        return "VALVE"
    if "FAN" in normalized:
        return "FAN"
    if "LIGHT" in normalized:
        return "GROW_LIGHT"
    if "HEATER" in normalized:
        return "HEATER"
    return "GENERIC_ACTUATOR"


def _default_layout(devices: list[Device]) -> ScadaLayout:
    symbols = [
        ScadaSymbol(id="infra-fish-tank", type="FISH_TANK", label="Bể cá", position=(-7, 0, -3)),
        ScadaSymbol(id="infra-bio-filter", type="BIO_FILTER", label="Bể lọc", position=(-2.5, 0, -3)),
        ScadaSymbol(id="infra-grow-bed", type="GROW_BED", label="Khay trồng", position=(2, 0, -3)),
        ScadaSymbol(id="infra-sump-tank", type="SUMP_TANK", label="Bể thu hồi", position=(6.5, 0, -3)),
    ]
    connections = [
        ScadaConnection(id="pipe-fish-filter", type="WATER_PIPE", source_symbol_id="infra-fish-tank", target_symbol_id="infra-bio-filter", flow_direction="SOURCE_TO_TARGET"),
        ScadaConnection(id="pipe-filter-grow", type="WATER_PIPE", source_symbol_id="infra-bio-filter", target_symbol_id="infra-grow-bed", flow_direction="SOURCE_TO_TARGET"),
        ScadaConnection(id="pipe-grow-sump", type="WATER_PIPE", source_symbol_id="infra-grow-bed", target_symbol_id="infra-sump-tank", flow_direction="SOURCE_TO_TARGET"),
    ]
    controller_index = actuator_index = 0
    for device in devices:
        if not _is_live_device(device):
            continue
        position = (-6.5 + controller_index * 3.2, 0, 2.8)
        symbol_type = "CONTROLLER_DEVICE"
        controller_index += 1
        symbols.append(
            ScadaSymbol(
                id=f"device-{device.id}",
                type=symbol_type,
                label=device.name,
                position=position,
                binding=ScadaBinding(entity_type="DEVICE", entity_id=device.id),
            )
        )
        for actuator in device.actuators:
            if not _is_live_actuator(actuator, device):
                continue
            model_code = actuator.actuator_model.code if actuator.actuator_model else None
            symbols.append(
                ScadaSymbol(
                    id=f"actuator-{actuator.id}",
                    type=_actuator_symbol_type(model_code),
                    label=actuator.name,
                    position=(-5.5 + actuator_index * 3.1, 0, -0.2),
                    binding=ScadaBinding(entity_type="ACTUATOR", entity_id=actuator.id),
                )
            )
            actuator_index += 1
    return ScadaLayout(
        schema_version=1,
        camera={"type": "ORTHOGRAPHIC", "zoom": 1.0, "target": [0, 0, 0]},
        symbols=symbols,
        connections=connections,
    )


def _sensor_runtime(
    sensor: Sensor, reading: TelemetryReading | None, now: datetime
) -> ScadaRuntimeSensor:
    if reading is None:
        return ScadaRuntimeSensor(
            id=sensor.id,
            value=None,
            recorded_at=None,
            received_at=None,
            freshness="NO_DATA",
            quality="UNVALIDATED",
            quality_reason="Chưa nhận dữ liệu.",
        )
    received_at = reading.received_at
    if received_at.tzinfo is None:
        received_at = received_at.replace(tzinfo=timezone.utc)
    freshness = "FRESH" if now - received_at <= STALE_AFTER else "STALE"
    # Engineering quality is independent from operational Alert thresholds.
    # Threshold state comes from threshold_alert_configs/OperationalIncident.
    quality, reason, _, _ = classify_measurement_quality(sensor.sensor_model.code, reading.value)
    return ScadaRuntimeSensor(
        id=sensor.id,
        value=reading.value,
        recorded_at=reading.recorded_at,
        received_at=reading.received_at,
        freshness=freshness,
        quality=quality,
        quality_reason=reason,
    )


def _layout_bindings(layout: ScadaLayout) -> dict[str, set[int]]:
    result: dict[str, set[int]] = defaultdict(set)
    for symbol in layout.symbols:
        if symbol.binding:
            result[symbol.binding.entity_type].add(symbol.binding.entity_id)
    return result


def _validate_layout(layout: ScadaLayout, devices: list[Device]) -> list[str]:
    valid = {
        "DEVICE": {device.id for device in devices},
        "SENSOR": {sensor.id for device in devices for sensor in device.sensors},
        "ACTUATOR": {actuator.id for device in devices for actuator in device.actuators},
    }
    symbol_ids = [symbol.id for symbol in layout.symbols]
    if len(symbol_ids) != len(set(symbol_ids)):
        raise ScadaLayoutValidationError("ID symbol trong layout phải là duy nhất.")
    for symbol in layout.symbols:
        binding = symbol.binding
        if binding and binding.entity_id not in valid[binding.entity_type]:
            raise ScadaLayoutValidationError(
                f"Binding {binding.entity_type}:{binding.entity_id} không thuộc Project."
            )
    known_symbols = set(symbol_ids)
    for connection in layout.connections:
        if (
            connection.source_symbol_id not in known_symbols
            or connection.target_symbol_id not in known_symbols
        ):
            raise ScadaLayoutValidationError(
                f"Đường ống {connection.id} tham chiếu symbol không tồn tại."
            )
    bindings = _layout_bindings(layout)
    warnings: list[str] = []
    for device in devices:
        if not _is_live_device(device):
            continue
        if device.id not in bindings["DEVICE"]:
            warnings.append(f"Device {device.code} chưa được bố trí.")
        for actuator in device.actuators:
            if _is_live_actuator(actuator, device) and actuator.id not in bindings["ACTUATOR"]:
                warnings.append(f"Actuator {actuator.code} chưa được bố trí.")
    return warnings


async def get_scada_runtime(db: AsyncSession, project: Project) -> ScadaRuntimeResponse:
    devices = await project_scada_devices(db, project.id)
    all_sensors = [sensor for device in devices for sensor in device.sensors]
    all_actuators = [actuator for device in devices for actuator in device.actuators]
    readings = await latest_sensor_readings(db, [sensor.id for sensor in all_sensors])
    commands = await latest_actuator_commands(db, [actuator.id for actuator in all_actuators])
    alerts = await open_project_alerts(db, project.id)
    dashboard = await latest_scada_dashboard(db, project.id, "PUBLISHED")
    layout = (
        ScadaLayout.model_validate(dashboard.layout)
        if dashboard is not None
        else _default_layout(devices)
    )
    dashboard_info = ScadaDashboardInfo(
        id=dashboard.id if dashboard else None,
        status="PUBLISHED" if dashboard else "GENERATED",
        version=dashboard.version if dashboard else 0,
        schema_version=layout.schema_version,
    )
    now = datetime.now(timezone.utc)
    reading_by_sensor = {reading.sensor_id: reading for reading in readings}
    command_by_actuator = {command.actuator_id: command for command in commands}
    device_by_id = {device.id: device for device in devices}
    sensor_by_id = {sensor.id: sensor for sensor in all_sensors}

    inventory_devices: list[ScadaInventoryDevice] = []
    inventory_sensors: list[ScadaInventorySensor] = []
    inventory_actuators: list[ScadaInventoryActuator] = []
    runtime_devices: list[ScadaRuntimeDevice] = []
    runtime_sensors: list[ScadaRuntimeSensor] = []
    runtime_actuators: list[ScadaRuntimeActuator] = []
    issues: list[ScadaIssue] = []

    active_devices = [device for device in devices if _is_live_device(device)]
    active_sensors = [
        sensor
        for device in active_devices
        for sensor in device.sensors
        if _is_live_sensor(sensor, device)
    ]
    active_actuators = [
        actuator
        for device in active_devices
        for actuator in device.actuators
        if _is_live_actuator(actuator, device)
    ]
    active_sensor_ids = {sensor.id for sensor in active_sensors}
    active_actuator_ids = {actuator.id for actuator in active_actuators}
    active_alerts = [alert for alert in alerts if alert.sensor_id in active_sensor_ids or alert.actuator_id in active_actuator_ids]
    alerts_by_sensor: dict[int, list[OperationalIncident]] = defaultdict(list)
    for alert in active_alerts:
        if alert.sensor_id is not None: alerts_by_sensor[alert.sensor_id].append(alert)

    for device in devices:
        template = device.device_template
        item = ScadaInventoryDevice(
            id=device.id,
            code=device.code,
            name=device.name,
            device_template_id=device.device_template_id,
            template_code=template.code if template else None,
            enabled=_is_live_device(device),
            connectivity=_connectivity(device) if _is_live_device(device) else "DISABLED",
            last_seen_at=device.last_seen_at,
        )
        inventory_devices.append(item)
        runtime_devices.append(
            ScadaRuntimeDevice(
                id=device.id,
                connectivity=item.connectivity,
                last_seen_at=device.last_seen_at,
            )
        )
        if not _is_live_device(device):
            issues.append(
                ScadaIssue(
                    id=f"device-{device.id}-disabled",
                    severity="INFO",
                    title="Thiết bị đã vô hiệu hóa",
                    root_cause=device.name,
                    affected_entities=[sensor.name for sensor in device.sensors],
                    current_state=f"{len(device.sensors)} phép đo bị ảnh hưởng.",
                    timestamp=device.disabled_at,
                    suggested_action="Kiểm tra lý do vô hiệu hóa trong trang thiết bị.",
                    device_id=device.id,
                )
            )
        elif item.connectivity == "OFFLINE":
            affected_sensors = [sensor for sensor in device.sensors if _is_live_sensor(sensor, device)]
            affected_actuators = [actuator for actuator in device.actuators if _is_live_actuator(actuator, device)]
            issues.append(
                ScadaIssue(
                    id=f"device-{device.id}-offline",
                    severity="HIGH",
                    title="Thiết bị mất kết nối",
                    root_cause=device.name,
                    affected_entities=[item.name for item in [*affected_sensors, *affected_actuators]],
                    current_state=f"{len(affected_sensors)} phép đo gián đoạn, {len(affected_actuators)} cơ cấu không thể điều khiển.",
                    timestamp=device.last_seen_at,
                    suggested_action="Kiểm tra nguồn, mạng LAN và kết nối MQTT của thiết bị.",
                    device_id=device.id,
                )
            )

        for sensor in device.sensors:
            enabled = _is_live_sensor(sensor, device)
            inventory_sensors.append(
                ScadaInventorySensor(
                    id=sensor.id,
                    code=sensor.code,
                    name=sensor.name,
                    sensor_model_code=sensor.sensor_model.code,
                    unit=sensor.sensor_model.unit,
                    device_id=device.id,
                    enabled=enabled,
                )
            )
            sensor_state = _sensor_runtime(sensor, reading_by_sensor.get(sensor.id), now)
            runtime_sensors.append(sensor_state)
            if not enabled:
                continue
            sensor_alerts = alerts_by_sensor.get(sensor.id, [])
            if sensor_alerts:
                alert = min(sensor_alerts, key=lambda item: SEVERITY_ORDER.get(item.technical_severity, 9))
                severity = alert.technical_severity
                issues.append(
                    ScadaIssue(
                        id=f"sensor-{sensor.id}-alert",
                        severity=severity if severity in SEVERITY_ORDER else "WARNING",
                        title=str((alert.trigger_snapshot or {}).get("message") or "Cảnh báo Sensor"),
                        root_cause=sensor.name,
                        affected_entities=[device.name, sensor.name],
                        current_state=(
                            f"{sensor_state.value} {sensor.sensor_model.unit} · "
                            f"{sensor_state.freshness} · {sensor_state.quality}"
                            if sensor_state.value is not None
                            else "Chưa có dữ liệu mới."
                        ),
                        timestamp=alert.started_at,
                        suggested_action="Kiểm tra cảm biến, hiệu chuẩn và ngưỡng cảnh báo.",
                        device_id=device.id,
                        sensor_id=sensor.id,
                    )
                )
            elif sensor_state.quality in ("OUT_OF_RANGE", "INVALID"):
                issues.append(
                    ScadaIssue(
                        id=f"sensor-{sensor.id}-quality",
                        severity="WARNING",
                        title="Dữ liệu ngoài miền hợp lệ",
                        root_cause=sensor.name,
                        affected_entities=[device.name, sensor.name],
                        current_state=f"{sensor_state.value} {sensor.sensor_model.unit}",
                        timestamp=sensor_state.received_at,
                        suggested_action="Kiểm tra cảm biến, hiệu chuẩn và ngưỡng cấu hình.",
                        device_id=device.id,
                        sensor_id=sensor.id,
                    )
                )

        for actuator in device.actuators:
            enabled = _is_live_actuator(actuator, device)
            model_code = actuator.actuator_model.code if actuator.actuator_model else None
            inventory_actuators.append(
                ScadaInventoryActuator(
                    id=actuator.id,
                    code=actuator.code,
                    name=actuator.name,
                    actuator_model_code=model_code,
                    device_id=device.id,
                    enabled=enabled,
                )
            )
            sync = (
                "UNKNOWN"
                if actuator.desired_state is None or actuator.reported_state is None
                else "IN_SYNC"
                if actuator.desired_state == actuator.reported_state
                else "OUT_OF_SYNC"
            )
            command = command_by_actuator.get(actuator.id)
            command_status = command.status if command else None
            runtime_actuators.append(
                ScadaRuntimeActuator(
                    id=actuator.id,
                    desired_state=actuator.desired_state,
                    reported_state=actuator.reported_state,
                    synchronization=sync,
                    command_status=command_status,
                    command_time=command.requested_at if command else actuator.last_command_at,
                    last_ack_at=command.acknowledged_at if command else None,
                    failure_reason=command.failure_reason if command else None,
                )
            )
            if not enabled:
                continue
            if command_status in ("TIMEOUT", "FAILED"):
                issues.append(
                    ScadaIssue(
                        id=f"actuator-{actuator.id}-{command_status.lower()}",
                        severity="CRITICAL",
                        title=f"{actuator.name} không phản hồi lệnh",
                        root_cause=f"Lệnh gần nhất: {command_status}",
                        affected_entities=[device.name, actuator.name],
                        current_state=f"Mong muốn: {actuator.desired_state}; thực tế: {actuator.reported_state}; ACK: {'đã nhận' if command and command.acknowledged_at else 'chưa nhận'}.",
                        timestamp=command.requested_at if command else actuator.last_command_at,
                        suggested_action="Kiểm tra kết nối Device và cơ cấu chấp hành trước khi gửi lại lệnh.",
                        device_id=device.id,
                        actuator_id=actuator.id,
                    )
                )
            elif sync == "OUT_OF_SYNC":
                issues.append(
                    ScadaIssue(
                        id=f"actuator-{actuator.id}-out-of-sync",
                        severity="HIGH",
                        title="Trạng thái cơ cấu chưa đồng bộ",
                        root_cause=actuator.name,
                        affected_entities=[device.name, actuator.name],
                        current_state=f"Mong muốn: {actuator.desired_state}; thực tế: {actuator.reported_state}.",
                        timestamp=actuator.last_reported_at,
                        suggested_action="Kiểm tra trạng thái reported và kết nối điều khiển.",
                        device_id=device.id,
                        actuator_id=actuator.id,
                    )
                )

    bindings = _layout_bindings(layout)
    unplaced: list[ScadaUnplacedEntity] = []
    for device in active_devices:
        if device.id not in bindings["DEVICE"]:
            template = device.device_template
            unplaced.append(
                ScadaUnplacedEntity(
                    entity_type="DEVICE",
                    entity_id=device.id,
                    name=device.name,
                    code=device.code,
                    suggested_symbol_type="CONTROLLER_DEVICE",
                    reason="Device active chưa có symbol trong layout.",
                )
            )
        for actuator in device.actuators:
            if _is_live_actuator(actuator, device) and actuator.id not in bindings["ACTUATOR"]:
                unplaced.append(
                    ScadaUnplacedEntity(
                        entity_type="ACTUATOR",
                        entity_id=actuator.id,
                        name=actuator.name,
                        code=actuator.code,
                        parent_device_id=device.id,
                        suggested_symbol_type=_actuator_symbol_type(actuator.actuator_model.code if actuator.actuator_model else None),
                        reason="Actuator active chưa có symbol riêng.",
                    )
                )
        if device.id not in bindings["DEVICE"]:
            for sensor in device.sensors:
                if _is_live_sensor(sensor, device) and sensor.id not in bindings["SENSOR"]:
                    unplaced.append(
                        ScadaUnplacedEntity(
                            entity_type="SENSOR",
                            entity_id=sensor.id,
                            name=sensor.name,
                            code=sensor.code,
                            parent_device_id=device.id,
                            suggested_symbol_type=_sensor_symbol_type(sensor.sensor_model.code),
                            reason="Sensor chưa có symbol và Device cha chưa được bố trí.",
                        )
                    )

    active_connections = any(actuator.reported_state is True for actuator in active_actuators)
    layout = layout.model_copy(
        update={
            "connections": [
                connection.model_copy(update={"active": active_connections})
                for connection in layout.connections
            ]
        }
    )
    sensor_states = {state.id: state for state in runtime_sensors}
    active_sensor_states = [sensor_states[sensor.id] for sensor in active_sensors]
    actuator_states = {state.id: state for state in runtime_actuators}
    active_actuator_states = [actuator_states[item.id] for item in active_actuators]
    connectivities = [_connectivity(device) for device in active_devices]
    alert_runtime = [
        ScadaRuntimeAlert(
            id=alert.id,
            resource_type=(alert.trigger_snapshot or {}).get("resource_type") or ("ACTUATOR" if alert.actuator_id else "SENSOR"),
            sensor_id=alert.sensor_id,
            actuator_id=alert.actuator_id,
            device_id=alert.device_id,
            severity=alert.technical_severity,
            status=alert.status,
            title=str((alert.trigger_snapshot or {}).get("message") or (alert.trigger_snapshot or {}).get("rule_name") or "Cảnh báo vận hành"),
            value=(alert.trigger_snapshot or {}).get("value"),
            timestamp=alert.started_at,
        )
        for alert in active_alerts
    ]
    issues.sort(key=lambda issue: (SEVERITY_ORDER[issue.severity], -(issue.timestamp.timestamp() if issue.timestamp else 0)))
    summary = ScadaSummary(
        active_devices_total=len(active_devices),
        connected_devices=connectivities.count("ONLINE"),
        waiting_devices=connectivities.count("WAITING_CONNECTION"),
        disconnected_devices=connectivities.count("OFFLINE"),
        unknown_connectivity_devices=connectivities.count("UNKNOWN"),
        disabled_devices=len(devices) - len(active_devices),
        active_sensors_total=len(active_sensors),
        fresh_sensors=sum(state.freshness == "FRESH" for state in active_sensor_states),
        fresh_valid_sensors=sum(state.freshness == "FRESH" and state.quality == "VALID" for state in active_sensor_states),
        fresh_invalid_sensors=sum(state.freshness == "FRESH" and state.quality in ("OUT_OF_RANGE", "INVALID") for state in active_sensor_states),
        stale_sensors=sum(state.freshness == "STALE" for state in active_sensor_states),
        no_data_sensors=sum(state.freshness == "NO_DATA" for state in active_sensor_states),
        disabled_sensors=len(all_sensors) - len(active_sensors),
        active_actuators_total=len(active_actuators),
        actuators_on=sum(state.reported_state is True for state in active_actuator_states),
        actuators_off=sum(state.reported_state is False for state in active_actuator_states),
        actuators_out_of_sync=sum(state.synchronization == "OUT_OF_SYNC" for state in active_actuator_states),
        commands_pending=sum(state.command_status in ("PENDING", "PUBLISHED") for state in active_actuator_states),
        commands_failed=sum(state.command_status == "FAILED" for state in active_actuator_states),
        commands_timeout=sum(state.command_status == "TIMEOUT" for state in active_actuator_states),
        disabled_actuators=len(all_actuators) - len(active_actuators),
        open_alerts=len(active_alerts),
        critical_alerts=sum(alert.severity == "CRITICAL" for alert in alert_runtime),
        warning_alerts=sum(alert.severity == "WARNING" for alert in alert_runtime),
        unplaced_entities=len(unplaced),
    )
    return ScadaRuntimeResponse(
        aquaponics_system={"id": project.id, "name": project.name, "code": project.code, "status": project.status},
        dashboard=dashboard_info,
        layout=layout,
        inventory=ScadaInventory(
            devices=inventory_devices,
            sensors=inventory_sensors,
            actuators=inventory_actuators,
        ),
        runtime=ScadaRuntimeState(
            devices=runtime_devices,
            sensors=runtime_sensors,
            actuators=runtime_actuators,
            alerts=alert_runtime,
        ),
        summary=summary,
        issues=issues,
        unplaced_entities=unplaced,
        updated_at=now,
    )


async def save_scada_draft(
    db: AsyncSession, project: Project, actor: User, layout: ScadaLayout
) -> ScadaLayoutMutationResponse:
    devices = await project_scada_devices(db, project.id)
    warnings = _validate_layout(layout, devices)
    persisted_layout = layout.model_copy(
        update={
            "connections": [
                connection.model_copy(update={"active": False})
                for connection in layout.connections
            ]
        }
    )
    draft = await latest_scada_dashboard(db, project.id, "DRAFT")
    if draft is None:
        draft = ScadaDashboard(
            project_id=project.id,
            status="DRAFT",
            version=await next_scada_dashboard_version(db, project.id),
            schema_version=persisted_layout.schema_version,
            layout=persisted_layout.model_dump(mode="json"),
            created_by_user_id=actor.id,
        )
        db.add(draft)
    else:
        draft.schema_version = persisted_layout.schema_version
        draft.layout = persisted_layout.model_dump(mode="json")
        draft.created_by_user_id = actor.id
    activity = await record_project_activity(db, project_id=project.id, actor=actor, action="SCADA_LAYOUT_UPDATED", entity_type="SCADA", entity_id=draft.id, entity_name="Sơ đồ vận hành", changes={"version": {"before": None, "after": draft.version}})
    await db.commit()
    await db.refresh(draft)
    await dispatch_project_activity(db, activity_id=activity.id)
    return ScadaLayoutMutationResponse(
        dashboard=ScadaDashboardInfo(
            id=draft.id,
            status="DRAFT",
            version=draft.version,
            schema_version=draft.schema_version,
        ),
        layout=persisted_layout,
        warnings=warnings,
    )


async def publish_scada_draft(
    db: AsyncSession, project: Project, actor: User
) -> ScadaLayoutMutationResponse:
    draft = await latest_scada_dashboard(db, project.id, "DRAFT")
    if draft is None:
        raise ScadaDraftNotFoundError("Chưa có bản nháp SCADA để xuất bản.")
    layout = ScadaLayout.model_validate(draft.layout)
    devices = await project_scada_devices(db, project.id)
    warnings = _validate_layout(layout, devices)
    published = ScadaDashboard(
        project_id=project.id,
        status="PUBLISHED",
        version=await next_scada_dashboard_version(db, project.id),
        schema_version=layout.schema_version,
        layout=layout.model_dump(mode="json"),
        created_by_user_id=actor.id,
        published_at=datetime.now(timezone.utc),
    )
    db.add(published)
    await db.flush()
    activity = await record_project_activity(db, project_id=project.id, actor=actor, action="SCADA_LAYOUT_PUBLISHED", entity_type="SCADA", entity_id=published.id, entity_name="Sơ đồ vận hành", changes={"version": {"before": draft.version, "after": published.version}})
    await db.commit()
    await db.refresh(published)
    await dispatch_project_activity(db, activity_id=activity.id)
    return ScadaLayoutMutationResponse(
        dashboard=ScadaDashboardInfo(
            id=published.id,
            status="PUBLISHED",
            version=published.version,
            schema_version=published.schema_version,
        ),
        layout=layout,
        warnings=warnings,
    )
