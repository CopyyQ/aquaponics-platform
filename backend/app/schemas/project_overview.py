from datetime import datetime
from typing import Literal

from pydantic import BaseModel

from app.schemas.device import DeviceRead
from app.schemas.project import ProjectRead


class ProjectOverviewOwner(BaseModel):
    id: int
    full_name: str
    email: str


class ProjectHealthReason(BaseModel):
    code: str
    severity: str
    message: str


class ProjectHealthRead(BaseModel):
    status: str
    label: str
    reasons: list[ProjectHealthReason]


class ProjectInventoryRead(BaseModel):
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
    members_total: int


class ProjectAlertSummaryRead(BaseModel):
    open_total: int
    critical_open: int
    warning_open: int


class ProjectFreshnessRead(BaseModel):
    last_received_at: datetime | None
    reporting_sensors: int
    expected_sensors: int
    coverage_ratio: float


class ProjectAttentionRead(BaseModel):
    id: str
    severity: str
    title: str
    description: str
    device_id: int | None = None
    sensor_id: int | None = None
    last_seen_at: datetime | None = None


class ProjectMeasurementGroupRead(BaseModel):
    model_code: str
    name: str
    unit: str
    reporting_sensors: int
    expected_sensors: int
    latest_value: float | None = None
    minimum_value: float | None = None
    maximum_value: float | None = None
    latest_at: datetime | None = None
    stale: bool
    counter: bool
    sensor_id: int | None = None
    device_id: int | None = None
    quality: str
    quality_reason: str | None = None
    engineering_min: float | None = None
    engineering_max: float | None = None


class ProjectDeviceHealthRead(BaseModel):
    id: int
    code: str
    name: str
    status: str
    is_enabled: bool
    last_seen_at: datetime | None
    sensor_count: int
    reporting_sensor_count: int
    stale_sensor_count: int
    offline_sensor_count: int
    open_alert_count: int


class ProjectRecentAlertRead(BaseModel):
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


class ActuatorLatestCommandRead(BaseModel):
    status: str
    requested_at: datetime


class ActuatorElectricalMetricRead(BaseModel):
    configured: bool
    sensor_id: int | None
    sensor_code: str | None = None
    sensor_name: str | None = None
    sensor_model_code: str | None = None
    source_device_id: int | None = None
    source_device_code: str | None = None
    source_device_name: str | None = None
    value_key: str | None = None
    value: float | None
    unit: Literal["V", "A"]
    quality: Literal["VALID", "OUT_OF_RANGE", "INVALID", "NO_DATA", "UNVALIDATED"]
    freshness: Literal["FRESH", "STALE", "NO_DATA"]
    recorded_at: datetime | None
    received_at: datetime | None
    lower_threshold: float | None
    upper_threshold: float | None
    threshold_source: Literal["ACTUATOR_OVERRIDE", "MODEL_DEFAULT", "NONE"] = "NONE"
    threshold_status: Literal["BELOW_RANGE", "ABOVE_RANGE", "IN_RANGE", "NO_DATA", "STALE", "INVALID", "UNCONFIGURED"] = "UNCONFIGURED"


class ActuatorElectricalRead(BaseModel):
    voltage: ActuatorElectricalMetricRead
    current: ActuatorElectricalMetricRead
    configured: bool
    sensor_id: int | None
    current_a: float | None
    quality: Literal["VALID", "OUT_OF_RANGE", "INVALID", "NO_DATA", "UNVALIDATED"]
    freshness: Literal["FRESH", "STALE", "NO_DATA"]
    recorded_at: datetime | None
    received_at: datetime | None
    minimum_running_current_a: float | None
    maximum_running_current_a: float | None


class ActuatorOperationalConclusionRead(BaseModel):
    code: str
    label: str
    explanation: str


class ActuatorActiveIncidentRead(BaseModel):
    id: int
    technical_severity: Literal["WARNING", "CRITICAL"]
    business_risk_level: str
    status: str
    rule_name: str
    evaluator_type: str
    condition_summary: str
    started_at: datetime
    duration_seconds: int
    evidence: dict[str, object]


class ProjectOverviewActuatorRead(BaseModel):
    id: int
    device_id: int
    device_name: str
    name: str
    is_enabled: bool
    connection_status: str
    desired_state: bool | None
    reported_state: bool | None
    synchronization_status: str
    command_status: str | None
    last_command_at: datetime | None
    last_ack_at: datetime | None
    last_reported_at: datetime | None
    latest_command: ActuatorLatestCommandRead | None
    electrical: ActuatorElectricalRead
    operational_conclusion: ActuatorOperationalConclusionRead
    active_incident: ActuatorActiveIncidentRead | None


class ActuatorInventoryRead(BaseModel):
    total: int
    responding: int
    out_of_sync: int
    disconnected: int
    failed: int


class EnergyDeviceSummaryRead(BaseModel):
    id: int
    name: str
    status: str


class EnergyDevicesSummaryRead(BaseModel):
    count: int
    items: list[EnergyDeviceSummaryRead]


class CriticalIssueRead(BaseModel):
    message: str


class ProjectOverviewResponse(BaseModel):
    project: ProjectRead
    owner: ProjectOverviewOwner | None
    member_count: int
    device_count: int
    online_device_count: int
    offline_device_count: int
    sensor_count: int
    offline_sensor_count: int
    open_alert_count: int
    last_telemetry_at: datetime | None
    health: ProjectHealthRead
    inventory: ProjectInventoryRead
    alerts: ProjectAlertSummaryRead
    freshness: ProjectFreshnessRead
    attention: list[ProjectAttentionRead]
    measurement_groups: list[ProjectMeasurementGroupRead]
    device_health: list[ProjectDeviceHealthRead]
    recent_alerts: list[ProjectRecentAlertRead]
    critical_issues: list[CriticalIssueRead]
    devices_summary: list[DeviceRead]
    energy_devices_summary: EnergyDevicesSummaryRead
    actuators: list[ProjectOverviewActuatorRead]
    actuator_inventory: ActuatorInventoryRead
