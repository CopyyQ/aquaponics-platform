from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_operational_user
from app.db.session import get_db
from app.core.enums import AggregatePeriod, MonitoringRange
from app.models.alert import SensorAlert
from app.models.device import Device
from app.models.device_template import DeviceTemplate
from app.models.sensor import Sensor
from app.models.telemetry import TelemetryAggregate, TelemetryReading
from app.models.user import User
from app.schemas.monitoring import (
    ProjectMonitoringActuatorHistoryResponse,
    ProjectMonitoringLatestResponse,
    ProjectMonitoringSeriesResponse,
    ProjectMonitoringSummaryResponse,
    DevicePowerSeriesResponse,
)
from app.services.access_service import require_project_access
from app.services.monitoring_service import (
    get_device_actuator_history,
    get_project_monitoring_latest,
    get_project_monitoring_series,
    get_project_monitoring_summary,
    get_device_power_series,
)

router = APIRouter(prefix="/projects", tags=["Project monitoring"])
async def project_sensor(db: AsyncSession, project_id: int, sensor_id: int) -> Sensor:
    sensor = await db.scalar(
        select(Sensor)
        .join(Device, Device.id == Sensor.device_id)
        .where(
            Sensor.id == sensor_id,
            Device.project_id == project_id,
            Sensor.is_deleted.is_(False),
            Sensor.deleted_at.is_(None),
            Sensor.is_enabled.is_(True),
            Device.is_deleted.is_(False),
            Device.deleted_at.is_(None),
            Device.is_enabled.is_(True),
        )
    )
    if sensor is None:
        raise HTTPException(status_code=404, detail="Cảm biến không thuộc Project")
    return sensor


@router.get("/{project_id}/telemetry/latest", deprecated=True)
@router.get(
    "/{project_id}/monitoring/inventory",
    response_model=ProjectMonitoringLatestResponse,
)
@router.get(
    "/{project_id}/monitoring/latest",
    response_model=ProjectMonitoringLatestResponse,
)
async def latest_project_telemetry(
    project_id: int,
    db: AsyncSession = Depends(get_db),
    actor: User = Depends(get_current_operational_user),
) -> ProjectMonitoringLatestResponse:
    await require_project_access(db, project_id, actor)
    return await get_project_monitoring_latest(db, project_id)


@router.get(
    "/{project_id}/monitoring/series",
    response_model=ProjectMonitoringSeriesResponse,
)
async def project_monitoring_series(
    project_id: int,
    range: MonitoringRange = Query(default=MonitoringRange.TWENTY_FOUR_HOURS),
    db: AsyncSession = Depends(get_db),
    actor: User = Depends(get_current_operational_user),
) -> ProjectMonitoringSeriesResponse:
    await require_project_access(db, project_id, actor)
    return await get_project_monitoring_series(
        db,
        project_id=project_id,
        monitoring_range=range,
    )


@router.get(
    "/{project_id}/devices/{device_id}/monitoring/power-series",
    response_model=DevicePowerSeriesResponse,
)
async def energy_device_power_series(
    project_id: int,
    device_id: int,
    range: MonitoringRange = Query(default=MonitoringRange.TWENTY_FOUR_HOURS),
    db: AsyncSession = Depends(get_db),
    actor: User = Depends(get_current_operational_user),
) -> DevicePowerSeriesResponse:
    await require_project_access(db, project_id, actor)
    device = await db.scalar(
        select(Device.id)
        .join(Device.device_template)
        .where(
            Device.id == device_id,
            Device.project_id == project_id,
            Device.is_deleted.is_(False),
            DeviceTemplate.device_kind == "ENERGY_MONITOR",
        )
    )
    if device is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy thiết bị năng lượng trong Project")
    return await get_device_power_series(
        db,
        project_id=project_id,
        device_id=device_id,
        monitoring_range=range,
    )


@router.get(
    "/{project_id}/devices/{device_id}/monitoring/sensor-series",
    response_model=ProjectMonitoringSeriesResponse,
)
async def device_monitoring_sensor_series(
    project_id: int,
    device_id: int,
    range: MonitoringRange = Query(default=MonitoringRange.TWENTY_FOUR_HOURS),
    db: AsyncSession = Depends(get_db),
    actor: User = Depends(get_current_operational_user),
) -> ProjectMonitoringSeriesResponse:
    await require_project_access(db, project_id, actor)
    device = await db.scalar(
        select(Device.id).where(
            Device.id == device_id,
            Device.project_id == project_id,
            Device.is_enabled.is_(True),
            Device.is_deleted.is_(False),
            Device.deleted_at.is_(None),
        )
    )
    if device is None:
        raise HTTPException(status_code=404, detail="Thiết bị không thuộc Project")
    return await get_project_monitoring_series(
        db,
        project_id=project_id,
        device_id=device_id,
        monitoring_range=range,
    )


@router.get(
    "/{project_id}/devices/{device_id}/monitoring/actuator-history",
    response_model=ProjectMonitoringActuatorHistoryResponse,
)
async def device_monitoring_actuator_history(
    project_id: int,
    device_id: int,
    range: MonitoringRange = Query(default=MonitoringRange.TWENTY_FOUR_HOURS),
    db: AsyncSession = Depends(get_db),
    actor: User = Depends(get_current_operational_user),
) -> ProjectMonitoringActuatorHistoryResponse:
    await require_project_access(db, project_id, actor)
    device = await db.scalar(
        select(Device.id).where(
            Device.id == device_id,
            Device.project_id == project_id,
            Device.is_enabled.is_(True),
            Device.is_deleted.is_(False),
            Device.deleted_at.is_(None),
        )
    )
    if device is None:
        raise HTTPException(status_code=404, detail="Thiết bị không thuộc Project")
    return await get_device_actuator_history(
        db,
        project_id=project_id,
        device_id=device_id,
        monitoring_range=range,
    )


@router.get("/{project_id}/telemetry")
@router.get("/{project_id}/sensors/{sensor_id}/telemetry")
async def project_telemetry_history(
    project_id: int,
    start: datetime,
    end: datetime,
    sensor_id: int | None = None,
    resolution: str = Query(default="RAW", pattern="^(RAW|HOUR|DAY)$"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=500, ge=1, le=5000),
    db: AsyncSession = Depends(get_db),
    actor: User = Depends(get_current_operational_user),
) -> dict:
    await require_project_access(db, project_id, actor)
    if sensor_id is None:
        raise HTTPException(status_code=422, detail="sensor_id là bắt buộc")
    await project_sensor(db, project_id, sensor_id)
    if resolution == "RAW":
        query = select(TelemetryReading).where(TelemetryReading.sensor_id == sensor_id, TelemetryReading.recorded_at >= start, TelemetryReading.recorded_at <= end)
        total = int(await db.scalar(select(func.count()).select_from(query.subquery())) or 0)
        items = list((await db.scalars(query.order_by(TelemetryReading.recorded_at).offset((page - 1) * page_size).limit(page_size))).all())
        return {"items": [{"timestamp": item.recorded_at, "value": item.value, "resolution": "RAW"} for item in items], "total": total, "page": page, "page_size": page_size}
    period = AggregatePeriod.HOUR if resolution == "HOUR" else AggregatePeriod.DAY
    query = select(TelemetryAggregate).where(TelemetryAggregate.sensor_id == sensor_id, TelemetryAggregate.period == period, TelemetryAggregate.bucket_time >= start, TelemetryAggregate.bucket_time <= end)
    total = int(await db.scalar(select(func.count()).select_from(query.subquery())) or 0)
    items = list((await db.scalars(query.order_by(TelemetryAggregate.bucket_time).offset((page - 1) * page_size).limit(page_size))).all())
    return {"items": [{"timestamp": item.bucket_time, "value": item.avg_value, "min_value": item.min_value, "max_value": item.max_value, "record_count": item.record_count, "resolution": resolution} for item in items], "total": total, "page": page, "page_size": page_size}


@router.get("/{project_id}/monitoring/summary", response_model=ProjectMonitoringSummaryResponse)
async def monitoring_summary(
    project_id: int,
    db: AsyncSession = Depends(get_db),
    actor: User = Depends(get_current_operational_user),
) -> dict:
    project = await require_project_access(db, project_id, actor)
    return await get_project_monitoring_summary(db, project_id, project_status=project.status)


@router.get("/{project_id}/alerts")
async def project_alerts(
    project_id: int,
    db: AsyncSession = Depends(get_db),
    actor: User = Depends(get_current_operational_user),
) -> list[dict]:
    await require_project_access(db, project_id, actor)
    rows = (
        await db.execute(
            select(SensorAlert, Sensor, Device)
            .join(Sensor, Sensor.id == SensorAlert.sensor_id)
            .join(Device, Device.id == Sensor.device_id)
            .where(Device.project_id == project_id, Device.is_deleted.is_(False), Device.deleted_at.is_(None), Device.is_enabled.is_(True), Sensor.is_deleted.is_(False), Sensor.deleted_at.is_(None), Sensor.is_enabled.is_(True))
            .order_by(SensorAlert.started_at.desc())
        )
    ).all()
    return [{"id": alert.id, "sensor_id": sensor.id, "sensor_name": sensor.name, "device_id": device.id, "device_name": device.name, "severity": alert.severity, "status": alert.status, "message": alert.message, "trigger_value": alert.trigger_value, "started_at": alert.started_at} for alert, sensor, device in rows]
