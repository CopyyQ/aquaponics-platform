from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, Boolean, CheckConstraint, DateTime, ForeignKey, Identity, Index, String, Text, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin


class Role(Base, TimestampMixin):
    __tablename__ = "roles"
    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    is_system: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    permissions: Mapped[list[RolePermission]] = relationship(back_populates="role", cascade="all, delete-orphan")


class Permission(Base, TimestampMixin):
    __tablename__ = "permissions"
    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    code: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)
    resource: Mapped[str] = mapped_column(String(80), nullable=False)
    action: Mapped[str] = mapped_column(String(80), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class RolePermission(Base, TimestampMixin):
    __tablename__ = "role_permissions"
    __table_args__ = (UniqueConstraint("role_id", "permission_id", name="uq_role_permissions_role_permission"),)
    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    role_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("roles.id", ondelete="CASCADE"), nullable=False, index=True)
    permission_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("permissions.id", ondelete="CASCADE"), nullable=False, index=True)
    role: Mapped[Role] = relationship(back_populates="permissions")
    permission: Mapped[Permission] = relationship()


class RoleAssignment(Base, TimestampMixin):
    __tablename__ = "role_assignments"
    __table_args__ = (
        UniqueConstraint("user_id", "role_id", "scope_type", "scope_id", name="uq_role_assignments_user_role_scope"),
        CheckConstraint(
            "(scope_type = 'GLOBAL' AND scope_id IS NULL) OR "
            "(scope_type = 'AQUAPONICS_SYSTEM' AND scope_id IS NOT NULL)",
            name="role_assignment_scope",
        ),
        Index("uq_role_assignments_global", "user_id", "role_id", unique=True,
              postgresql_where=text("scope_type = 'GLOBAL'")),
    )
    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    role_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("roles.id", ondelete="CASCADE"), nullable=False, index=True)
    scope_type: Mapped[str] = mapped_column(String(32), nullable=False)
    scope_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("aquaponics_systems.id", ondelete="CASCADE"), index=True)
    created_by: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="SET NULL"))
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    role: Mapped[Role] = relationship()


class UserPermissionOverride(Base, TimestampMixin):
    __tablename__ = "user_permission_overrides"
    __table_args__ = (
        UniqueConstraint("user_id", "permission_id", "scope_type", "scope_id", name="uq_user_permission_overrides_user_permission_scope"),
        CheckConstraint(
            "(scope_type = 'GLOBAL' AND scope_id IS NULL) OR "
            "(scope_type = 'AQUAPONICS_SYSTEM' AND scope_id IS NOT NULL)",
            name="user_permission_override_scope",
        ),
        CheckConstraint("effect IN ('ALLOW', 'DENY')", name="user_permission_override_effect"),
        Index("uq_user_permission_overrides_global", "user_id", "permission_id", unique=True,
              postgresql_where=text("scope_type = 'GLOBAL'")),
    )
    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    permission_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("permissions.id", ondelete="CASCADE"), nullable=False, index=True)
    scope_type: Mapped[str] = mapped_column(String(32), nullable=False)
    scope_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("aquaponics_systems.id", ondelete="CASCADE"), index=True)
    effect: Mapped[str] = mapped_column(String(8), nullable=False)
    created_by: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="SET NULL"))
    permission: Mapped[Permission] = relationship()
