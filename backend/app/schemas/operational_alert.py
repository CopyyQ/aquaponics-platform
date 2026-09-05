from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class AlertRuleRevisionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    revision: int
    business_risk_level: str
    condition_schema_version: int
    condition_config: dict[str, Any]
    message_template: str | None
    consequence: str | None
    recommended_action: str | None
    source_reference: str
    source_order: int
    status: str
    created_at: datetime
    published_at: datetime | None


class AlertRuleRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    code: str
    name: str
    target_type: str
    evaluator_type: str
    is_enabled: bool
    current_revision: AlertRuleRevisionRead | None
    revisions: list[AlertRuleRevisionRead] = []
    sensor_model_ids: list[int] = []
    actuator_model_ids: list[int] = []
    updated_at: datetime


class AlertRuleRevisionCreate(BaseModel):
    business_risk_level: Literal["EXTREME", "VERY_HIGH", "HIGH", "MEDIUM", "LOW_MEDIUM", "LOW"]
    condition_config: dict[str, Any]
    message_template: str | None = None
    consequence: str | None = None
    recommended_action: str | None = None


class AlertRuleCreate(BaseModel):
    code: str = Field(pattern=r"^[A-Z][A-Z0-9_]{2,99}$")
    name: str = Field(min_length=1, max_length=255)
    target_type: Literal["SENSOR", "ACTUATOR"]
    evaluator_type: Literal["THRESHOLD", "THRESHOLD_BANDS", "RANGE_BANDS", "DIGITAL_STATE", "THRESHOLD_DURATION", "ACTUATOR_FEEDBACK", "SCHEDULE_FEEDBACK", "BASELINE_DEVIATION", "WINDOW_DURATION", "TREND"]
    revision: AlertRuleRevisionCreate


class RuleValidationRead(BaseModel):
    valid: bool
    missing_fields: list[str]


class AlertRuleProfileCreate(BaseModel):
    code: str = Field(pattern=r"^[A-Z][A-Z0-9_]{2,99}$")
    name: str = Field(min_length=1, max_length=255)
    config: dict[str, Any]
    actuator_model_ids: list[int] = []
    sensor_model_ids: list[int] = []


class AlertRuleProfileRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    rule_id: int
    code: str
    name: str
    config: dict[str, Any]
    is_enabled: bool
    actuator_model_ids: list[int] = []
    sensor_model_ids: list[int] = []
    created_at: datetime
    updated_at: datetime


class FeedbackBindingCreate(BaseModel):
    sensor_id: int
    feedback_role: Literal["SUPPLY_VOLTAGE", "RUNNING_CURRENT"] = "RUNNING_CURRENT"
    value_key: str = Field(default="current_a", pattern=r"^[a-z][a-z0-9_]*$", min_length=2, max_length=80)
    lower_threshold: float | None = None
    upper_threshold: float | None = None

    @model_validator(mode="after")
    def validate_thresholds(self) -> "FeedbackBindingCreate":
        if self.lower_threshold is not None and self.upper_threshold is not None and self.lower_threshold >= self.upper_threshold:
            raise ValueError("Ngưỡng dưới phải nhỏ hơn ngưỡng trên")
        return self


class FeedbackBindingRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    actuator_id: int
    sensor_id: int
    feedback_role: str
    value_key: str
    unit: str
    data_type: str
    lower_threshold: float | None
    upper_threshold: float | None
    effective_lower_threshold: float | None = None
    effective_upper_threshold: float | None = None
    default_lower_threshold: float | None = None
    default_upper_threshold: float | None = None
    threshold_source: Literal["ACTUATOR_OVERRIDE", "MODEL_DEFAULT", "NONE"] = "NONE"
    is_enabled: bool
    created_at: datetime
    updated_at: datetime


class FeedbackSensorOptionRead(BaseModel):
    id: int
    code: str
    name: str
    device_id: int
    device_code: str
    device_name: str
    sensor_model_id: int
    sensor_model_code: str
    sensor_model_name: str
    unit: str
    data_type: str


class NotificationDeliveryRead(BaseModel):
    id: int
    created_at: datetime
    project_id: int
    project_name: str
    rule_name: str
    business_risk_level: str
    channel: str
    recipient_name: str
    status: str
    attempt_count: int
    reason: str | None = None


class OperationalIncidentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    project_id: int
    rule_id: int
    rule_revision_id: int
    device_id: int | None
    sensor_id: int | None
    actuator_id: int | None
    status: str
    technical_severity: str
    business_risk_level_snapshot: str
    started_at: datetime
    opened_at: datetime | None
    acknowledged_at: datetime | None
    normalized_at: datetime | None
    resolved_at: datetime | None
    occurrence_count: int
    trigger_snapshot: dict[str, Any]


class IncidentResolutionRequest(BaseModel):
    resolution_note: str = Field(min_length=1, max_length=2000)
