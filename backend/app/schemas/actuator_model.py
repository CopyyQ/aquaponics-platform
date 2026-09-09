from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field, field_validator


class ActuatorModelCreate(BaseModel):
    code: str = Field(pattern=r"^[A-Z][A-Z0-9_]*$", min_length=2, max_length=80)
    name: str = Field(min_length=2, max_length=255)
    description: str | None = None
    data_type: str = Field(default="BOOLEAN", pattern="^BOOLEAN$")
    default_state: bool = False
    is_active: bool = True
    nominal_voltage_v: float | None = Field(default=None, gt=0)
    voltage_tolerance_v: float | None = Field(default=None, ge=0)
    zero_voltage_max_v: float | None = Field(default=None, ge=0)
    minimum_running_current_a: float | None = Field(default=None, ge=0)
    maximum_running_current_a: float | None = Field(default=None, ge=0)

    @field_validator("code", mode="before")
    @classmethod
    def normalize_code(cls, value: str) -> str:
        return str(value).strip().upper()


class ActuatorModelUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=255)
    description: str | None = None
    default_state: bool | None = None
    is_active: bool | None = None
    nominal_voltage_v: float | None = Field(default=None, gt=0)
    voltage_tolerance_v: float | None = Field(default=None, ge=0)
    zero_voltage_max_v: float | None = Field(default=None, ge=0)
    minimum_running_current_a: float | None = Field(default=None, ge=0)
    maximum_running_current_a: float | None = Field(default=None, ge=0)


class ActuatorModelRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    code: str
    name: str
    description: str | None
    data_type: str
    default_state: bool
    is_active: bool
    sort_order: int
    nominal_voltage_v: float | None
    voltage_tolerance_v: float | None
    zero_voltage_max_v: float | None
    minimum_running_current_a: float | None
    maximum_running_current_a: float | None
    is_deleted: bool
    created_at: datetime
    updated_at: datetime
