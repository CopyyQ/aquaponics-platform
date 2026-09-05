from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, CheckConstraint, Float, Identity, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, SoftDeleteMixin, TimestampMixin

if TYPE_CHECKING:
    from app.models.device_template import DeviceTemplateSensor
    from app.models.sensor import Sensor


class SensorModel(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "sensor_models"
    __table_args__ = (
        CheckConstraint(
            "default_lower_threshold IS NULL OR default_upper_threshold IS NULL "
            "OR default_lower_threshold < default_upper_threshold",
            name="default_threshold_order",
        ),
        CheckConstraint(
            "measurement_semantics IN ('GAUGE', 'COUNTER')",
            name="measurement_semantics_allowed",
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    code: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(255))
    unit: Mapped[str] = mapped_column(String(50))
    value_type: Mapped[str] = mapped_column(String(30), default="NUMBER", nullable=False)
    chart_type: Mapped[str] = mapped_column(String(30), default="LINE", nullable=False)
    measurement_semantics: Mapped[str] = mapped_column(
        String(20), default="GAUGE", server_default="GAUGE", nullable=False
    )
    description: Mapped[str | None] = mapped_column(Text)
    default_lower_threshold: Mapped[float | None] = mapped_column(Float)
    default_upper_threshold: Mapped[float | None] = mapped_column(Float)
    default_warning_enabled: Mapped[bool] = mapped_column(default=True, nullable=False)
    default_below_threshold_message: Mapped[str | None] = mapped_column(Text)
    default_above_threshold_message: Mapped[str | None] = mapped_column(Text)
    default_alert_risk_level: Mapped[str | None] = mapped_column(String(30))
    is_visible: Mapped[bool] = mapped_column(default=True)
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)

    sensors: Mapped[list["Sensor"]] = relationship(back_populates="sensor_model")
    template_mappings: Mapped[list["DeviceTemplateSensor"]] = relationship(
        back_populates="sensor_model"
    )
