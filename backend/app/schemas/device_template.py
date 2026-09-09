from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from app.core.enums import DeviceType


class DeviceTemplateBase(BaseModel):
    code: str = Field(pattern=r"^[A-Z0-9_-]+$", min_length=2, max_length=80)
    name: str = Field(min_length=2, max_length=255)
    description: str | None = None
    notes: str | None = None
    device_type: DeviceType
    nominal_output_voltage_v: float | None = Field(default=None, gt=0)
    is_active: bool = True

    @field_validator("code", mode="before")
    @classmethod
    def normalize_code(cls, value: str) -> str:
        return str(value).strip().upper()

    @field_validator("name", mode="before")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        return str(value).strip()


class DeviceTemplateCreate(DeviceTemplateBase):
    pass


class DeviceTemplateUpdate(BaseModel):
    code: str | None = Field(default=None, pattern=r"^[A-Z0-9_-]+$", min_length=2, max_length=80)
    name: str | None = Field(default=None, min_length=2, max_length=255)
    description: str | None = None
    notes: str | None = None
    device_type: DeviceType | None = None
    nominal_output_voltage_v: float | None = Field(default=None, gt=0)
    is_active: bool | None = None

    @field_validator("code", mode="before")
    @classmethod
    def normalize_code(cls, value: str | None) -> str | None:
        return str(value).strip().upper() if value is not None else None


class TemplateSensorInput(BaseModel):
    sensor_model_id: int
    code: str = Field(pattern=r"^[A-Z0-9_-]+$", min_length=2, max_length=80)
    display_name: str | None = Field(default=None, max_length=255)
    default_location: str | None = Field(default=None, max_length=255)
    default_lower_threshold: float | None = None
    default_upper_threshold: float | None = None
    default_alerts_enabled: bool | None = None
    default_below_threshold_message: str | None = Field(default=None, max_length=2000)
    default_above_threshold_message: str | None = Field(default=None, max_length=2000)
    default_below_risk_level: str | None = Field(default=None, pattern="^(EXTREME|VERY_HIGH|HIGH|MEDIUM|LOW_MEDIUM|LOW)$")
    default_above_risk_level: str | None = Field(default=None, pattern="^(EXTREME|VERY_HIGH|HIGH|MEDIUM|LOW_MEDIUM|LOW)$")
    sort_order: int = Field(default=0, ge=0)
    is_required: bool = False

    @model_validator(mode="after")
    def validate_thresholds(self):
        if self.default_lower_threshold is not None and self.default_upper_threshold is not None and self.default_lower_threshold >= self.default_upper_threshold:
            raise ValueError("Ngưỡng dưới phải nhỏ hơn ngưỡng trên")
        return self


class TemplateSensorUpdate(BaseModel):
    code: str | None = Field(default=None, pattern=r"^[A-Z0-9_-]+$", min_length=2, max_length=80)
    display_name: str | None = Field(default=None, max_length=255)
    default_location: str | None = Field(default=None, max_length=255)
    default_lower_threshold: float | None = None
    default_upper_threshold: float | None = None
    default_alerts_enabled: bool | None = None
    default_below_threshold_message: str | None = Field(default=None, max_length=2000)
    default_above_threshold_message: str | None = Field(default=None, max_length=2000)
    default_below_risk_level: str | None = Field(default=None, pattern="^(EXTREME|VERY_HIGH|HIGH|MEDIUM|LOW_MEDIUM|LOW)$")
    default_above_risk_level: str | None = Field(default=None, pattern="^(EXTREME|VERY_HIGH|HIGH|MEDIUM|LOW_MEDIUM|LOW)$")
    sort_order: int | None = Field(default=None, ge=0)
    is_required: bool | None = None

    @model_validator(mode="after")
    def validate_thresholds(self):
        if (
            self.default_lower_threshold is not None
            and self.default_upper_threshold is not None
            and self.default_lower_threshold >= self.default_upper_threshold
        ):
            raise ValueError("Ngưỡng dưới phải nhỏ hơn ngưỡng trên")
        return self


class TemplateSensorRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    sensor_model_id: int
    code: str
    display_name: str | None
    default_location: str | None
    default_lower_threshold: float | None
    default_upper_threshold: float | None
    default_alerts_enabled: bool | None
    default_below_threshold_message: str | None
    default_above_threshold_message: str | None
    default_below_risk_level: str | None
    default_above_risk_level: str | None
    sort_order: int
    is_required: bool
    model_code: str
    model_name: str
    unit: str
    value_type: str
    chart_type: str
    measurement_semantics: str


class TemplateActuatorInput(BaseModel):
    actuator_model_id: int
    code: str = Field(pattern=r"^[A-Z0-9_-]+$", min_length=2, max_length=80)
    default_name: str | None = Field(default=None, max_length=255)
    default_location: str | None = Field(default=None, max_length=255)
    default_notes: str | None = None
    actuator_type: str = Field(default="SWITCH", pattern="^(SWITCH|PUMP|VALVE|LIGHT|ALARM|OTHER)$")
    default_state: bool | None = None
    command_capability: str = Field(default="ON_OFF", pattern="^ON_OFF$")
    monitor_current: bool = False
    electrical_profile_id: int | None = None
    sort_order: int = Field(default=0, ge=0)
    is_required: bool = False
    is_enabled: bool = True

    @field_validator("code", mode="before")
    @classmethod
    def normalize_code(cls, value: str) -> str:
        return str(value).strip().upper()


class TemplateActuatorUpdate(BaseModel):
    code: str | None = Field(default=None, pattern=r"^[A-Z0-9_-]+$", min_length=2, max_length=80)
    default_name: str | None = Field(default=None, max_length=255)
    default_location: str | None = Field(default=None, max_length=255)
    default_notes: str | None = None
    actuator_type: str | None = Field(default=None, pattern="^(SWITCH|PUMP|VALVE|LIGHT|ALARM|OTHER)$")
    default_state: bool | None = None
    command_capability: str | None = Field(default=None, pattern="^ON_OFF$")
    monitor_current: bool | None = None
    electrical_profile_id: int | None = None
    sort_order: int | None = Field(default=None, ge=0)
    is_required: bool | None = None
    is_enabled: bool | None = None

    @field_validator("code", mode="before")
    @classmethod
    def normalize_code(cls, value: str | None) -> str | None:
        return str(value).strip().upper() if value is not None else None


class TemplateActuatorRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    actuator_model_id: int
    code: str
    default_name: str | None
    default_location: str | None
    default_notes: str | None
    actuator_type: str
    default_state: bool | None
    command_capability: str
    monitor_current: bool
    electrical_profile_id: int | None
    electrical_profile_code: str | None
    electrical_profile_name: str | None
    sort_order: int
    is_required: bool
    is_enabled: bool
    model_code: str
    model_name: str


class ActuatorCurrentProfileRead(BaseModel):
    id: int
    code: str
    name: str
    actuator_model_ids: list[int]


class DeviceTemplateRead(DeviceTemplateBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    created_at: datetime
    updated_at: datetime
    sensors: list[TemplateSensorRead] = Field(default_factory=list)
    actuators: list[TemplateActuatorRead] = Field(default_factory=list)


class DeviceTemplateList(BaseModel):
    items: list[DeviceTemplateRead]
    total: int
    page: int
    page_size: int
