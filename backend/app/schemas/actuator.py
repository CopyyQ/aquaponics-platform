from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.project_overview import ActuatorElectricalRead


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
    disabled_at: datetime | None
    disabled_by_user_id: int | None
    disabled_reason: str | None
    removed_at: datetime | None
    removed_by_user_id: int | None
    removed_reason: str | None
    created_at: datetime
    updated_at: datetime
    electrical_feedbacks: ActuatorElectricalRead | None = None


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
