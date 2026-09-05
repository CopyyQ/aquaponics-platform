import csv
import io
from datetime import datetime
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_operational_user
from app.db.session import get_db
from app.core.enums import AggregatePeriod
from app.models.device import Device
from app.models.sensor import Sensor, SensorModel
from app.models.telemetry import TelemetryAggregate, TelemetryReading
from app.models.user import User
from app.services.access_service import accessible_device_clause, require_sensor_access
from app.schemas.telemetry import (
    LatestTelemetryItem,
    TelemetryReadingRead,
)

router = APIRouter(prefix="/telemetry", tags=["Telemetry"])


@router.get("/latest", response_model=list[LatestTelemetryItem])
async def latest_telemetry(
    db: AsyncSession = Depends(get_db),
    actor: User = Depends(get_current_operational_user),
) -> list[LatestTelemetryItem]:
    latest_subquery = (
        select(
            TelemetryReading.sensor_id,
            func.max(TelemetryReading.recorded_at).label("max_recorded_at"),
        )
        .group_by(TelemetryReading.sensor_id)
        .subquery()
    )
    query = (
        select(Sensor, SensorModel, Device, TelemetryReading)
        .join(SensorModel, Sensor.sensor_model_id == SensorModel.id)
        .join(Device, Sensor.device_id == Device.id)
        .outerjoin(latest_subquery, latest_subquery.c.sensor_id == Sensor.id)
        .outerjoin(
            TelemetryReading,
            and_(
                TelemetryReading.sensor_id == Sensor.id,
                TelemetryReading.recorded_at == latest_subquery.c.max_recorded_at,
            ),
        )
        .where(
            Sensor.is_deleted.is_(False),
            Sensor.deleted_at.is_(None),
            Sensor.is_enabled.is_(True),
            Device.is_deleted.is_(False),
            Device.deleted_at.is_(None),
            Device.is_enabled.is_(True),
            accessible_device_clause(actor),
        )
        .order_by(Sensor.name)
    )
    rows = (await db.execute(query)).all()
    return [
        LatestTelemetryItem(
            sensor_id=sensor.id,
            sensor_code=sensor.code,
            sensor_name=sensor.name,
            device_id=device.id,
            device_name=device.name,
            unit=model.unit,
            value=reading.value if reading else None,
            recorded_at=reading.recorded_at if reading else None,
        )
        for sensor, model, device, reading in rows
    ]


@router.get("/sensors/{sensor_id}/latest", response_model=TelemetryReadingRead | None)
async def sensor_latest(
    sensor_id: int,
    db: AsyncSession = Depends(get_db),
    actor: User = Depends(get_current_operational_user),
) -> TelemetryReading | None:
    await require_sensor_access(db, sensor_id, actor)
    return await db.scalar(
        select(TelemetryReading)
        .where(TelemetryReading.sensor_id == sensor_id)
        .order_by(TelemetryReading.recorded_at.desc())
        .limit(1)
    )


@router.get("/sensors/{sensor_id}/history")
async def sensor_history(
    sensor_id: int,
    start: datetime,
    end: datetime,
    resolution: Literal["RAW", "HOUR", "DAY", "AUTO"] = "AUTO",
    limit: int = Query(5000, ge=1, le=20000),
    db: AsyncSession = Depends(get_db),
    actor: User = Depends(get_current_operational_user),
) -> list[dict]:
    await require_sensor_access(db, sensor_id, actor)
    if start >= end:
        raise HTTPException(status_code=400, detail="start phải nhỏ hơn end")
    if resolution == "AUTO":
        days = (end - start).total_seconds() / 86400
        resolution = "RAW" if days <= 2 else "HOUR" if days <= 90 else "DAY"

    if resolution == "RAW":
        readings = list(
            (
                await db.scalars(
                    select(TelemetryReading)
                    .where(
                        TelemetryReading.sensor_id == sensor_id,
                        TelemetryReading.recorded_at >= start,
                        TelemetryReading.recorded_at <= end,
                    )
                    .order_by(TelemetryReading.recorded_at)
                    .limit(limit)
                )
            ).all()
        )
        return [
            {
                "timestamp": item.recorded_at,
                "value": item.value,
                "min_value": item.value,
                "max_value": item.value,
                "record_count": 1,
                "resolution": "RAW",
            }
            for item in readings
        ]

    period = AggregatePeriod.HOUR if resolution == "HOUR" else AggregatePeriod.DAY
    aggregates = list(
        (
            await db.scalars(
                select(TelemetryAggregate)
                .where(
                    TelemetryAggregate.sensor_id == sensor_id,
                    TelemetryAggregate.period == period,
                    TelemetryAggregate.bucket_time >= start,
                    TelemetryAggregate.bucket_time <= end,
                )
                .order_by(TelemetryAggregate.bucket_time)
                .limit(limit)
            )
        ).all()
    )
    return [
        {
            "timestamp": item.bucket_time,
            "value": item.avg_value,
            "min_value": item.min_value,
            "max_value": item.max_value,
            "record_count": item.record_count,
            "resolution": item.period.value,
        }
        for item in aggregates
    ]


@router.get("/export")
async def export_telemetry(
    sensor_id: int,
    start: datetime,
    end: datetime,
    db: AsyncSession = Depends(get_db),
    actor: User = Depends(get_current_operational_user),
) -> StreamingResponse:
    sensor = await require_sensor_access(db, sensor_id, actor)
    readings = list(
        (
            await db.scalars(
                select(TelemetryReading)
                .where(
                    TelemetryReading.sensor_id == sensor_id,
                    TelemetryReading.recorded_at >= start,
                    TelemetryReading.recorded_at <= end,
                )
                .order_by(TelemetryReading.recorded_at)
            )
        ).all()
    )
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["sensor_id", "sensor_code", "recorded_at", "received_at", "value"])
    for item in readings:
        writer.writerow(
            [sensor.id, sensor.code, item.recorded_at.isoformat(), item.received_at.isoformat(), item.value]
        )
    payload = "\ufeff" + output.getvalue()
    return StreamingResponse(
        iter([payload.encode("utf-8")]),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{sensor.code}-telemetry.csv"'},
    )
