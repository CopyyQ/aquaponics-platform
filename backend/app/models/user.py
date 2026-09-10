from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import BigInteger, DateTime, Enum, ForeignKey, Identity, String, Text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, SoftDeleteMixin, TimestampMixin
from app.core.enums import UserRole, UserStatus


class User(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    public_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), default=uuid4, unique=True, index=True, nullable=False)
    username: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    full_name: Mapped[str] = mapped_column(String(255))
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    phone_number: Mapped[str] = mapped_column(String(30), unique=True, index=True)
    address: Mapped[str] = mapped_column(Text, default="")
    system_role: Mapped[UserRole] = mapped_column(
        Enum(UserRole, name="user_system_role"), default=UserRole.VIEWER
    )
    role_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("roles.id", ondelete="RESTRICT"), index=True)
    role = relationship("Role")
    status: Mapped[UserStatus] = mapped_column(
        Enum(UserStatus, name="user_status"), default=UserStatus.ACTIVE
    )
    must_change_password: Mapped[bool] = mapped_column(default=True)
    token_version: Mapped[int] = mapped_column(default=0, nullable=False)
    disabled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    disabled_by_user_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="SET NULL"))
    disabled_reason: Mapped[str | None] = mapped_column(Text)
    locked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    locked_by_user_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="SET NULL"))
    locked_reason: Mapped[str | None] = mapped_column(Text)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    password_changed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_by: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="SET NULL"))

    creator: Mapped[User | None] = relationship(remote_side=[id], foreign_keys=[created_by])
    disabled_by: Mapped[User | None] = relationship(remote_side=[id], foreign_keys=[disabled_by_user_id])
    locked_by: Mapped[User | None] = relationship(remote_side=[id], foreign_keys=[locked_by_user_id])
