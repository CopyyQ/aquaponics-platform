"""Make Sensor threshold configuration the canonical incident source.

Revision ID: 0035
Revises: 0034
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "0035"
down_revision = "0034"
branch_labels = None
depends_on = None

RISK_VALUES = "'EXTREME','VERY_HIGH','HIGH','MEDIUM','LOW_MEDIUM','LOW'"


def upgrade() -> None:
    op.add_column("sensors", sa.Column("below_threshold_message", sa.Text(), nullable=True))
    op.add_column("sensors", sa.Column("above_threshold_message", sa.Text(), nullable=True))
    op.add_column("sensors", sa.Column("alert_risk_level", sa.String(length=30), nullable=True))
    op.create_check_constraint("sensor_alert_risk_allowed", "sensors", f"alert_risk_level IS NULL OR alert_risk_level IN ({RISK_VALUES})")

    op.add_column("sensor_models", sa.Column("default_warning_enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")))
    op.add_column("sensor_models", sa.Column("default_below_threshold_message", sa.Text(), nullable=True))
    op.add_column("sensor_models", sa.Column("default_above_threshold_message", sa.Text(), nullable=True))
    op.add_column("sensor_models", sa.Column("default_alert_risk_level", sa.String(length=30), nullable=True))
    op.create_check_constraint("sensor_model_default_alert_risk_allowed", "sensor_models", f"default_alert_risk_level IS NULL OR default_alert_risk_level IN ({RISK_VALUES})")

    op.add_column("device_template_sensors", sa.Column("default_warning_enabled", sa.Boolean(), nullable=True))
    op.add_column("device_template_sensors", sa.Column("default_below_threshold_message", sa.Text(), nullable=True))
    op.add_column("device_template_sensors", sa.Column("default_above_threshold_message", sa.Text(), nullable=True))
    op.add_column("device_template_sensors", sa.Column("default_alert_risk_level", sa.String(length=30), nullable=True))
    op.create_check_constraint("template_sensor_default_alert_risk_allowed", "device_template_sensors", f"default_alert_risk_level IS NULL OR default_alert_risk_level IN ({RISK_VALUES})")

    op.alter_column("operational_incidents", "rule_id", existing_type=sa.BigInteger(), nullable=True)
    op.alter_column("operational_incidents", "rule_revision_id", existing_type=sa.BigInteger(), nullable=True)
    op.create_index(
        "uq_active_sensor_threshold_incident",
        "operational_incidents",
        ["project_id", "context_key"],
        unique=True,
        postgresql_where=sa.text("rule_id IS NULL AND status IN ('PENDING','OPEN','ACKNOWLEDGED','NORMALIZED')"),
    )


def downgrade() -> None:
    raise RuntimeError("0035 preserves canonical Sensor incidents; downgrade requires an explicit data migration plan.")
