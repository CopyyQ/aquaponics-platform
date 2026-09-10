from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import BigInteger, Boolean, CheckConstraint, DateTime, Float, ForeignKey, Identity, Index, Integer, String, Text, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID as PGUUID

from app.db.base import Base, SoftDeleteMixin, TimestampMixin

if TYPE_CHECKING:
    from app.models.actuator_model import ActuatorModel
    from app.models.device import Device
    from app.models.user import User


class Actuator(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "actuators"
    __table_args__ = (
        UniqueConstraint("device_id", "code", name="uq_actuator_device_code"),
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    public_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), default=uuid4, unique=True, index=True, nullable=False)
    device_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("devices.id", ondelete="RESTRICT"), index=True)
    actuator_model_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("actuator_models.id", ondelete="SET NULL"), nullable=True
    )
    sequence_number: Mapped[int] = mapped_column(Integer, nullable=False)
    code: Mapped[str] = mapped_column(String(80))
    name: Mapped[str] = mapped_column(String(255))
    location: Mapped[str | None] = mapped_column(String(255))
    notes: Mapped[str | None] = mapped_column(Text)
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    desired_state: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    reported_state: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    last_command_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    # Time claimed by the device for the state currently stored.  This is
    # deliberately separate from last_reported_at, which is the trusted
    # backend receipt time used for runtime freshness.
    reported_state_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_reported_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    voltage_v: Mapped[float | None] = mapped_column(Float)
    current_a: Mapped[float | None] = mapped_column(Float)
    electrical_recorded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    electrical_received_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    # `last_reported_at` remains the compatibility name for the status receipt
    # timestamp.  New callers use this explicit alias.
    status_received_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    electrical_alerts_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"), default=False)
    voltage_lower_threshold: Mapped[float | None] = mapped_column(Float)
    voltage_upper_threshold: Mapped[float | None] = mapped_column(Float)
    voltage_low_message: Mapped[str | None] = mapped_column(Text)
    voltage_high_message: Mapped[str | None] = mapped_column(Text)
    voltage_low_risk_level: Mapped[str | None] = mapped_column(String(30))
    voltage_high_risk_level: Mapped[str | None] = mapped_column(String(30))
    current_lower_threshold: Mapped[float | None] = mapped_column(Float)
    current_upper_threshold: Mapped[float | None] = mapped_column(Float)
    current_low_message: Mapped[str | None] = mapped_column(Text)
    current_high_message: Mapped[str | None] = mapped_column(Text)
    current_low_risk_level: Mapped[str | None] = mapped_column(String(30))
    current_high_risk_level: Mapped[str | None] = mapped_column(String(30))
    disabled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    disabled_by_user_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    disabled_reason: Mapped[str | None] = mapped_column(Text)
    removed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    removed_by_user_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    removed_reason: Mapped[str | None] = mapped_column(Text)

    device: Mapped["Device"] = relationship(back_populates="actuators")
    actuator_model: Mapped["ActuatorModel | None"] = relationship(lazy="joined")
    disabled_by: Mapped["User | None"] = relationship(foreign_keys=[disabled_by_user_id])
    removed_by: Mapped["User | None"] = relationship(foreign_keys=[removed_by_user_id])
    commands: Mapped[list["ActuatorCommand"]] = relationship(
        back_populates="actuator", cascade="all, delete-orphan"
    )
    state_history: Mapped[list["ActuatorStateHistory"]] = relationship(
        back_populates="actuator", cascade="all, delete-orphan"
    )
    readings: Mapped[list["ActuatorReading"]] = relationship(
        back_populates="actuator", cascade="all, delete-orphan"
    )
    threshold_alert_configs = relationship("ThresholdAlertConfig", back_populates="actuator")


class ActuatorReading(Base):
    __tablename__ = "actuator_readings"
    __table_args__ = (
        Index("ix_actuator_readings_actuator_recorded_desc", "actuator_id", "recorded_at"),
        CheckConstraint("quality IN ('VALID', 'UNVALIDATED', 'INVALID')", name="quality_allowed"),
        UniqueConstraint("legacy_source_key", name="uq_actuator_reading_legacy_source_key"),
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    actuator_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("actuators.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    voltage_v: Mapped[float | None] = mapped_column(Float)
    current_a: Mapped[float | None] = mapped_column(Float)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    quality: Mapped[str] = mapped_column(String(20), nullable=False, server_default="UNVALIDATED")
    # Transitional provenance only.  New MQTT samples leave this NULL; the
    # partial legacy backfill uses it to remain deterministic and idempotent.
    legacy_source_key: Mapped[str | None] = mapped_column(String(180))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=text("now()"))

    actuator: Mapped["Actuator"] = relationship(back_populates="readings")


class ActuatorCommand(Base, TimestampMixin):
    __tablename__ = "actuator_commands"

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    actuator_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("actuators.id", ondelete="RESTRICT"), index=True
    )
    desired_state: Mapped[bool] = mapped_column(Boolean, nullable=False)
    reported_state: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    status: Mapped[str] = mapped_column(String(30), default="PENDING", nullable=False)
    requested_by_user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="RESTRICT"))
    requested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    acknowledged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    failed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    timed_out_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    failure_reason: Mapped[str | None] = mapped_column(Text)

    actuator: Mapped["Actuator"] = relationship(back_populates="commands")


class ActuatorStateHistory(Base):
    __tablename__ = "actuator_state_history"
    __table_args__ = (
        Index("ix_actuator_state_history_actuator_recorded", "actuator_id", "recorded_at"),
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    actuator_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("actuators.id", ondelete="CASCADE"), nullable=False, index=True
    )
    state: Mapped[bool] = mapped_column(Boolean, nullable=False)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    source: Mapped[str] = mapped_column(String(30), nullable=False)
    command_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("actuator_commands.id", ondelete="SET NULL"), nullable=True
    )

    actuator: Mapped["Actuator"] = relationship(back_populates="state_history")
