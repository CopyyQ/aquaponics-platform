from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import BigInteger, Boolean, CheckConstraint, DateTime, Float, ForeignKey, Identity, Index, Integer, String, Text, UniqueConstraint, func, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin


class AlertRule(Base, TimestampMixin):
    __tablename__ = "alert_rules"
    __table_args__ = (
        CheckConstraint("target_type IN ('SENSOR','ACTUATOR')", name="alert_rule_target_type_allowed"),
        CheckConstraint("evaluator_type IN ('THRESHOLD','THRESHOLD_BANDS','RANGE_BANDS','DIGITAL_STATE','THRESHOLD_DURATION','ACTUATOR_FEEDBACK','SCHEDULE_FEEDBACK','BASELINE_DEVIATION','WINDOW_DURATION','TREND')", name="alert_rule_evaluator_type_allowed"),
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    code: Mapped[str] = mapped_column(String(100), unique=True)
    name: Mapped[str] = mapped_column(String(255))
    target_type: Mapped[str] = mapped_column(String(30))
    evaluator_type: Mapped[str] = mapped_column(String(50))
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True, server_default=text("true"))
    current_revision_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("alert_rule_revisions.id", ondelete="SET NULL", use_alter=True)
    )
    revisions: Mapped[list[AlertRuleRevision]] = relationship(
        back_populates="rule", foreign_keys="AlertRuleRevision.rule_id", order_by="AlertRuleRevision.revision"
    )
    current_revision: Mapped[AlertRuleRevision | None] = relationship(
        foreign_keys=[current_revision_id], post_update=True
    )
    sensor_models = relationship("SensorModel", secondary="alert_rule_sensor_models", viewonly=True)
    actuator_models = relationship("ActuatorModel", secondary="alert_rule_actuator_models", viewonly=True)

    @property
    def sensor_model_ids(self) -> list[int]:
        return [item.id for item in self.sensor_models]

    @property
    def actuator_model_ids(self) -> list[int]:
        return [item.id for item in self.actuator_models]


class AlertRuleRevision(Base):
    __tablename__ = "alert_rule_revisions"
    __table_args__ = (
        UniqueConstraint("rule_id", "revision", name="uq_alert_rule_revision"),
        CheckConstraint("business_risk_level IN ('EXTREME','VERY_HIGH','HIGH','MEDIUM','LOW_MEDIUM','LOW')", name="alert_revision_risk_allowed"),
        CheckConstraint("status IN ('DRAFT','INCOMPLETE','VALIDATED','PUBLISHED','RETIRED')", name="alert_revision_status_allowed"),
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    rule_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("alert_rules.id", ondelete="CASCADE"), index=True)
    revision: Mapped[int] = mapped_column(Integer)
    business_risk_level: Mapped[str] = mapped_column(String(30))
    condition_schema_version: Mapped[int] = mapped_column(Integer, default=1, server_default="1")
    condition_config: Mapped[dict[str, Any]] = mapped_column(JSONB)
    message_template: Mapped[str | None] = mapped_column(Text)
    consequence: Mapped[str | None] = mapped_column(Text)
    recommended_action: Mapped[str | None] = mapped_column(Text)
    source_reference: Mapped[str] = mapped_column(String(255), server_default="Business rules 2026-08-24")
    source_order: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(30))
    created_by: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="SET NULL"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    published_by: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="SET NULL"))
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    rule: Mapped[AlertRule] = relationship(back_populates="revisions", foreign_keys=[rule_id])


class AlertRuleProfile(Base, TimestampMixin):
    __tablename__ = "alert_rule_profiles"

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    rule_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("alert_rules.id", ondelete="CASCADE"), index=True)
    code: Mapped[str] = mapped_column(String(100), unique=True)
    name: Mapped[str] = mapped_column(String(255))
    config: Mapped[dict[str, Any]] = mapped_column(JSONB)
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True, server_default=text("true"))


class AlertRuleActuatorModelProfile(Base):
    __tablename__ = "alert_rule_actuator_model_profiles"
    profile_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("alert_rule_profiles.id", ondelete="CASCADE"), primary_key=True)
    actuator_model_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("actuator_models.id", ondelete="CASCADE"), primary_key=True)


class AlertRuleSensorModelProfile(Base):
    __tablename__ = "alert_rule_sensor_model_profiles"
    profile_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("alert_rule_profiles.id", ondelete="CASCADE"), primary_key=True)
    sensor_model_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("sensor_models.id", ondelete="CASCADE"), primary_key=True)


class AlertRuleActuatorModel(Base):
    __tablename__ = "alert_rule_actuator_models"
    rule_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("alert_rules.id", ondelete="CASCADE"), primary_key=True)
    actuator_model_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("actuator_models.id", ondelete="CASCADE"), primary_key=True, index=True)


class AlertRuleSensorModel(Base):
    __tablename__ = "alert_rule_sensor_models"
    rule_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("alert_rules.id", ondelete="CASCADE"), primary_key=True)
    sensor_model_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("sensor_models.id", ondelete="CASCADE"), primary_key=True, index=True)


class AlertRuleProjectOverride(Base, TimestampMixin):
    __tablename__ = "alert_rule_project_overrides"
    __table_args__ = (UniqueConstraint("rule_id", "project_id", name="uq_alert_rule_project_overrides_rule_scope"),)
    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    rule_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("alert_rules.id", ondelete="CASCADE"))
    project_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    config: Mapped[dict[str, Any]] = mapped_column(JSONB)
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True, server_default=text("true"))


class AlertRuleActuatorOverride(Base, TimestampMixin):
    __tablename__ = "alert_rule_actuator_overrides"
    __table_args__ = (UniqueConstraint("rule_id", "actuator_id", name="uq_alert_rule_actuator_overrides_rule_scope"),)
    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    rule_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("alert_rules.id", ondelete="CASCADE"))
    actuator_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("actuators.id", ondelete="CASCADE"), index=True)
    config: Mapped[dict[str, Any]] = mapped_column(JSONB)
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True, server_default=text("true"))


class AlertRuleSensorOverride(Base, TimestampMixin):
    __tablename__ = "alert_rule_sensor_overrides"
    __table_args__ = (UniqueConstraint("rule_id", "sensor_id", name="uq_alert_rule_sensor_overrides_rule_scope"),)
    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    rule_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("alert_rules.id", ondelete="CASCADE"))
    sensor_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("sensors.id", ondelete="CASCADE"), index=True)
    config: Mapped[dict[str, Any]] = mapped_column(JSONB)
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True, server_default=text("true"))


class ActuatorFeedbackBinding(Base, TimestampMixin):
    __tablename__ = "actuator_feedback_bindings"
    __table_args__ = (
        UniqueConstraint("actuator_id", "feedback_role", name="uq_actuator_feedback_role"),
        CheckConstraint("feedback_role IN ('SUPPLY_VOLTAGE','RUNNING_CURRENT')", name="actuator_feedback_role_allowed"),
        CheckConstraint("data_type IN ('FLOAT')", name="data_type_allowed"),
        CheckConstraint("lower_threshold IS NULL OR upper_threshold IS NULL OR lower_threshold < upper_threshold", name="feedback_binding_threshold_order"),
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    actuator_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("actuators.id", ondelete="CASCADE"), index=True)
    sensor_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("sensors.id", ondelete="RESTRICT"), index=True)
    feedback_role: Mapped[str] = mapped_column(String(40), default="RUNNING_CURRENT")
    model_feedback_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("actuator_model_feedback_definitions.id", ondelete="SET NULL"), index=True
    )
    value_key: Mapped[str] = mapped_column(String(80), default="current_a", server_default="current_a")
    unit: Mapped[str] = mapped_column(String(50), default="A", server_default="A")
    data_type: Mapped[str] = mapped_column(String(30), default="FLOAT", server_default="FLOAT")
    lower_threshold: Mapped[float | None] = mapped_column(Float)
    upper_threshold: Mapped[float | None] = mapped_column(Float)
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True, server_default=text("true"))
    created_by: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="SET NULL"))
    updated_by: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="SET NULL"))


class OperationalIncident(Base, TimestampMixin):
    __tablename__ = "operational_incidents"
    __table_args__ = (
        Index("ix_operational_incidents_project_status", "project_id", "status"),
        Index("ix_operational_incidents_rule_status", "rule_id", "status"),
        Index("uq_active_operational_incident", "rule_id", "context_key", unique=True, postgresql_where=text("status IN ('PENDING','OPEN','ACKNOWLEDGED','NORMALIZED')")),
        CheckConstraint("status IN ('PENDING','OPEN','ACKNOWLEDGED','NORMALIZED','RESOLVED')", name="operational_incident_status_allowed"),
        CheckConstraint("technical_severity IN ('WARNING','CRITICAL')", name="operational_incident_severity_allowed"),
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    project_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("projects.id", ondelete="RESTRICT"))
    # NULL identifies the canonical Sensor-threshold path. AlertRule remains a
    # compatibility/advanced actuator mechanism during the phased migration.
    rule_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("alert_rules.id", ondelete="RESTRICT"))
    rule_revision_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("alert_rule_revisions.id", ondelete="RESTRICT"))
    device_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("devices.id", ondelete="RESTRICT"))
    sensor_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("sensors.id", ondelete="RESTRICT"))
    actuator_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("actuators.id", ondelete="RESTRICT"))
    context_key: Mapped[str] = mapped_column(String(160))
    status: Mapped[str] = mapped_column(String(30))
    technical_severity: Mapped[str] = mapped_column(String(30))
    business_risk_level_snapshot: Mapped[str] = mapped_column(String(30))
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    opened_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    acknowledged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    normalized_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_triggered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    occurrence_count: Mapped[int] = mapped_column(Integer, default=1, server_default="1")
    trigger_snapshot: Mapped[dict[str, Any]] = mapped_column(JSONB)
    acknowledged_by: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="SET NULL"))
    resolved_by: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="SET NULL"))
    resolution_note: Mapped[str | None] = mapped_column(Text)


class NotificationOutbox(Base):
    __tablename__ = "notification_outbox"
    __table_args__ = (Index("ix_notification_outbox_status_available", "status", "available_at"),)

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    incident_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("operational_incidents.id", ondelete="CASCADE"))
    event_type: Mapped[str] = mapped_column(String(30))
    idempotency_key: Mapped[str] = mapped_column(String(200), unique=True)
    payload_snapshot: Mapped[dict[str, Any]] = mapped_column(JSONB)
    status: Mapped[str] = mapped_column(String(30), default="PENDING", server_default="PENDING")
    available_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    attempt_count: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    last_attempt_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    skip_reason: Mapped[str | None] = mapped_column(String(120))


class NotificationDelivery(Base, TimestampMixin):
    __tablename__ = "notification_deliveries"
    __table_args__ = (Index("ix_notification_deliveries_outbox_status", "outbox_id", "status"),)

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    outbox_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("notification_outbox.id", ondelete="CASCADE"))
    incident_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("operational_incidents.id", ondelete="CASCADE"))
    channel: Mapped[str] = mapped_column(String(30))
    recipient_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("project_notification_recipients.id", ondelete="SET NULL"))
    recipient_reference: Mapped[str] = mapped_column(String(120))
    idempotency_key: Mapped[str] = mapped_column(String(240), unique=True)
    status: Mapped[str] = mapped_column(String(30), default="PENDING", server_default="PENDING")
    attempt_count: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    last_attempt_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    next_retry_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    failed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    error_category: Mapped[str | None] = mapped_column(String(60))
    provider_message_id: Mapped[str | None] = mapped_column(String(120))
