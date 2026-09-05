from datetime import datetime

from pydantic import BaseModel


class EnergyTemplateRead(BaseModel):
    code: str
    name: str
    nominal_output_voltage_v: float | None


class EnergyDeviceRead(BaseModel):
    id: int
    code: str
    name: str
    device_kind: str
    enabled: bool
    connectivity: str
    last_seen_at: datetime | None
    last_received_at: datetime | None
    last_valid_recorded_at: datetime | None
    template: EnergyTemplateRead


class EnergyMeasurementRead(BaseModel):
    sensor_id: int | None
    sensor_code: str | None
    model_code: str
    name: str
    unit: str
    semantics: str
    raw_value: float | None
    display_value: float | None
    freshness: str
    quality: str
    quality_reason: str | None
    engineering_min: float | None
    engineering_max: float | None
    recorded_at: datetime | None
    received_at: datetime | None


class EnergyDataHealthRead(BaseModel):
    expected_measurements: int
    fresh_measurements: int
    valid_measurements: int
    invalid_measurements: int
    missing_measurements: int


class EnergyIssueRead(BaseModel):
    code: str
    severity: str
    message: str
    sensor_id: int | None = None


class EnergyOverviewResponse(BaseModel):
    device: EnergyDeviceRead
    measurements: dict[str, EnergyMeasurementRead]
    data_health: EnergyDataHealthRead
    energy_consumption: dict[str, float | None]
    issues: list[EnergyIssueRead]


class EnergyPowerSensorRead(BaseModel):
    id: int
    code: str
    model_code: str
    unit: str


class EnergyPowerPoint(BaseModel):
    bucket_time: datetime
    avg_value: float
    min_value: float
    max_value: float
    sample_count: int
    partial: bool = False


class EnergyPowerSeriesResponse(BaseModel):
    device_id: int
    sensor: EnergyPowerSensorRead
    range: str
    resolution: str
    timezone: str
    points: list[EnergyPowerPoint]
