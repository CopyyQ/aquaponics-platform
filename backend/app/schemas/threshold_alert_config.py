from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.core.enums import ThresholdMetricType

_RISK = "^(EXTREME|VERY_HIGH|HIGH|MEDIUM|LOW_MEDIUM|LOW)$"


class ThresholdAlertConfigWrite(BaseModel):
    enabled: bool = True
    lower_threshold: float | None = None
    upper_threshold: float | None = None
    below_risk_level: str | None = Field(default=None, pattern=_RISK)
    above_risk_level: str | None = Field(default=None, pattern=_RISK)
    below_message: str | None = Field(default=None, max_length=2000)
    above_message: str | None = Field(default=None, max_length=2000)
    below_consequence: str | None = Field(default=None, max_length=4000)
    above_consequence: str | None = Field(default=None, max_length=4000)
    below_recommended_actions: str | None = Field(default=None, max_length=4000)
    above_recommended_actions: str | None = Field(default=None, max_length=4000)
    delay_seconds: int = Field(default=0, ge=0, le=86400)

    @field_validator(
        "below_message", "above_message", "below_consequence", "above_consequence",
        "below_recommended_actions", "above_recommended_actions", mode="before",
    )
    @classmethod
    def normalize_content(cls, value: object) -> object:
        return value.strip() or None if isinstance(value, str) else value

    @model_validator(mode="after")
    def threshold_order(self):
        if self.lower_threshold is not None and self.upper_threshold is not None and self.lower_threshold >= self.upper_threshold:
            raise ValueError("Ngưỡng dưới phải nhỏ hơn ngưỡng trên")
        return self


class ThresholdAlertConfigCreate(ThresholdAlertConfigWrite):
    pass


class ThresholdAlertConfigUpdate(BaseModel):
    enabled: bool | None = None
    lower_threshold: float | None = None
    upper_threshold: float | None = None
    below_risk_level: str | None = Field(default=None, pattern=_RISK)
    above_risk_level: str | None = Field(default=None, pattern=_RISK)
    below_message: str | None = Field(default=None, max_length=2000)
    above_message: str | None = Field(default=None, max_length=2000)
    below_consequence: str | None = Field(default=None, max_length=4000)
    above_consequence: str | None = Field(default=None, max_length=4000)
    below_recommended_actions: str | None = Field(default=None, max_length=4000)
    above_recommended_actions: str | None = Field(default=None, max_length=4000)
    delay_seconds: int | None = Field(default=None, ge=0, le=86400)

    @field_validator(
        "below_message", "above_message", "below_consequence", "above_consequence",
        "below_recommended_actions", "above_recommended_actions", mode="before",
    )
    @classmethod
    def normalize_content(cls, value: object) -> object:
        return value.strip() or None if isinstance(value, str) else value


class ThresholdAlertConfigRead(ThresholdAlertConfigWrite):
    model_config = ConfigDict(from_attributes=True)
    id: int
    sensor_id: UUID | None
    actuator_id: UUID | None
    metric_type: ThresholdMetricType
    created_at: datetime
    updated_at: datetime
