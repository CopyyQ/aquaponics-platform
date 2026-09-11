from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


EntityType = Literal["DEVICE", "SENSOR", "ACTUATOR"]


class ScadaBinding(BaseModel):
    entity_type: EntityType
    entity_id: UUID


class ScadaSymbol(BaseModel):
    id: str
    type: str
    label: str
    position: tuple[float, float, float]
    binding: ScadaBinding | None = None


class ScadaConnection(BaseModel):
    id: str
    type: Literal["WATER_PIPE", "AIR_PIPE"]
    source_symbol_id: str
    target_symbol_id: str
    flow_direction: Literal["SOURCE_TO_TARGET"]
    active: bool = False


class ScadaLayout(BaseModel):
    schema_version: int = 1
    camera: dict[str, object] = Field(default_factory=dict)
    symbols: list[ScadaSymbol] = Field(default_factory=list)
    connections: list[ScadaConnection] = Field(default_factory=list)


class ScadaDashboardInfo(BaseModel):
    id: int | None
    status: Literal["GENERATED", "DRAFT", "PUBLISHED"]
    version: int
    schema_version: int


class ScadaInventoryDevice(BaseModel):
    id: UUID
    code: str
    name: str
    device_template_id: int | None
    template_code: str | None
    enabled: bool
    connectivity: str
    last_seen_at: datetime | None


class ScadaInventorySensor(BaseModel):
    id: UUID
    code: str
    name: str
    sensor_model_code: str
    unit: str
    device_id: UUID
    enabled: bool


class ScadaInventoryActuator(BaseModel):
    id: UUID
    code: str
    name: str
    actuator_model_code: str | None
    device_id: UUID
    enabled: bool


class ScadaInventory(BaseModel):
    devices: list[ScadaInventoryDevice]
    sensors: list[ScadaInventorySensor]
    actuators: list[ScadaInventoryActuator]


class ScadaRuntimeDevice(BaseModel):
    id: UUID
    connectivity: str
    last_seen_at: datetime | None


class ScadaRuntimeSensor(BaseModel):
    id: UUID
    value: float | None
    recorded_at: datetime | None
    received_at: datetime | None
    freshness: Literal["FRESH", "STALE", "NO_DATA"]
    quality: Literal["VALID", "OUT_OF_RANGE", "INVALID", "UNVALIDATED"]
    quality_reason: str | None


class ScadaRuntimeActuator(BaseModel):
    id: UUID
    desired_state: bool | None
    reported_state: bool | None
    synchronization: Literal["IN_SYNC", "OUT_OF_SYNC", "UNKNOWN"]
    command_status: str | None
    command_time: datetime | None
    last_ack_at: datetime | None
    failure_reason: str | None


class ScadaRuntimeAlert(BaseModel):
    id: int
    resource_type: Literal["SENSOR", "ACTUATOR"]
    sensor_id: UUID | None
    actuator_id: UUID | None
    device_id: UUID | None
    severity: str
    status: str
    title: str
    value: float | None
    timestamp: datetime


class ScadaRuntimeState(BaseModel):
    devices: list[ScadaRuntimeDevice]
    sensors: list[ScadaRuntimeSensor]
    actuators: list[ScadaRuntimeActuator]
    alerts: list[ScadaRuntimeAlert]


class ScadaIssue(BaseModel):
    id: str
    severity: Literal["CRITICAL", "HIGH", "WARNING", "INFO"]
    title: str
    root_cause: str
    affected_entities: list[str]
    current_state: str
    timestamp: datetime | None
    suggested_action: str
    device_id: UUID | None = None
    sensor_id: UUID | None = None
    actuator_id: UUID | None = None


class ScadaUnplacedEntity(BaseModel):
    entity_type: EntityType
    entity_id: UUID
    name: str
    code: str
    parent_device_id: UUID | None = None
    suggested_symbol_type: str
    reason: str


class ScadaSummary(BaseModel):
    active_devices_total: int
    connected_devices: int
    waiting_devices: int
    disconnected_devices: int
    unknown_connectivity_devices: int
    disabled_devices: int
    active_sensors_total: int
    fresh_sensors: int
    fresh_valid_sensors: int
    fresh_invalid_sensors: int
    stale_sensors: int
    no_data_sensors: int
    disabled_sensors: int
    active_actuators_total: int
    actuators_on: int
    actuators_off: int
    actuators_out_of_sync: int
    commands_pending: int
    commands_failed: int
    commands_timeout: int
    disabled_actuators: int
    open_alerts: int
    critical_alerts: int
    warning_alerts: int
    unplaced_entities: int


class ScadaAquaponicsSystem(BaseModel):
    id: UUID
    code: str
    name: str
    status: str


class ScadaRuntimeResponse(BaseModel):
    aquaponics_system: ScadaAquaponicsSystem
    dashboard: ScadaDashboardInfo
    layout: ScadaLayout
    inventory: ScadaInventory
    runtime: ScadaRuntimeState
    summary: ScadaSummary
    issues: list[ScadaIssue]
    unplaced_entities: list[ScadaUnplacedEntity]
    updated_at: datetime


class ScadaLayoutMutationResponse(BaseModel):
    dashboard: ScadaDashboardInfo
    layout: ScadaLayout
    warnings: list[str] = Field(default_factory=list)
