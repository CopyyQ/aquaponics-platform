from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from app.core.enums import AlertDirection, AlertLifecycleStatus, AlertResourceType, AlertSeverity


class AlertRead(BaseModel):
    id: int
    resource_type: AlertResourceType
    device_id: UUID | None
    sensor_id: UUID | None
    actuator_id: UUID | None
    metric: str
    direction: AlertDirection | None
    alert_type: str
    severity: AlertSeverity
    risk_level: str
    status: AlertLifecycleStatus
    message: str
    actual_value: float | None
    threshold_value: float | None
    started_at: datetime
    last_triggered_at: datetime
    occurrence_count: int
    acknowledged_at: datetime | None
    acknowledged_by: UUID | None
    condition_active: bool
    normalized_at: datetime | None
    resolved_at: datetime | None
    resolved_by_user_id: UUID | None
    resolved_by_name: str | None
    resolution_note: str | None
    created_at: datetime
    updated_at: datetime


class AlertResolutionRequest(BaseModel):
    resolution_note: str = Field(min_length=3, max_length=2000)

    @field_validator("resolution_note")
    @classmethod
    def clean_resolution_note(cls, value: str) -> str:
        cleaned = value.strip()
        if len(cleaned) < 3:
            raise ValueError("Ghi chú khắc phục phải có ít nhất 3 ký tự")
        return cleaned
