from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.core.enums import AggregatePeriod


class DeviceReadingInput(BaseModel):
    sensor_code: str = Field(min_length=1, max_length=80)
    value: float
    recorded_at: datetime

    @field_validator("value")
    @classmethod
    def finite_value(cls, value: float) -> float:
        if value != value or value in (float("inf"), float("-inf")):
            raise ValueError("Giá trị phải là số hữu hạn")
        return value


class DeviceTelemetryInput(BaseModel):
    sent_at: datetime
    readings: list[DeviceReadingInput] = Field(min_length=1, max_length=500)


class TelemetryIngestError(BaseModel):
    sensor_code: str
    error: str


class TelemetryIngestResponse(BaseModel):
    device_code: str
    accepted: int
    duplicates: int
    rejected: int
    server_time: datetime
    errors: list[TelemetryIngestError]


class TelemetryReadingRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    sensor_id: UUID
    recorded_at: datetime
    received_at: datetime
    value: float


class TelemetryAggregateRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    sensor_id: int
    period: AggregatePeriod
    bucket_time: datetime
    min_value: float
    max_value: float
    avg_value: float
    record_count: int


class LatestTelemetryItem(BaseModel):
    sensor_id: int
    sensor_code: str
    sensor_name: str
    device_id: int
    device_name: str
    unit: str
    value: float | None
    recorded_at: datetime | None
