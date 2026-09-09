from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field



class ActuatorCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    actuator_model_id: int = Field(gt=0)
    location: str | None = Field(default=None, max_length=255)
    notes: str | None = None


class ActuatorUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    location: str | None = Field(default=None, max_length=255)
    notes: str | None = None


class ActuatorModelSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    code: str
    name: str


class ActuatorRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    device_id: int
    actuator_model_id: int | None
    actuator_model: ActuatorModelSummary | None
    sequence_number: int
    code: str
    name: str
    location: str | None
    notes: str | None
    is_enabled: bool
    desired_state: bool | None
    reported_state: bool | None
    last_command_at: datetime | None
    last_reported_at: datetime | None
    status_received_at: datetime | None
    voltage_v: float | None
    current_a: float | None
    electrical_recorded_at: datetime | None
    electrical_received_at: datetime | None
    electrical_alerts_enabled: bool
    voltage_lower_threshold: float | None
    voltage_upper_threshold: float | None
    voltage_low_message: str | None
    voltage_high_message: str | None
    voltage_low_risk_level: str | None
    voltage_high_risk_level: str | None
    current_lower_threshold: float | None
    current_upper_threshold: float | None
    current_low_message: str | None
    current_high_message: str | None
    current_low_risk_level: str | None
    current_high_risk_level: str | None
    disabled_at: datetime | None
    disabled_by_user_id: int | None
    disabled_reason: str | None
    removed_at: datetime | None
    removed_by_user_id: int | None
    removed_reason: str | None
    created_at: datetime
    updated_at: datetime


class ActuatorReadingRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    actuator_id: int
    voltage_v: float | None
    current_a: float | None
    recorded_at: datetime
    received_at: datetime
    quality: str


class ActuatorCommandCreate(BaseModel):
    desired_state: bool


class ActuatorCommandRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    command_id: int
    actuator_id: int
    desired_state: bool
    reported_state: bool | None
    status: str
    requested_at: datetime
