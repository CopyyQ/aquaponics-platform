from __future__ import annotations

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Float,
    ForeignKey,
    Identity,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin


class ThresholdAlertConfig(Base, TimestampMixin):
    """The only runtime source for Sensor and Actuator threshold policy."""

    __tablename__ = "threshold_alert_configs"
    __table_args__ = (
        CheckConstraint("(sensor_id IS NOT NULL AND actuator_id IS NULL) OR (sensor_id IS NULL AND actuator_id IS NOT NULL)", name="exactly_one_resource"),
        CheckConstraint("(sensor_id IS NOT NULL AND metric_type = 'SENSOR_VALUE') OR (actuator_id IS NOT NULL AND metric_type IN ('VOLTAGE', 'CURRENT'))", name="metric_matches_resource"),
        CheckConstraint("lower_threshold IS NULL OR upper_threshold IS NULL OR lower_threshold <= upper_threshold", name="threshold_order"),
        CheckConstraint("delay_seconds >= 0", name="delay_nonnegative"),
        CheckConstraint("below_risk_level IS NULL OR below_risk_level IN ('EXTREME','VERY_HIGH','HIGH','MEDIUM','LOW_MEDIUM','LOW')", name="below_risk_allowed"),
        CheckConstraint("above_risk_level IS NULL OR above_risk_level IN ('EXTREME','VERY_HIGH','HIGH','MEDIUM','LOW_MEDIUM','LOW')", name="above_risk_allowed"),
        UniqueConstraint("sensor_id", name="uq_threshold_alert_config_sensor"),
        UniqueConstraint("actuator_id", "metric_type", name="uq_threshold_alert_config_actuator_metric"),
        Index("ix_threshold_alert_configs_sensor", "sensor_id"),
        Index("ix_threshold_alert_configs_actuator_metric", "actuator_id", "metric_type"),
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    sensor_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("sensors.id", ondelete="CASCADE"))
    actuator_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("actuators.id", ondelete="CASCADE"))
    metric_type: Mapped[str] = mapped_column(String(30), nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default=text("true"))
    lower_threshold: Mapped[float | None] = mapped_column(Float)
    upper_threshold: Mapped[float | None] = mapped_column(Float)
    below_risk_level: Mapped[str | None] = mapped_column(String(30))
    above_risk_level: Mapped[str | None] = mapped_column(String(30))
    below_message: Mapped[str | None] = mapped_column(Text)
    above_message: Mapped[str | None] = mapped_column(Text)
    below_consequence: Mapped[str | None] = mapped_column(Text)
    above_consequence: Mapped[str | None] = mapped_column(Text)
    below_recommended_actions: Mapped[str | None] = mapped_column(Text)
    above_recommended_actions: Mapped[str | None] = mapped_column(Text)
    delay_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")

    sensor = relationship("Sensor", back_populates="threshold_alert_config")
    actuator = relationship("Actuator", back_populates="threshold_alert_configs")
