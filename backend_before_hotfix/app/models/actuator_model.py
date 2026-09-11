from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, Boolean, CheckConstraint, Float, Identity, Integer, String, DateTime, Text, UniqueConstraint, func
from app.db.base import SoftDeleteMixin
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class ActuatorModel(Base, SoftDeleteMixin):
    __tablename__ = "actuator_models"
    __table_args__ = (
        UniqueConstraint("code", name="uq_actuator_models_code"),
        CheckConstraint(
            "(nominal_voltage_v IS NULL OR nominal_voltage_v > 0) AND "
            "(voltage_tolerance_v IS NULL OR voltage_tolerance_v >= 0) AND "
            "(zero_voltage_max_v IS NULL OR zero_voltage_max_v >= 0) AND "
            "(minimum_running_current_a IS NULL OR minimum_running_current_a >= 0) AND "
            "(maximum_running_current_a IS NULL OR maximum_running_current_a >= 0) AND "
            "(minimum_running_current_a IS NULL OR maximum_running_current_a IS NULL OR minimum_running_current_a <= maximum_running_current_a)",
            name="electrical_values_nonnegative",
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    code: Mapped[str] = mapped_column(String(80))
    name: Mapped[str] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(Text)
    data_type: Mapped[str] = mapped_column(String(30), default="BOOLEAN", nullable=False)
    default_state: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    nominal_voltage_v: Mapped[float | None] = mapped_column(Float)
    voltage_tolerance_v: Mapped[float | None] = mapped_column(Float)
    zero_voltage_max_v: Mapped[float | None] = mapped_column(Float)
    minimum_running_current_a: Mapped[float | None] = mapped_column(Float)
    maximum_running_current_a: Mapped[float | None] = mapped_column(Float)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
