from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, Boolean, CheckConstraint, Float, ForeignKey, Identity, Integer, String, DateTime, Text, UniqueConstraint, func, text
from app.db.base import SoftDeleteMixin
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class ActuatorModel(Base, SoftDeleteMixin):
    __tablename__ = "actuator_models"
    __table_args__ = (UniqueConstraint("code", name="uq_actuator_models_code"),)

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    code: Mapped[str] = mapped_column(String(80))
    name: Mapped[str] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(Text)
    data_type: Mapped[str] = mapped_column(String(30), default="BOOLEAN", nullable=False)
    default_state: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    feedback_definitions: Mapped[list["ActuatorModelFeedbackDefinition"]] = relationship(
        back_populates="actuator_model",
        cascade="all, delete-orphan",
        order_by="ActuatorModelFeedbackDefinition.display_order",
    )


class ActuatorModelFeedbackDefinition(Base):
    __tablename__ = "actuator_model_feedback_definitions"
    __table_args__ = (
        UniqueConstraint("actuator_model_id", "feedback_role", name="uq_actuator_model_feedback_role"),
        CheckConstraint("feedback_role IN ('SUPPLY_VOLTAGE','RUNNING_CURRENT')", name="role_allowed"),
        CheckConstraint("data_type IN ('FLOAT')", name="data_type_allowed"),
        CheckConstraint("display_order >= 0", name="order_nonnegative"),
        CheckConstraint("default_lower_threshold IS NULL OR default_upper_threshold IS NULL OR default_lower_threshold < default_upper_threshold", name="threshold_order"),
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    actuator_model_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("actuator_models.id", ondelete="CASCADE"), index=True)
    feedback_role: Mapped[str] = mapped_column(String(40), nullable=False)
    sensor_model_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("sensor_models.id", ondelete="RESTRICT"), index=True)
    value_key: Mapped[str] = mapped_column(String(80), nullable=False)
    unit: Mapped[str] = mapped_column(String(50), nullable=False)
    data_type: Mapped[str] = mapped_column(String(30), nullable=False)
    default_lower_threshold: Mapped[float | None] = mapped_column(Float)
    default_upper_threshold: Mapped[float | None] = mapped_column(Float)
    is_required: Mapped[bool] = mapped_column(Boolean, default=True, server_default=text("true"), nullable=False)
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True, server_default=text("true"), nullable=False)
    display_order: Mapped[int] = mapped_column(Integer, default=0, server_default="0", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    actuator_model: Mapped[ActuatorModel] = relationship(back_populates="feedback_definitions")
    sensor_model = relationship("SensorModel")
