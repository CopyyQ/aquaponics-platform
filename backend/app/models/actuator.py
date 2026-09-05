from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Identity, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

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
