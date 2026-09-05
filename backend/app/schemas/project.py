from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.device import DeviceRead
from app.core.enums import DeviceStatus, ProjectStatus, SensorStatus


class ProjectCreate(BaseModel):
    owner_user_id: int
    code: str = Field(pattern=r"^[A-Z0-9_-]+$", min_length=3, max_length=80)
    name: str = Field(min_length=2, max_length=255)
    location: str | None = Field(default=None, max_length=255)
    description: str | None = None
    status: ProjectStatus = ProjectStatus.ACTIVE

    @field_validator("code", mode="before")
    @classmethod
    def normalize_code(cls, value: str) -> str:
        return str(value).strip().upper()

    @field_validator("name", mode="before")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        return str(value).strip()


class AdminProjectCreate(BaseModel):
    code: str = Field(pattern=r"^[A-Z0-9_-]+$", min_length=3, max_length=80)
    name: str = Field(min_length=2, max_length=255)
    location: str | None = Field(default=None, max_length=255)
    description: str | None = None

    @field_validator("code", mode="before")
    @classmethod
    def normalize_code(cls, value: str) -> str:
        return str(value).strip().upper()

    @field_validator("name", mode="before")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        return str(value).strip()


class ProjectUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=255)
    location: str | None = Field(default=None, max_length=255)
    description: str | None = None
    status: ProjectStatus | None = None


class ProjectDisableRequest(BaseModel):
    reason: str = Field(min_length=3, max_length=1000)


class DeviceFromTemplateRequest(BaseModel):
    device_template_id: int = Field(gt=0)
    code: str | None = Field(default=None, pattern=r"^[A-Z0-9_-]+$", min_length=3, max_length=80)
    name: str | None = Field(default=None, min_length=2, max_length=255)
    location: str | None = Field(default=None, max_length=255)
    description: str | None = None


class ProjectRead(ProjectCreate):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    updated_at: datetime
    disabled_at: datetime | None = None
    disabled_by_user_id: int | None = None
    disabled_reason: str | None = None


class AdminUserProjectRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    code: str
    location: str | None
    status: ProjectStatus
    device_count: int
    sensor_count: int
    open_alert_count: int
    latest_telemetry_at: datetime | None


class AdminUserProjectListResponse(BaseModel):
    items: list[AdminUserProjectRead]
    total: int


class ProjectDeviceManagementRead(DeviceRead):
    sensor_count: int = 0
    actuator_count: int = 0


class DeviceListResponse(BaseModel):
    items: list[ProjectDeviceManagementRead]
    total: int


class DeviceConfigOwner(BaseModel):
    id: int
    full_name: str


class DeviceConfigProject(BaseModel):
    id: int
    code: str
    name: str
    owner: DeviceConfigOwner


class DeviceConfigMqtt(BaseModel):
    host: str
    port: int
    authentication: bool
    tls: bool


class DeviceConfigTopics(BaseModel):
    telemetry: str
    status: str


class DeviceConfigSensor(BaseModel):
    id: int
    sensor_code: str
    sensor_model_code: str
    name: str
    unit: str
    is_enabled: bool
    status: SensorStatus
    lower_threshold: float | None
    upper_threshold: float | None


class DeviceConfigFeedbackMqtt(BaseModel):
    topic: str
    payload: dict[str, object]


class DeviceConfigActuatorFeedback(BaseModel):
    role: str
    sensor_id: int
    sensor_code: str
    sensor_model_code: str
    value_key: str
    unit: str
    data_type: str
    lower_threshold: float | None
    upper_threshold: float | None
    mqtt: DeviceConfigFeedbackMqtt


class DeviceConfigActuator(BaseModel):
    id: int
    code: str
    name: str
    actuator_model_code: str | None
    is_enabled: bool
    feedbacks: list[DeviceConfigActuatorFeedback]


class DeviceConfigDevice(BaseModel):
    id: int
    code: str
    name: str
    is_enabled: bool
    status: DeviceStatus
    location: str | None
    topics: DeviceConfigTopics
    sensors: list[DeviceConfigSensor]
    actuators: list[DeviceConfigActuator]


class DeviceConfigSummary(BaseModel):
    device_count: int
    enabled_device_count: int
    disabled_device_count: int
    sensor_count: int
    enabled_sensor_count: int
    disabled_sensor_count: int
    actuator_count: int
    enabled_actuator_count: int
    feedback_count: int


class ProjectDeviceConfig(BaseModel):
    exported_at: datetime
    project: DeviceConfigProject
    mqtt: DeviceConfigMqtt
    devices: list[DeviceConfigDevice]
    summary: DeviceConfigSummary


class ProjectMemberCreate(BaseModel):
    user_id: int


class ProjectMemberRead(BaseModel):
    id: int
    user_id: int
    full_name: str
    username: str
    email: str
    phone_number: str
    role: str
    status: str
    created_at: datetime
    created_by: int | None
    created_by_name: str | None


class ProjectMemberListResponse(BaseModel):
    items: list[ProjectMemberRead]
    total: int
    page: int
    page_size: int
