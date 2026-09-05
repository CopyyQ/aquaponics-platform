from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator

from app.schemas.telemetry import DeviceReadingInput


class MqttTelemetryPayload(BaseModel):
    sent_at: datetime
    readings: list[DeviceReadingInput] = Field(min_length=1, max_length=500)


class MqttStatusPayload(BaseModel):
    status: Literal["ONLINE", "OFFLINE"]
    sent_at: datetime
    ip: str | None = None
    firmware_version: str | None = None
    actuators: list["MqttActuatorStatus"]

    @field_validator("status", mode="before")
    @classmethod
    def normalize_legacy_status(cls, value: object) -> object:
        if isinstance(value, str) and value.lower() in {"online", "offline"}:
            return value.upper()
        return value


class MqttActuatorStatus(BaseModel):
    actuator_code: str
    state: bool


class MqttCommandAckPayload(BaseModel):
    command_id: int
    actuator_code: str
    reported_state: bool
    status: Literal["ACKNOWLEDGED", "FAILED"]
    sent_at: datetime
