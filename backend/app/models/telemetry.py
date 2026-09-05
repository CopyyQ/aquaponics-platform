from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, CheckConstraint, DateTime, Enum, Float, ForeignKey, Identity, Index, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.core.enums import AggregatePeriod

if TYPE_CHECKING:
    from app.models.sensor import Sensor


class TelemetryReading(Base):
    __tablename__ = "telemetry_readings"
    __table_args__ = (
        Index("uq_telemetry_sensor_recorded", "sensor_id", "recorded_at", unique=True),
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    sensor_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("sensors.id", ondelete="RESTRICT"))
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    value: Mapped[float] = mapped_column(Float)

    sensor: Mapped["Sensor"] = relationship(back_populates="telemetry_readings")


class TelemetryAggregate(Base):
    __tablename__ = "telemetry_aggregates"
    __table_args__ = (
        Index("uq_aggregate_bucket", "sensor_id", "period", "bucket_time", unique=True),
        CheckConstraint("record_count > 0", name="aggregate_record_count_positive"),
        CheckConstraint(
            "min_value <= avg_value AND avg_value <= max_value",
            name="aggregate_value_order",
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    sensor_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("sensors.id", ondelete="RESTRICT"))
    period: Mapped[AggregatePeriod] = mapped_column(
        Enum(AggregatePeriod, name="aggregate_period")
    )
    bucket_time: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    min_value: Mapped[float] = mapped_column(Float)
    max_value: Mapped[float] = mapped_column(Float)
    avg_value: Mapped[float] = mapped_column(Float)
    record_count: Mapped[int] = mapped_column(Integer)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    sensor: Mapped["Sensor"] = relationship(back_populates="telemetry_aggregates")
