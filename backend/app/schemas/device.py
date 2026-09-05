from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.core.enums import DeviceStatus


class DeviceBase(BaseModel):
    code: str = Field(pattern=r"^[A-Z0-9_-]+$", min_length=3, max_length=80)
    name: str = Field(min_length=2, max_length=255)
    description: str | None = None
    location: str | None = Field(default=None, max_length=255)


class DeviceCreate(DeviceBase):
    device_template_id: int | None = None
    installation_location: str | None = Field(default=None, max_length=255)
    notes: str | None = None
    create_default_sensors: bool = False


class DeviceUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=255)
    description: str | None = None
    location: str | None = Field(default=None, max_length=255)


class DeviceRead(DeviceBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    device_template_id: int | None
    device_kind: str = "GENERIC"
    template_code: str | None = None
    template_name: str | None = None
    nominal_output_voltage_v: float | None = None
    status: DeviceStatus
    last_seen_at: datetime | None
    is_enabled: bool
    disabled_at: datetime | None
    disabled_by_user_id: int | None
    disabled_reason: str | None
    created_at: datetime
    updated_at: datetime


class CredentialIssueRequest(BaseModel):
    expires_at: datetime | None = None


class CredentialStatus(BaseModel):
    device_id: int
    active: bool
    version: int | None
    issued_at: datetime | None
    expires_at: datetime | None
    last_used_at: datetime | None
    revoked_at: datetime | None
    sensor_count: int = 0
    sensors: list["ConnectionSensor"] = Field(default_factory=list)


class ConnectionSensor(BaseModel):
    sensor_code: str
    model_code: str
    name: str
    unit: str
