from datetime import UTC, datetime, timedelta
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_roles
from app.db.session import get_db
from app.core.enums import AlertSeverity, AlertStatus, DeviceStatus, UserRole
from app.models.alert import SensorAlert
from app.models.device import Device
from app.models.project import Project
from app.models.sensor import Sensor, SensorModel
from app.models.telemetry import TelemetryReading
from app.models.user import User
from app.services.access_service import active_project_clause

router = APIRouter(prefix="/admin/monitoring", tags=["Admin monitoring"])
ACTIVE_ALERTS = [AlertStatus.PENDING, AlertStatus.OPEN, AlertStatus.ACKNOWLEDGED]


def health_for(score: int) -> str:
    if score >= 70:
        return "CRITICAL"
    if score >= 35:
        return "WARNING"
    if score > 0:
        return "ATTENTION"
    return "HEALTHY"


async def project_rows(db: AsyncSession) -> list[dict]:
    projects = list((await db.scalars(select(Project).where(active_project_clause(Project)))).all())
    owners = {
        item.id: item
        for item in (
            await db.scalars(select(User).where(User.is_deleted.is_(False), User.status == "ACTIVE"))
        ).all()
    }
    project_ids = {item.id for item in projects}
    devices = list((await db.scalars(select(Device).where(Device.is_deleted.is_(False), Device.deleted_at.is_(None), Device.is_enabled.is_(True), Device.project_id.in_(project_ids)))).all()) if project_ids else []
    device_ids = {item.id for item in devices}
    sensors = list((await db.scalars(select(Sensor).where(Sensor.is_deleted.is_(False), Sensor.deleted_at.is_(None), Sensor.is_enabled.is_(True), Sensor.device_id.in_(device_ids)))).all()) if device_ids else []
    sensor_ids = {item.id for item in sensors}
    alerts = list((await db.scalars(select(SensorAlert).where(SensorAlert.sensor_id.in_(sensor_ids), SensorAlert.status.in_(ACTIVE_ALERTS)))).all()) if sensor_ids else []
    latest_by_sensor = dict((await db.execute(select(TelemetryReading.sensor_id, func.max(TelemetryReading.recorded_at)).group_by(TelemetryReading.sensor_id))).all())
    now = datetime.now(UTC)
    rows: list[dict] = []
    for project in projects:
        project_devices = [item for item in devices if item.project_id == project.id]
        device_ids = {item.id for item in project_devices}
        project_sensors = [item for item in sensors if item.device_id in device_ids]
        sensor_ids = {item.id for item in project_sensors}
        project_alerts = [item for item in alerts if item.sensor_id in sensor_ids]
        critical = sum(item.severity == AlertSeverity.CRITICAL for item in project_alerts)
        warnings = sum(item.severity == AlertSeverity.WARNING for item in project_alerts)
        offline_devices = sum(item.status == DeviceStatus.OFFLINE for item in project_devices)
        abnormal = sum(item.status == "OFFLINE" for item in project_sensors)
        latest = max((latest_by_sensor.get(item.id) for item in project_sensors if latest_by_sensor.get(item.id)), default=None)
        stale = latest is None or latest < now - timedelta(minutes=15)
        risk_score = min(100, critical * 30 + warnings * 12 + offline_devices * 15 + abnormal * 6 + (10 if stale else 0))
        owner = owners.get(project.owner_user_id)
        last_event = max([item.started_at for item in project_alerts] + ([latest] if latest else []) + [project.updated_at])
        rows.append({
            "id": project.id, "code": project.code, "name": project.name,
            "location": project.location, "project_status": project.status,
            "owner_user_id": project.owner_user_id,
            "customer_name": owner.full_name if owner else "Không xác định",
            "customer_email": owner.email if owner else None,
            "risk_score": risk_score, "health_status": health_for(risk_score),
            "critical_alert_count": critical, "warning_alert_count": warnings,
            "offline_device_count": offline_devices, "online_device_count": sum(item.status == DeviceStatus.ONLINE for item in project_devices),
            "device_count": len(project_devices), "abnormal_sensor_count": abnormal,
            "sensor_count": len(project_sensors), "last_telemetry_at": latest,
            "last_event_at": last_event, "stale": stale,
        })
    return rows


@router.get("/projects")
async def list_monitoring_projects(
    q: str = Query(default="", max_length=255), severity: str | None = None,
    health_status: str | None = None, customer_id: int | None = None,
    location: str | None = None, device_status: str | None = None,
    sensor_type: str | None = None, has_alerts: bool | None = None,
    stale_only: bool = False,
    sort_by: Literal["risk_score", "alerts", "online_ratio", "last_telemetry_at", "project_name", "customer_name", "last_event_at"] = "risk_score",
    sort_order: Literal["asc", "desc"] = "desc",
    page: int = Query(default=1, ge=1), page_size: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db), _: User = Depends(require_roles(UserRole.ADMIN)),
) -> dict:
    rows = await project_rows(db)
    keyword = q.strip().casefold()
    if keyword:
        rows = [row for row in rows if keyword in row["name"].casefold() or keyword in row["customer_name"].casefold()]
    if severity:
        rows = [row for row in rows if row["health_status"] == severity]
    if health_status:
        rows = [row for row in rows if row["health_status"] == health_status]
    if customer_id is not None:
        rows = [row for row in rows if row["owner_user_id"] == customer_id]
    if location:
        rows = [row for row in rows if location.casefold() in (row["location"] or "").casefold()]
    if device_status == "OFFLINE":
        rows = [row for row in rows if row["offline_device_count"] > 0]
    if device_status == "ONLINE":
        rows = [row for row in rows if row["device_count"] > 0 and row["offline_device_count"] == 0]
    if sensor_type:
        model_id = await db.scalar(select(SensorModel.id).where(SensorModel.code == sensor_type))
        sensor_project_ids = set((await db.scalars(select(Device.project_id).join(Sensor, Sensor.device_id == Device.id).where(Sensor.sensor_model_id == model_id))).all()) if model_id else set()
        rows = [row for row in rows if row["id"] in sensor_project_ids]
    if has_alerts is not None:
        rows = [row for row in rows if (row["critical_alert_count"] + row["warning_alert_count"] > 0) is has_alerts]
    if stale_only:
        rows = [row for row in rows if row["stale"]]
    key_functions = {
        "risk_score": lambda row: row["risk_score"],
        "alerts": lambda row: row["critical_alert_count"] * 1000 + row["warning_alert_count"],
        "online_ratio": lambda row: row["online_device_count"] / row["device_count"] if row["device_count"] else 0,
        "last_telemetry_at": lambda row: row["last_telemetry_at"] or datetime.min.replace(tzinfo=UTC),
        "project_name": lambda row: row["name"].casefold(), "customer_name": lambda row: row["customer_name"].casefold(),
        "last_event_at": lambda row: row["last_event_at"],
    }
    rows.sort(key=key_functions[sort_by], reverse=sort_order == "desc")
    total = len(rows)
    start = (page - 1) * page_size
    items = rows[start:start + page_size]
    for index, item in enumerate(items, start=start + 1):
        item["rank"] = index
    return {"items": items, "total": total, "page": page, "page_size": page_size, "updated_at": datetime.now(UTC)}


@router.get("/projects/{project_id}")
async def monitoring_project_detail(project_id: int, db: AsyncSession = Depends(get_db), _: User = Depends(require_roles(UserRole.ADMIN))) -> dict:
    row = next((item for item in await project_rows(db) if item["id"] == project_id), None)
    if row is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy dự án")
    return row
