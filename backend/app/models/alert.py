from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Identity,
    Index,
    Integer,
    Text,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.enums import AlertSeverity, AlertStatus, AlertType
from app.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.sensor import Sensor
    from app.models.user import User


class SensorAlert(Base, TimestampMixin):
    __tablename__ = "sensor_alerts"
    __table_args__ = (
        Index(
            "uq_active_sensor_alert",
            "sensor_id",
            "alert_type",
            unique=True,
            postgresql_where=text("status IN ('PENDING', 'OPEN', 'ACKNOWLEDGED')"),
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    sensor_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("sensors.id", ondelete="RESTRICT"))
    alert_type: Mapped[AlertType] = mapped_column(Enum(AlertType, name="alert_type"))
    severity: Mapped[AlertSeverity] = mapped_column(
        Enum(AlertSeverity, name="alert_severity"), default=AlertSeverity.WARNING
    )
    status: Mapped[AlertStatus] = mapped_column(
        Enum(AlertStatus, name="alert_status"), default=AlertStatus.PENDING
    )
    message: Mapped[str] = mapped_column(Text)
    trigger_value: Mapped[float | None] = mapped_column(Float)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    last_triggered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    occurrence_count: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    acknowledged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    acknowledged_by: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="SET NULL")
    )
    condition_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    normalized_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    resolved_by_user_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="SET NULL")
    )
    resolution_note: Mapped[str | None] = mapped_column(Text)

    sensor: Mapped[Sensor] = relationship(back_populates="alerts")
    resolved_by_user: Mapped[User | None] = relationship(foreign_keys=[resolved_by_user_id], lazy="joined")

    @property
    def resolved_by_name(self) -> str | None:
        return self.resolved_by_user.full_name if self.resolved_by_user else None
