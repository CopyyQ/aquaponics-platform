from datetime import UTC, datetime, timedelta
import math

from sqlalchemy import func, literal_column, select
from sqlalchemy.dialects.postgresql import insert

from app.core.enums import AggregatePeriod
from app.db.session import async_session_factory
from app.models.telemetry import TelemetryAggregate, TelemetryReading


def normalize_aggregate_values(
    minimum: float,
    maximum: float,
    average: float,
) -> tuple[float, float, float]:
    """Convert one aggregate using a single numeric representation and clamp float noise."""
    normalized = (float(minimum), float(maximum), float(average))
    if not all(math.isfinite(value) for value in normalized):
        raise ValueError("Telemetry aggregate values must be finite")
    min_value, max_value, avg_value = normalized
    if min_value > max_value:
        raise ValueError("Telemetry aggregate minimum exceeds maximum")
    return min_value, max_value, min(max(avg_value, min_value), max_value)


async def aggregate_period(period: AggregatePeriod) -> None:
    now = datetime.now(UTC)
    start = now - (timedelta(hours=2) if period == AggregatePeriod.HOUR else timedelta(days=2))
    date_unit = "'hour'" if period == AggregatePeriod.HOUR else "'day'"
    bucket_time = func.date_trunc(literal_column(date_unit), TelemetryReading.recorded_at)
    async with async_session_factory() as db:
        rows = (
            await db.execute(
                select(
                    TelemetryReading.sensor_id,
                    bucket_time.label("bucket_time"),
                    func.min(TelemetryReading.value),
                    func.max(TelemetryReading.value),
                    func.avg(TelemetryReading.value),
                    func.count(TelemetryReading.id),
                )
                .where(TelemetryReading.recorded_at >= start)
                .group_by(TelemetryReading.sensor_id, bucket_time)
            )
        ).all()
        for sensor_id, bucket, minimum, maximum, average, count in rows:
            min_value, max_value, avg_value = normalize_aggregate_values(
                minimum,
                maximum,
                average,
            )
            await db.execute(
                insert(TelemetryAggregate)
                .values(
                    sensor_id=sensor_id,
                    period=period,
                    bucket_time=bucket,
                    min_value=min_value,
                    max_value=max_value,
                    avg_value=avg_value,
                    record_count=int(count),
                    updated_at=now,
                )
                .on_conflict_do_update(
                    index_elements=["sensor_id", "period", "bucket_time"],
                    set_={
                        "min_value": min_value,
                        "max_value": max_value,
                        "avg_value": avg_value,
                        "record_count": int(count),
                        "updated_at": now,
                    },
                )
            )
        await db.commit()
