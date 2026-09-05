from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import BigInteger, Boolean, CheckConstraint, DateTime, ForeignKey, Identity, Integer, String, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.project import Project


class ProjectPublicSettings(Base, TimestampMixin):
    __tablename__ = "project_public_settings"
    __table_args__ = (
        UniqueConstraint("project_id", name="uq_project_public_settings_project_id"),
        UniqueConstraint("public_slug", name="uq_project_public_settings_public_slug"),
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    project_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=False, server_default=text("false"), nullable=False)
    public_slug: Mapped[str] = mapped_column(String(120), nullable=False)
    project: Mapped[Project] = relationship()


class ProjectNotificationSettings(Base, TimestampMixin):
    __tablename__ = "project_notification_settings"
    __table_args__ = (
        UniqueConstraint("project_id", name="uq_project_notification_settings_project_id"),
        CheckConstraint("reminder_interval_minutes IS NULL OR reminder_interval_minutes > 0", name="reminder_positive"),
        CheckConstraint("minimum_business_risk_level IN ('EXTREME','VERY_HIGH','HIGH','MEDIUM','LOW_MEDIUM','LOW')", name="risk_allowed"),
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    project_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    telegram_enabled: Mapped[bool] = mapped_column(Boolean, default=False, server_default=text("false"), nullable=False)
    notify_alert_opened: Mapped[bool] = mapped_column(Boolean, default=True, server_default=text("true"), nullable=False)
    notify_alert_resolved: Mapped[bool] = mapped_column(Boolean, default=True, server_default=text("true"), nullable=False)
    notify_alert_recovered: Mapped[bool] = mapped_column(Boolean, default=True, server_default=text("true"), nullable=False)
    notify_alert_escalated: Mapped[bool] = mapped_column(Boolean, default=True, server_default=text("true"), nullable=False)
    notify_alert_reminder: Mapped[bool] = mapped_column(Boolean, default=False, server_default=text("false"), nullable=False)
    reminder_interval_minutes: Mapped[int | None] = mapped_column(Integer)
    minimum_business_risk_level: Mapped[str] = mapped_column(String(30), default="LOW", server_default="LOW", nullable=False)
    risk_extreme_enabled: Mapped[bool] = mapped_column(Boolean, default=True, server_default=text("true"), nullable=False)
    risk_very_high_enabled: Mapped[bool] = mapped_column(Boolean, default=True, server_default=text("true"), nullable=False)
    risk_high_enabled: Mapped[bool] = mapped_column(Boolean, default=True, server_default=text("true"), nullable=False)
    risk_medium_enabled: Mapped[bool] = mapped_column(Boolean, default=True, server_default=text("true"), nullable=False)
    risk_low_medium_enabled: Mapped[bool] = mapped_column(Boolean, default=True, server_default=text("true"), nullable=False)
    risk_low_enabled: Mapped[bool] = mapped_column(Boolean, default=True, server_default=text("true"), nullable=False)
    last_health_status: Mapped[str | None] = mapped_column(String(30))
    last_health_fingerprint: Mapped[str | None] = mapped_column(String(64))
    last_health_snapshot: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    last_health_evaluated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_health_notified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    project: Mapped[Project] = relationship()


class ProjectNotificationRiskPolicy(Base, TimestampMixin):
    __tablename__ = "project_notification_risk_policies"
    __table_args__ = (
        UniqueConstraint("project_id", "risk_level", name="uq_project_notification_risk_policy"),
        CheckConstraint("risk_level IN ('EXTREME','VERY_HIGH','HIGH','MEDIUM','LOW_MEDIUM','LOW')", name="risk_level_allowed"),
        CheckConstraint("initial_reminder_seconds >= 0", name="initial_nonnegative"),
        CheckConstraint("repeat_interval_seconds >= 0", name="repeat_nonnegative"),
        CheckConstraint("max_reminders >= 0", name="max_reminders_nonnegative"),
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    project_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    risk_level: Mapped[str] = mapped_column(String(30), nullable=False)
    telegram_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False)
    notify_on_open: Mapped[bool] = mapped_column(Boolean, default=True, server_default=text("true"), nullable=False)
    notify_on_escalation: Mapped[bool] = mapped_column(Boolean, default=True, server_default=text("true"), nullable=False)
    notify_on_recovery: Mapped[bool] = mapped_column(Boolean, default=True, server_default=text("true"), nullable=False)
    notify_on_resolved: Mapped[bool] = mapped_column(Boolean, default=True, server_default=text("true"), nullable=False)
    reminder_enabled: Mapped[bool] = mapped_column(Boolean, default=False, server_default=text("false"), nullable=False)
    initial_reminder_seconds: Mapped[int] = mapped_column(Integer, default=0, server_default="0", nullable=False)
    repeat_interval_seconds: Mapped[int] = mapped_column(Integer, default=0, server_default="0", nullable=False)
    max_reminders: Mapped[int] = mapped_column(Integer, default=0, server_default="0", nullable=False)
    stop_reminders_on_ack: Mapped[bool] = mapped_column(Boolean, default=True, server_default=text("true"), nullable=False)
    project: Mapped[Project] = relationship()


class ProjectNotificationRecipient(Base, TimestampMixin):
    __tablename__ = "project_notification_recipients"
    __table_args__ = (
        UniqueConstraint("project_id", "telegram_chat_id", name="uq_project_notification_recipient_chat"),
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    project_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    telegram_chat_id: Mapped[str] = mapped_column(String(64), nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, server_default=text("true"), nullable=False)
    project: Mapped[Project] = relationship()
