from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, DateTime, Enum, ForeignKey, Identity, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.enums import DeviceStatus
from app.db.base import Base, SoftDeleteMixin, TimestampMixin

if TYPE_CHECKING:
    from app.models.actuator import Actuator
    from app.models.device_template import DeviceTemplate
    from app.models.legacy_device_credential import DeviceCredential
    from app.models.project import Project
    from app.models.sensor import Sensor


class Device(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "devices"

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    project_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("projects.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    device_template_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("device_templates.id", ondelete="SET NULL"), nullable=True, index=True
    )
    code: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(Text)
    location: Mapped[str | None] = mapped_column(String(255))
    status: Mapped[DeviceStatus] = mapped_column(
        Enum(DeviceStatus, name="device_status"), default=DeviceStatus.WAITING_CONNECTION
    )
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    disconnected_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    is_enabled: Mapped[bool] = mapped_column(default=True, nullable=False)
    disabled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    disabled_by_user_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="SET NULL"))
    disabled_reason: Mapped[str | None] = mapped_column(Text)

    credentials: Mapped[list[DeviceCredential]] = relationship(
        back_populates="device", cascade="all, delete-orphan"
    )
    sensors: Mapped[list[Sensor]] = relationship(back_populates="device")
    actuators: Mapped[list[Actuator]] = relationship(back_populates="device")
    project: Mapped[Project] = relationship(back_populates="devices")
    device_template: Mapped[DeviceTemplate | None] = relationship(back_populates="devices")



# Compatibility import for legacy services. No new runtime API should use it.
from app.models.legacy_device_credential import DeviceCredential
