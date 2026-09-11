from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

RiskLevel = Literal["LOW", "LOW_MEDIUM", "MEDIUM", "HIGH", "VERY_HIGH", "EXTREME"]
RangeMode = Literal["INSIDE_RANGE", "OUTSIDE_RANGE"]


class RangeCondition(BaseModel):
    min: float | None = None
    max: float | None = None

    @model_validator(mode="after")
    def validate_bounds(self):
        if self.min is None and self.max is None:
            raise ValueError("Phải nhập ít nhất một giới hạn")
        if self.min is not None and self.max is not None and self.min > self.max:
            raise ValueError("Giới hạn từ không được lớn hơn giới hạn đến")
        return self


class AlertScenarioCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(min_length=1, max_length=255)
    is_enabled: bool = True
    risk_level: RiskLevel
    duration_seconds: int = Field(default=0, ge=0, le=86400)
    message: str | None = Field(default=None, max_length=2000)
    consequence: str | None = Field(default=None, max_length=4000)
    recommended_action: str | None = Field(default=None, max_length=4000)
    range_mode: RangeMode | None = None
    range: RangeCondition | None = None
    reported_state: bool | None = None
    voltage: RangeCondition | None = None
    current: RangeCondition | None = None


class AlertScenarioUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str | None = Field(default=None, min_length=1, max_length=255)
    is_enabled: bool | None = None
    risk_level: RiskLevel | None = None
    duration_seconds: int | None = Field(default=None, ge=0, le=86400)
    message: str | None = Field(default=None, max_length=2000)
    consequence: str | None = Field(default=None, max_length=4000)
    recommended_action: str | None = Field(default=None, max_length=4000)
    range_mode: RangeMode | None = None
    range: RangeCondition | None = None
    reported_state: bool | None = None
    voltage: RangeCondition | None = None
    current: RangeCondition | None = None


class AlertScenarioRead(BaseModel):
    id: UUID
    name: str
    target_type: Literal["SENSOR", "ACTUATOR"]
    evaluator_type: str
    is_enabled: bool
    risk_level: RiskLevel
    duration_seconds: int
    message: str | None
    consequence: str | None
    recommended_action: str | None
    condition: dict
    created_at: datetime
    updated_at: datetime
