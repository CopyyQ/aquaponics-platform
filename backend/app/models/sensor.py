from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, CheckConstraint, DateTime, Enum, Float, ForeignKey, Identity, Index, Integer, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, SoftDeleteMixin, TimestampMixin
from app.core.enums import SensorStatus

if TYPE_CHECKING:
    from app.models.alert import SensorAlert
    from app.models.device import Device
    from app.models.telemetry import TelemetryAggregate, TelemetryReading


class Sensor(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "sensors"
    __table_args__ = (
        Index("uq_sensor_device_code", "device_id", "code", unique=True),
        Index("ix_sensors_device_id", "device_id"),
        CheckConstraint("alert_delay_seconds >= 0", name="alert_delay_non_negative"),
        CheckConstraint(
            "lower_threshold IS NULL OR upper_threshold IS NULL OR lower_threshold < upper_threshold",
            name="threshold_order",
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    device_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("devices.id", ondelete="RESTRICT"))
    sensor_model_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("sensor_models.id", ondelete="RESTRICT")
    )
    code: Mapped[str] = mapped_column(String(80))
    name: Mapped[str] = mapped_column(String(255))
    installation_location: Mapped[str | None] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(Text)
    status: Mapped[SensorStatus] = mapped_column(
        Enum(SensorStatus, name="sensor_status"), default=SensorStatus.WAITING_CONNECTION
    )
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    legacy_warning_enabled: Mapped[bool] = mapped_column("warning_enabled", default=True, nullable=False)
    legacy_alert_risk_level: Mapped[str | None] = mapped_column("alert_risk_level", String(30))
    alerts_enabled: Mapped[bool] = mapped_column(default=True, nullable=False)
    lower_threshold: Mapped[float | None] = mapped_column(Float)
    upper_threshold: Mapped[float | None] = mapped_column(Float)
    below_threshold_message: Mapped[str | None] = mapped_column(Text)
    above_threshold_message: Mapped[str | None] = mapped_column(Text)
    below_risk_level: Mapped[str | None] = mapped_column(String(30))
    above_risk_level: Mapped[str | None] = mapped_column(String(30))
    alert_delay_seconds: Mapped[int] = mapped_column(Integer, default=0)
    is_enabled: Mapped[bool] = mapped_column(default=True, nullable=False)
    disabled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    disabled_by_user_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="SET NULL"))
    disabled_reason: Mapped[str | None] = mapped_column(Text)

    device: Mapped["Device"] = relationship(back_populates="sensors")
    sensor_model: Mapped["SensorModel"] = relationship(back_populates="sensors")
    telemetry_readings: Mapped[list["TelemetryReading"]] = relationship(back_populates="sensor")
    telemetry_aggregates: Mapped[list["TelemetryAggregate"]] = relationship(back_populates="sensor")
    alerts: Mapped[list["SensorAlert"]] = relationship(back_populates="sensor")
    threshold_alert_config = relationship("ThresholdAlertConfig", back_populates="sensor", uselist=False)


# Compatibility import for callers migrating to app.models.sensor_model.
from app.models.sensor_model import SensorModel  # noqa: E402,F401
