from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.enums import MonitoringRange
from app.models.device import Device
from app.models.device_template import DeviceTemplate
from app.models.sensor import Sensor, SensorModel
from app.models.telemetry import TelemetryReading
from app.queries.monitoring_queries import device_power_series_rows
from app.services.energy_monitor_service import ENERGY_MONITOR_KIND, ENERGY_SENSOR_SPECS
from app.services.monitoring_service import MONITORING_RANGE_CONFIG, POWER_BUCKETS, _quality


MEASUREMENT_KEYS = (
    "output_voltage",
    "input_voltage",
    "load_current",
    "input_current",
    "power",
    "energy_total",
)


def counter_segment_delta(values: list[float]) -> float | None:
    """Return a monotonic-counter delta, treating each decrease as a reset."""
    if len(values) < 2:
        return None
    total = 0.0
    previous = values[0]
    for current in values[1:]:
        if current >= previous:
            total += current - previous
        else:
            total += max(current, 0.0)
        previous = current
    return total


async def _counter_delta_since(
    db: AsyncSession, *, sensor_id: int, start: datetime, end: datetime
) -> float | None:
    baseline = await db.scalar(
        select(TelemetryReading.value)
        .where(
            TelemetryReading.sensor_id == sensor_id,
            TelemetryReading.recorded_at <= start,
        )
        .order_by(TelemetryReading.recorded_at.desc(), TelemetryReading.id.desc())
        .limit(1)
    )
    values = list(
        (
            await db.scalars(
                select(TelemetryReading.value)
                .where(
                    TelemetryReading.sensor_id == sensor_id,
                    TelemetryReading.recorded_at > start,
                    TelemetryReading.recorded_at <= end,
                )
                .order_by(TelemetryReading.recorded_at, TelemetryReading.id)
            )
        ).all()
    )
    if baseline is None:
        return None
    return counter_segment_delta([float(baseline), *(float(item) for item in values)])


async def _energy_device(db: AsyncSession, project_id: int, device_id: int) -> tuple[Device, DeviceTemplate]:
    row = (await db.execute(
        select(Device, DeviceTemplate)
        .join(DeviceTemplate, DeviceTemplate.id == Device.device_template_id)
        .where(
            Device.id == device_id,
            Device.project_id == project_id,
            Device.is_deleted.is_(False),
            DeviceTemplate.device_kind == ENERGY_MONITOR_KIND,
        )
    )).first()
    if row is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy thiết bị giám sát năng lượng trong dự án này")
    return row


async def get_energy_monitor_overview(db: AsyncSession, *, project_id: int, device_id: int) -> dict:
    device, template = await _energy_device(db, project_id, device_id)
    latest_rank = func.row_number().over(
        partition_by=TelemetryReading.sensor_id,
        order_by=(TelemetryReading.received_at.desc(), TelemetryReading.id.desc()),
    ).label("latest_rank")
    latest = (
        select(TelemetryReading.sensor_id, TelemetryReading.value, TelemetryReading.recorded_at,
               TelemetryReading.received_at, latest_rank)
        .subquery()
    )
    rows = (await db.execute(
        select(Sensor, SensorModel, latest.c.value, latest.c.recorded_at, latest.c.received_at)
        .join(SensorModel, SensorModel.id == Sensor.sensor_model_id)
        .outerjoin(latest, (latest.c.sensor_id == Sensor.id) & (latest.c.latest_rank == 1))
        .where(
            Sensor.device_id == device.id,
            Sensor.is_enabled.is_(True),
            Sensor.is_deleted.is_(False),
            SensorModel.code.in_(tuple(spec.model_code for spec in ENERGY_SENSOR_SPECS)),
        )
    )).all()
    by_model = {model.code: (sensor, model, value, recorded_at, received_at) for sensor, model, value, recorded_at, received_at in rows}
    now = datetime.now(timezone.utc)
    stale_seconds = settings.device_offline_seconds
    measurements: dict[str, dict] = {}
    issues: list[dict] = []
    fresh = valid = invalid = missing = 0
    last_received_at = None
    last_valid_recorded_at = None
    for key, spec in zip(MEASUREMENT_KEYS, ENERGY_SENSOR_SPECS, strict=True):
        row = by_model.get(spec.model_code)
        sensor, model, value, recorded_at, received_at = row if row else (None, None, None, None, None)
        raw = float(value) if value is not None else None
        quality, reason, minimum, maximum = _quality(spec.model_code, raw)
        is_fresh = received_at is not None and (now - received_at).total_seconds() <= stale_seconds
        freshness = "FRESH" if is_fresh else "STALE" if received_at else "NO_DATA"
        if raw is None:
            missing += 1
        elif is_fresh:
            fresh += 1
        if quality in {"VALID", "UNVALIDATED"} and raw is not None:
            valid += 1
            if recorded_at and (last_valid_recorded_at is None or recorded_at > last_valid_recorded_at):
                last_valid_recorded_at = recorded_at
        elif raw is not None:
            invalid += 1
            issues.append({"code": "INVALID_MEASUREMENT", "severity": "WARNING", "message": f"{spec.name}: {reason}", "sensor_id": sensor.id if sensor else None})
        if received_at and (last_received_at is None or received_at > last_received_at):
            last_received_at = received_at
        measurements[key] = {
            "sensor_id": sensor.id if sensor else None, "sensor_code": sensor.code if sensor else None,
            "model_code": spec.model_code, "name": spec.name, "unit": spec.unit,
            "semantics": spec.measurement_semantics, "raw_value": raw,
            "display_value": raw if quality in {"VALID", "UNVALIDATED"} else None,
            "freshness": freshness, "quality": quality, "quality_reason": reason,
            "engineering_min": minimum, "engineering_max": maximum,
            "recorded_at": recorded_at, "received_at": received_at,
        }
    if not device.is_enabled:
        issues.insert(0, {"code": "DEVICE_DISABLED", "severity": "INFO", "message": "Thiết bị đã vô hiệu hóa.", "sensor_id": None})
    elif str(device.status) == "OFFLINE":
        issues.insert(0, {"code": "DEVICE_DISCONNECTED", "severity": "CRITICAL", "message": "Thiết bị mất kết nối; các phép đo có thể bị gián đoạn.", "sensor_id": None})
    elif missing:
        issues.append({"code": "MISSING_MEASUREMENTS", "severity": "WARNING", "message": f"Thiếu dữ liệu cho {missing} phép đo bắt buộc.", "sensor_id": None})
    energy_row = by_model.get("ENERGY_TOTAL_WH")
    energy_sensor = energy_row[0] if energy_row else None
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    consumption = {
        "last_1h_wh": None,
        "last_6h_wh": None,
        "last_12h_wh": None,
        "last_24h_wh": None,
        "month_to_date_wh": None,
    }
    if energy_sensor is not None:
        starts = {
            "last_1h_wh": now - timedelta(hours=1),
            "last_6h_wh": now - timedelta(hours=6),
            "last_12h_wh": now - timedelta(hours=12),
            "last_24h_wh": now - timedelta(hours=24),
            "month_to_date_wh": month_start,
        }
        for name, start in starts.items():
            consumption[name] = await _counter_delta_since(
                db, sensor_id=energy_sensor.id, start=start, end=now
            )
    return {
        "device": {"id": device.id, "code": device.code, "name": device.name,
                   "device_kind": ENERGY_MONITOR_KIND, "enabled": device.is_enabled,
                   "connectivity": "DISABLED" if not device.is_enabled else str(device.status),
                   "last_seen_at": device.last_seen_at, "last_received_at": last_received_at,
                   "last_valid_recorded_at": last_valid_recorded_at,
                   "template": {"code": template.code, "name": template.name, "nominal_output_voltage_v": template.nominal_output_voltage_v}},
        "measurements": measurements,
        "data_health": {"expected_measurements": len(ENERGY_SENSOR_SPECS), "fresh_measurements": fresh, "valid_measurements": valid,
                        "invalid_measurements": invalid, "missing_measurements": missing},
        "energy_consumption": consumption,
        "issues": issues,
    }


async def get_energy_power_series(db: AsyncSession, *, project_id: int, device_id: int, monitoring_range: MonitoringRange) -> dict:
    device, _ = await _energy_device(db, project_id, device_id)
    power_sensor = await db.scalar(
        select(Sensor).join(SensorModel).where(Sensor.device_id == device.id, SensorModel.code == "POWER_W", Sensor.is_deleted.is_(False))
    )
    if power_sensor is None:
        raise HTTPException(status_code=422, detail="Thiết bị năng lượng thiếu Sensor POWER_W")
    config = MONITORING_RANGE_CONFIG[monitoring_range]
    end = datetime.now(timezone.utc)
    rows = await device_power_series_rows(db, project_id=project_id, device_id=device_id, start=end - config.duration, end=end, bucket_size=POWER_BUCKETS[monitoring_range])
    return {"device_id": device.id, "sensor": {"id": power_sensor.id, "code": power_sensor.code, "model_code": "POWER_W", "unit": "W"},
            "range": monitoring_range, "resolution": config.resolution, "timezone": "UTC",
            "points": [{"bucket_time": bucket, "avg_value": float(avg), "min_value": float(minimum), "max_value": float(maximum), "sample_count": int(count), "partial": False} for bucket, avg, minimum, maximum, count in rows]}
