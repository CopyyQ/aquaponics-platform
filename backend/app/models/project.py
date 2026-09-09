from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, DateTime, Enum, ForeignKey, Identity, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, SoftDeleteMixin, TimestampMixin
from app.core.enums import ProjectStatus

if TYPE_CHECKING:
    from app.models.device import Device
    from app.models.project_member import ProjectMember
    from app.models.user import User


class Project(Base, TimestampMixin, SoftDeleteMixin):
    """Internal compatibility model for the canonical Aquaponics System."""
    __tablename__ = "aquaponics_systems"
    __table_args__ = (
        Index("ix_aquaponics_systems_status", "status"),
        Index("ix_aquaponics_systems_disabled_by_user_id", "disabled_by_user_id"),
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    owner_user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    code: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(255))
    location: Mapped[str | None] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(Text)
    status: Mapped[ProjectStatus] = mapped_column(
        Enum(ProjectStatus, name="project_status"), default=ProjectStatus.ACTIVE
    )
    disabled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    disabled_by_user_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    disabled_reason: Mapped[str | None] = mapped_column(Text)

    owner: Mapped["User"] = relationship(foreign_keys=[owner_user_id])
    disabled_by: Mapped["User | None"] = relationship(foreign_keys=[disabled_by_user_id])
    devices: Mapped[list["Device"]] = relationship(back_populates="project")
    members: Mapped[list["ProjectMember"]] = relationship(
        back_populates="project", cascade="all, delete-orphan"
    )



# Compatibility import for callers migrating to app.models.project_member.
from app.models.project_member import ProjectMember  # noqa: E402,F401
