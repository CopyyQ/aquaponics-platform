from datetime import datetime

import math
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.core.enums import SensorStatus


class SensorFromModelRequest(BaseModel):
    sensor_model_id: int = Field(gt=0)


class SensorModelBase(BaseModel):
    code: str = Field(pattern=r"^[A-Z0-9_-]+$", min_length=2, max_length=80)
    name: str = Field(min_length=2, max_length=255)
    unit: str = Field(min_length=1, max_length=50)
    description: str | None = None
    value_type: str = Field(default="NUMBER", max_length=30)
    chart_type: str = Field(default="LINE", max_length=30)
    measurement_semantics: str = Field(default="GAUGE", pattern="^(GAUGE|COUNTER)$")
    is_active: bool = True
    default_lower_threshold: float | None = None
    default_upper_threshold: float | None = None
    default_warning_enabled: bool = True
    default_below_threshold_message: str | None = Field(default=None, max_length=2000)
    default_above_threshold_message: str | None = Field(default=None, max_length=2000)
    default_alert_risk_level: str | None = Field(default=None, pattern="^(EXTREME|VERY_HIGH|HIGH|MEDIUM|LOW_MEDIUM|LOW)$")

    @field_validator("code", mode="before")
    @classmethod
    def normalize_code(cls, value: str) -> str:
        return str(value).strip().upper()

    @field_validator("name", "unit", mode="before")
    @classmethod
    def normalize_text(cls, value: str) -> str:
        return str(value).strip()

    @model_validator(mode="after")
    def validate_thresholds(self):
        if (
            self.default_lower_threshold is not None
            and self.default_upper_threshold is not None
            and self.default_lower_threshold >= self.default_upper_threshold
        ):
            raise ValueError("Ngưỡng dưới phải nhỏ hơn ngưỡng trên")
        return self


class SensorModelCreate(SensorModelBase):
    pass


class SensorModelUpdate(BaseModel):
    name: str | None = None
    unit: str | None = None
    description: str | None = None
    default_lower_threshold: float | None = None
    default_upper_threshold: float | None = None
    default_warning_enabled: bool | None = None
    default_below_threshold_message: str | None = Field(default=None, max_length=2000)
    default_above_threshold_message: str | None = Field(default=None, max_length=2000)
    default_alert_risk_level: str | None = Field(default=None, pattern="^(EXTREME|VERY_HIGH|HIGH|MEDIUM|LOW_MEDIUM|LOW)$")
    value_type: str | None = Field(default=None, max_length=30)
    chart_type: str | None = Field(default=None, max_length=30)
    measurement_semantics: str | None = Field(
        default=None, pattern="^(GAUGE|COUNTER)$"
    )
    is_active: bool | None = None


class SensorModelRead(SensorModelBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    is_visible: bool
    created_at: datetime
    updated_at: datetime


class SensorCreate(BaseModel):
    sensor_model_id: int
    code: str = Field(pattern=r"^[A-Z0-9_-]+$", min_length=2, max_length=80)
    name: str = Field(min_length=2, max_length=255)
    installation_location: str | None = Field(default=None, max_length=255)
    description: str | None = None


class SensorUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=255)
    installation_location: str | None = Field(default=None, max_length=255)
    description: str | None = None
    lower_threshold: float | None = None
    upper_threshold: float | None = None

    @field_validator("lower_threshold", "upper_threshold")
    @classmethod
    def validate_finite(cls, value: float | None) -> float | None:
        if value is not None and not math.isfinite(value):
            raise ValueError("Ngưỡng phải là số hữu hạn")
        return value

    @model_validator(mode="after")
    def validate_thresholds(self):
        if self.lower_threshold is not None and self.upper_threshold is not None:
            if self.lower_threshold >= self.upper_threshold:
                raise ValueError("Ngưỡng dưới phải nhỏ hơn ngưỡng trên")
        return self


class SensorThresholdUpdate(BaseModel):
    warning_enabled: bool
    lower_threshold: float | None = None
    upper_threshold: float | None = None
    alert_delay_seconds: int = Field(default=0, ge=0, le=86400)
    below_threshold_message: str | None = Field(default=None, max_length=2000)
    above_threshold_message: str | None = Field(default=None, max_length=2000)
    alert_risk_level: str | None = Field(default=None, pattern="^(EXTREME|VERY_HIGH|HIGH|MEDIUM|LOW_MEDIUM|LOW)$")

    @model_validator(mode="after")
    def validate_thresholds(self):
        if (
            self.lower_threshold is not None
            and self.upper_threshold is not None
            and self.lower_threshold >= self.upper_threshold
        ):
            raise ValueError("Ngưỡng dưới phải nhỏ hơn ngưỡng trên")
        return self


class SensorRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    device_id: int
    sensor_model_id: int
    code: str
    name: str
    installation_location: str | None
    description: str | None
    status: SensorStatus
    last_seen_at: datetime | None
    warning_enabled: bool
    lower_threshold: float | None
    upper_threshold: float | None
    below_threshold_message: str | None
    above_threshold_message: str | None
    alert_risk_level: str | None
    alert_delay_seconds: int
    is_enabled: bool
    disabled_at: datetime | None
    disabled_by_user_id: int | None
    disabled_reason: str | None
    created_at: datetime
    updated_at: datetime
