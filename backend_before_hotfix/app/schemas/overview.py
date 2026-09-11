from datetime import datetime

from pydantic import BaseModel

from app.schemas.alert import AlertRead
from app.schemas.telemetry import LatestTelemetryItem


class StatusCount(BaseModel):
    total: int
    online: int
    offline: int
    waiting: int
    disabled: int


class OverviewResponse(BaseModel):
    devices: StatusCount
    sensors: StatusCount
    open_alerts: int
    latest_received_at: datetime | None
    latest_telemetry: list[LatestTelemetryItem]
    recent_alerts: list[AlertRead]
