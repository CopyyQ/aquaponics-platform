from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.project_overview import (
    ActuatorActiveAlertRead,
    ActuatorElectricalRead,
)

from app.core.enums import DeviceStatus, MonitoringRange, SensorStatus


class MonitoringLatestValue(BaseModel):
    value: float
    recorded_at: datetime
    quality: str = "UNVALIDATED"
    quality_reason: str | None = None
    engineering_min: float | None = None
    engineering_max: float | None = None
    freshness: str = "FRESH"


class MonitoringSensor(BaseModel):
    id: UUID
    code: str
    name: str
    unit: str
    is_enabled: bool
    connection_status: SensorStatus
    data_status: SensorStatus
    latest: MonitoringLatestValue | None
    lower_threshold: float | None
    upper_threshold: float | None
    threshold_state: str = "UNCONFIGURED"
    alerts_enabled: bool = True


class MonitoringLatestCommand(BaseModel):
    status: str
    requested_at: datetime


class MonitoringActuator(BaseModel):
    id: UUID
    code: str
    name: str
    actuator_model: str | None
    connection_status: DeviceStatus
    desired_state: bool | None
    reported_state: bool | None
    synchronization_status: str
    latest_command: MonitoringLatestCommand | None
    last_reported_at: datetime | None
    electrical: ActuatorElectricalRead
    active_alert: ActuatorActiveAlertRead | None


class MonitoringDevice(BaseModel):
    id: UUID
    code: str
    name: str
    is_enabled: bool
    connection_status: DeviceStatus
    location: str | None
    last_seen_at: datetime | None
    sensors: list[MonitoringSensor]
    actuators: list[MonitoringActuator]


class MonitoringLatestRead(BaseModel):
    aquaponics_system_id: UUID
    devices: list[MonitoringDevice]


class ProjectHealthReason(BaseModel):
    code: str
    severity: str
    message: str


class ProjectHealth(BaseModel):
    status: str
    label: str
    reasons: list[ProjectHealthReason]


class ProjectInventorySummary(BaseModel):
    devices_total: int
    devices_enabled: int
    devices_online: int
    devices_offline: int
    devices_waiting: int
    sensors_total: int
    sensors_enabled: int
    sensors_reporting: int
    sensors_stale: int
    sensors_offline: int
    members_total: int = 0


class ProjectFreshness(BaseModel):
    last_received_at: datetime | None
    reporting_sensors: int
    expected_sensors: int
    coverage_ratio: float


class ProjectAttentionItem(BaseModel):
    id: str
    severity: str
    title: str
    description: str
    device_id: int | None = None
    sensor_id: int | None = None
    last_seen_at: datetime | None = None


class ProjectMeasurementGroup(BaseModel):
    model_code: str
    name: str
    unit: str
    reporting_sensors: int
    expected_sensors: int
    latest_value: float | None
    minimum_value: float | None
    maximum_value: float | None
    latest_at: datetime | None
    stale: bool
    counter: bool
    sensor_id: int | None = None
    device_id: int | None = None
    quality: str = "UNVALIDATED"
    quality_reason: str | None = None
    engineering_min: float | None = None
    engineering_max: float | None = None


class ProjectActuatorHealth(BaseModel):
    id: int
    device_id: int
    device_name: str
    device_code: str
    code: str
    name: str
    actuator_model: str | None
    is_enabled: bool
    connection_status: str
    desired_state: bool | None
    reported_state: bool | None
    synchronization_status: str
    command_status: str | None
    last_command_at: datetime | None
    last_ack_at: datetime | None
    last_reported_at: datetime | None


class ProjectDeviceHealth(BaseModel):
    id: int
    code: str
    name: str
    status: DeviceStatus
    is_enabled: bool
    last_seen_at: datetime | None
    sensor_count: int
    reporting_sensor_count: int
    stale_sensor_count: int
    offline_sensor_count: int
    open_alert_count: int


class ProjectRecentAlert(BaseModel):
    id: int
    sensor_id: int
    sensor_name: str
    device_id: int
    device_name: str
    severity: str
    status: str
    message: str
    trigger_value: float | None
    condition_active: bool
    normalized_at: datetime | None
    resolved_by_user_id: int | None
    started_at: datetime


class ProjectBusinessAlert(BaseModel):
    id: int
    risk: str
    rule_name: str
    started_at: datetime
    duration_seconds: int
    message: str
    condition: str
    value: float | None
    unit: str | None
    device_name: str | None
    device_code: str | None
    sensor_name: str | None
    sensor_code: str | None
    actuator_name: str | None
    actuator_code: str | None
    desired_state: bool | None
    reported_state: bool | None
    current_a: float | None
    lower: float | None
    upper: float | None
    threshold: float | None
    operator: str | None


class ProjectBusinessAlerts(BaseModel):
    counts: dict[str, int]
    items: list[ProjectBusinessAlert]


class ProjectMonitoringSummaryResponse(BaseModel):
    project_id: int
    health: ProjectHealth
    inventory: ProjectInventorySummary
    alerts: dict[str, int]
    freshness: ProjectFreshness
    attention: list[ProjectAttentionItem]
    measurement_groups: list[ProjectMeasurementGroup]
    device_health: list[ProjectDeviceHealth]
    recent_alerts: list[ProjectRecentAlert]
    business_alerts: ProjectBusinessAlerts
    actuators: list[ProjectActuatorHealth] = []
    actuator_inventory: dict[str, int] = {}


class MonitoringSeriesPoint(BaseModel):
    recorded_at: datetime
    value: float


class MonitoringDataGap(BaseModel):
    from_: datetime = Field(alias="from")
    to: datetime
    reason: str

    model_config = {"populate_by_name": True}


class MonitoringSensorSeries(BaseModel):
    sensor_id: UUID
    unit: str
    points: list[MonitoringSeriesPoint]
    gaps: list[MonitoringDataGap]


class MonitoringSeriesRead(BaseModel):
    aquaponics_system_id: UUID
    range: MonitoringRange
    resolution: str
    series: list[MonitoringSensorSeries]


class DevicePowerPoint(BaseModel):
    bucket_time: datetime
    avg_value: float
    min_value: float
    max_value: float
    reading_count: int


class DevicePowerSeriesResponse(BaseModel):
    project_id: int
    device_id: int
    range: MonitoringRange
    resolution: str
    timezone: str
    unit: str
    points: list[DevicePowerPoint]


class ActuatorHistoryPoint(BaseModel):
    recorded_at: datetime
    state: bool


class ActuatorHistoryGap(BaseModel):
    from_: datetime = Field(alias="from")
    to: datetime
    reason: str

    model_config = {"populate_by_name": True}


class ActuatorHistoryStatistics(BaseModel):
    on_duration_seconds: int
    off_duration_seconds: int
    unknown_duration_seconds: int
    on_percentage: float | None
    on_count: int
    off_count: int
    last_changed_at: datetime | None


class MonitoringActuatorHistory(BaseModel):
    actuator_id: UUID
    points: list[ActuatorHistoryPoint]
    gaps: list[ActuatorHistoryGap]
    statistics: ActuatorHistoryStatistics


class ProjectMonitoringActuatorHistoryResponse(BaseModel):
    project_id: int
    device_id: int
    range: MonitoringRange
    items: list[MonitoringActuatorHistory]


class MonitoringActuatorHistoryRead(BaseModel):
    aquaponics_system_id: UUID
    device_id: UUID
    range: MonitoringRange
    items: list[MonitoringActuatorHistory]
