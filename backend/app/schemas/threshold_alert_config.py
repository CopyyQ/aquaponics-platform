from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator

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
    delay_seconds: int = Field(default=0, ge=0, le=86400)

    @model_validator(mode="after")
    def threshold_order(self):
        if self.lower_threshold is not None and self.upper_threshold is not None and self.lower_threshold > self.upper_threshold:
            raise ValueError("Ngưỡng dưới không được lớn hơn ngưỡng trên")
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
    delay_seconds: int | None = Field(default=None, ge=0, le=86400)


class ThresholdAlertConfigRead(ThresholdAlertConfigWrite):
    model_config = ConfigDict(from_attributes=True)
    id: int
    sensor_id: int | None
    actuator_id: int | None
    metric_type: ThresholdMetricType
    created_at: datetime
    updated_at: datetime
