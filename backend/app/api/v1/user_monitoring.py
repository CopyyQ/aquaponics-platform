from datetime import UTC, datetime
from typing import Literal

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_operational_user
from app.db.session import get_db
from app.models.user import User
from app.services.project_health_service import build_project_health_rows

router = APIRouter(prefix="/monitoring", tags=["User monitoring"])


@router.get("/projects")
async def list_user_monitoring_projects(
    q: str = Query(default="", max_length=255),
    health_status: str | None = None,
    device_status: str | None = None,
    has_offline_sensors: bool | None = None,
    has_out_of_range: bool | None = None,
    sort_by: Literal["risk_score", "alerts", "online_ratio", "last_telemetry_at", "project_name"] = "risk_score",
    sort_order: Literal["asc", "desc"] = "desc",
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    actor: User = Depends(get_current_operational_user),
) -> dict:
    rows = await build_project_health_rows(db, actor)
    keyword = q.strip().casefold()
    if keyword:
        rows = [
            row
            for row in rows
            if keyword in row["name"].casefold() or keyword in row["code"].casefold()
        ]
    if health_status:
        rows = [row for row in rows if row["health_status"] == health_status]
    if device_status == "OFFLINE":
        rows = [row for row in rows if row["offline_device_count"] > 0]
    if device_status == "ONLINE":
        rows = [
            row
            for row in rows
            if row["device_count"] > 0 and row["offline_device_count"] == 0
        ]
    if has_offline_sensors is not None:
        rows = [row for row in rows if (row["offline_sensor_count"] > 0) is has_offline_sensors]
    if has_out_of_range is not None:
        rows = [
            row
            for row in rows
            if (row["out_of_range_sensor_count"] > 0) is has_out_of_range
        ]

    key_functions = {
        "risk_score": lambda row: row["risk_score"],
        "alerts": lambda row: row["open_alert_count"],
        "online_ratio": lambda row: row["online_device_count"] / row["device_count"] if row["device_count"] else 0,
        "last_telemetry_at": lambda row: row["last_telemetry_at"] or datetime.min.replace(tzinfo=UTC),
        "project_name": lambda row: row["name"].casefold(),
    }
    rows.sort(key=key_functions[sort_by], reverse=sort_order == "desc")
    total = len(rows)
    start = (page - 1) * page_size
    items = rows[start : start + page_size]
    for index, item in enumerate(items, start=start + 1):
        item["rank"] = index
    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "updated_at": datetime.now(UTC),
    }
