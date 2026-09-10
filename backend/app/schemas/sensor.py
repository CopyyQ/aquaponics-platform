from datetime import datetime

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

    @field_validator("code", mode="before")
    @classmethod
    def normalize_code(cls, value: str) -> str:
        return str(value).strip().upper()

    @field_validator("name", "unit", mode="before")
    @classmethod
    def normalize_text(cls, value: str) -> str:
        return str(value).strip()



class SensorModelCreate(SensorModelBase):
    pass


class SensorModelUpdate(BaseModel):
    name: str | None = None
    unit: str | None = None
    description: str | None = None
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
    alerts_enabled: bool
    lower_threshold: float | None
    upper_threshold: float | None
    below_threshold_message: str | None
    above_threshold_message: str | None
    below_risk_level: str | None
    above_risk_level: str | None
    alert_delay_seconds: int
    is_enabled: bool
    disabled_at: datetime | None
    disabled_by_user_id: int | None
    disabled_reason: str | None
    created_at: datetime
    updated_at: datetime
