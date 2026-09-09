from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, Boolean, CheckConstraint, Float, ForeignKey, Identity, Index, Integer, String, Text, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, SoftDeleteMixin, TimestampMixin

if TYPE_CHECKING:
    from app.models.device import Device
    from app.models.sensor import SensorModel
    from app.models.actuator_model import ActuatorModel
    from app.models.operational_alert import AlertRuleProfile


class DeviceTemplate(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "device_templates"
    __table_args__ = (
        UniqueConstraint("code", name="uq_device_templates_code"),
        Index("ix_device_templates_code", "code"),
        CheckConstraint(
            "nominal_output_voltage_v IS NULL OR nominal_output_voltage_v > 0",
            name="nominal_voltage_positive",
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    code: Mapped[str] = mapped_column(String(80), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    notes: Mapped[str | None] = mapped_column(Text)
    nominal_output_voltage_v: Mapped[float | None] = mapped_column(Float)
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)

    sensor_mappings: Mapped[list[DeviceTemplateSensor]] = relationship(
        back_populates="device_template", cascade="all, delete-orphan", order_by="DeviceTemplateSensor.sort_order"
    )
    actuator_mappings: Mapped[list["DeviceTemplateActuator"]] = relationship(
        back_populates="device_template", cascade="all, delete-orphan",
        order_by="DeviceTemplateActuator.sort_order",
    )
    devices: Mapped[list["Device"]] = relationship(back_populates="device_template")


class DeviceTemplateSensor(Base, TimestampMixin):
    __tablename__ = "device_template_sensors"
    __table_args__ = (
        UniqueConstraint("device_template_id", "code", name="uq_device_template_sensor_code"),
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    device_template_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("device_templates.id", ondelete="CASCADE"), nullable=False, index=True
    )
    sensor_model_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("sensor_models.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    code: Mapped[str] = mapped_column(String(80), nullable=False)
    display_name: Mapped[str | None] = mapped_column(String(255))
    default_location: Mapped[str | None] = mapped_column(String(255))
    default_lower_threshold: Mapped[float | None] = mapped_column(Float)
    default_upper_threshold: Mapped[float | None] = mapped_column(Float)
    legacy_default_warning_enabled: Mapped[bool | None] = mapped_column("default_warning_enabled")
    default_alerts_enabled: Mapped[bool | None] = mapped_column(Boolean)
    default_below_threshold_message: Mapped[str | None] = mapped_column(Text)
    default_above_threshold_message: Mapped[str | None] = mapped_column(Text)
    default_below_risk_level: Mapped[str | None] = mapped_column(String(30))
    default_above_risk_level: Mapped[str | None] = mapped_column(String(30))
    legacy_default_alert_risk_level: Mapped[str | None] = mapped_column("default_alert_risk_level", String(30))
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_required: Mapped[bool] = mapped_column(default=False, server_default="false", nullable=False)

    device_template: Mapped[DeviceTemplate] = relationship(back_populates="sensor_mappings")
    sensor_model: Mapped["SensorModel"] = relationship(back_populates="template_mappings")


class DeviceTemplateActuator(Base, TimestampMixin):
    __tablename__ = "device_template_actuators"
    __table_args__ = (
        UniqueConstraint("device_template_id", "code", name="uq_device_template_actuator_code"),
        Index("ix_device_template_actuators_template_id", "device_template_id"),
        Index("ix_device_template_actuators_actuator_model_id", "actuator_model_id"),
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    device_template_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("device_templates.id", ondelete="CASCADE"))
    actuator_model_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("actuator_models.id", ondelete="RESTRICT"))
    code: Mapped[str] = mapped_column(String(80), nullable=False)
    default_name: Mapped[str | None] = mapped_column(String(255))
    default_location: Mapped[str | None] = mapped_column(String(255))
    default_notes: Mapped[str | None] = mapped_column(Text)
    actuator_type: Mapped[str] = mapped_column(String(40), default="SWITCH", server_default="SWITCH", nullable=False)
    default_state: Mapped[bool | None] = mapped_column(Boolean)
    command_capability: Mapped[str] = mapped_column(String(30), default="ON_OFF", server_default="ON_OFF", nullable=False)
    monitor_current: Mapped[bool] = mapped_column(Boolean, default=False, server_default=text("false"), nullable=False)
    electrical_profile_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("alert_rule_profiles.id", ondelete="RESTRICT"), index=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_required: Mapped[bool] = mapped_column(default=False, nullable=False)
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True, server_default=text("true"), nullable=False)

    device_template: Mapped[DeviceTemplate] = relationship(back_populates="actuator_mappings")
    actuator_model: Mapped["ActuatorModel"] = relationship()
    electrical_profile: Mapped["AlertRuleProfile | None"] = relationship("AlertRuleProfile")
