"""Add actuator model feedback definitions and runtime MQTT metadata.

Revision ID: 0030
Revises: 0029
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op


revision = "0030"
down_revision = "0029"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    table_name = "actuator_model_feedback_definitions"
    if table_name not in inspector.get_table_names():
        op.create_table(
            table_name,
            sa.Column("id", sa.BigInteger(), sa.Identity(always=True), nullable=False),
        sa.Column("actuator_model_id", sa.BigInteger(), nullable=False),
        sa.Column("feedback_role", sa.String(40), nullable=False),
        sa.Column("sensor_model_id", sa.BigInteger(), nullable=False),
        sa.Column("value_key", sa.String(80), nullable=False),
        sa.Column("unit", sa.String(50), nullable=False),
        sa.Column("data_type", sa.String(30), nullable=False),
        sa.Column("is_required", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("is_enabled", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("display_order", sa.Integer(), server_default="0", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("feedback_role IN ('RUNNING_CURRENT')", name="role_allowed"),
        sa.CheckConstraint("data_type IN ('FLOAT')", name="data_type_allowed"),
        sa.CheckConstraint("display_order >= 0", name="order_nonnegative"),
        sa.ForeignKeyConstraint(["actuator_model_id"], ["actuator_models.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["sensor_model_id"], ["sensor_models.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("actuator_model_id", "feedback_role", name="uq_actuator_model_feedback_role"),
        )
        op.create_index("ix_actuator_model_feedback_definitions_actuator_model_id", table_name, ["actuator_model_id"])
        op.create_index("ix_actuator_model_feedback_definitions_sensor_model_id", table_name, ["sensor_model_id"])

    inspector = sa.inspect(bind)
    binding_columns = {column["name"] for column in inspector.get_columns("actuator_feedback_bindings")}
    additions = {
        "model_feedback_id": sa.Column("model_feedback_id", sa.BigInteger(), nullable=True),
        "value_key": sa.Column("value_key", sa.String(80), server_default="current_a", nullable=False),
        "unit": sa.Column("unit", sa.String(50), server_default="A", nullable=False),
        "data_type": sa.Column("data_type", sa.String(30), server_default="FLOAT", nullable=False),
    }
    for name, column in additions.items():
        if name not in binding_columns:
            op.add_column("actuator_feedback_bindings", column)
    inspector = sa.inspect(bind)
    foreign_keys = inspector.get_foreign_keys("actuator_feedback_bindings")
    if not any(item["constrained_columns"] == ["model_feedback_id"] for item in foreign_keys):
        op.create_foreign_key("fk_actuator_feedback_bindings_model_feedback", "actuator_feedback_bindings", table_name, ["model_feedback_id"], ["id"], ondelete="SET NULL")
    index_names = {item["name"] for item in inspector.get_indexes("actuator_feedback_bindings")}
    if "ix_actuator_feedback_bindings_model_feedback_id" not in index_names:
        op.create_index("ix_actuator_feedback_bindings_model_feedback_id", "actuator_feedback_bindings", ["model_feedback_id"])
    checks = {item["name"] for item in inspector.get_check_constraints("actuator_feedback_bindings")}
    if "ck_actuator_feedback_bindings_data_type_allowed" not in checks and "data_type_allowed" not in checks:
        op.create_check_constraint("data_type_allowed", "actuator_feedback_bindings", "data_type IN ('FLOAT')")


def downgrade() -> None:
    op.drop_constraint("data_type_allowed", "actuator_feedback_bindings", type_="check")
    op.drop_index("ix_actuator_feedback_bindings_model_feedback_id", table_name="actuator_feedback_bindings")
    op.drop_constraint("fk_actuator_feedback_bindings_model_feedback", "actuator_feedback_bindings", type_="foreignkey")
    for column in ("data_type", "unit", "value_key", "model_feedback_id"):
        op.drop_column("actuator_feedback_bindings", column)
    op.drop_index("ix_actuator_model_feedback_definitions_sensor_model_id", table_name="actuator_model_feedback_definitions")
    op.drop_index("ix_actuator_model_feedback_definitions_actuator_model_id", table_name="actuator_model_feedback_definitions")
    op.drop_table("actuator_model_feedback_definitions")
