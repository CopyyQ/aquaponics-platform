"""Complete actuator template CRUD and Telegram risk policy.

Revision ID: 0029
Revises: 0028
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op


revision = "0029"
down_revision = "0028"
branch_labels = None
depends_on = None


RISK_ORDER = ("LOW", "LOW_MEDIUM", "MEDIUM", "HIGH", "VERY_HIGH", "EXTREME")


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    actuator_columns = {column["name"] for column in inspector.get_columns("device_template_actuators")}
    additions = {
        "code": sa.Column("code", sa.String(80), nullable=True),
        "actuator_type": sa.Column("actuator_type", sa.String(40), server_default="SWITCH", nullable=False),
        "default_state": sa.Column("default_state", sa.Boolean(), nullable=True),
        "command_capability": sa.Column("command_capability", sa.String(30), server_default="ON_OFF", nullable=False),
        "monitor_current": sa.Column("monitor_current", sa.Boolean(), server_default=sa.false(), nullable=False),
        "electrical_profile_id": sa.Column("electrical_profile_id", sa.BigInteger(), nullable=True),
        "is_enabled": sa.Column("is_enabled", sa.Boolean(), server_default=sa.true(), nullable=False),
    }
    for name, column in additions.items():
        if name not in actuator_columns:
            op.add_column("device_template_actuators", column)
    op.execute(
        """
        UPDATE device_template_actuators AS mapping
        SET code = model.code
        FROM actuator_models AS model
        WHERE model.id = mapping.actuator_model_id AND mapping.code IS NULL
        """
    )
    if "code" not in actuator_columns:
        op.alter_column("device_template_actuators", "code", nullable=False)
    inspector = sa.inspect(bind)
    unique_names = {item["name"] for item in inspector.get_unique_constraints("device_template_actuators")}
    if "uq_device_template_actuator_model" in unique_names:
        op.drop_constraint("uq_device_template_actuator_model", "device_template_actuators", type_="unique")
    if "uq_device_template_actuator_code" not in unique_names:
        op.create_unique_constraint("uq_device_template_actuator_code", "device_template_actuators", ["device_template_id", "code"])
    foreign_keys = inspector.get_foreign_keys("device_template_actuators")
    if not any(item["constrained_columns"] == ["electrical_profile_id"] for item in foreign_keys):
        op.create_foreign_key("fk_device_template_actuators_electrical_profile", "device_template_actuators", "alert_rule_profiles", ["electrical_profile_id"], ["id"], ondelete="RESTRICT")
    index_names = {item["name"] for item in inspector.get_indexes("device_template_actuators")}
    if "ix_device_template_actuators_electrical_profile_id" not in index_names:
        op.create_index("ix_device_template_actuators_electrical_profile_id", "device_template_actuators", ["electrical_profile_id"])

    notification_columns = {column["name"] for column in sa.inspect(bind).get_columns("project_notification_settings")}
    for risk in RISK_ORDER:
        name = f"risk_{risk.lower()}_enabled"
        if name not in notification_columns:
            op.add_column("project_notification_settings", sa.Column(name, sa.Boolean(), server_default=sa.true(), nullable=False))
    if "notify_alert_recovered" not in notification_columns:
        op.add_column("project_notification_settings", sa.Column("notify_alert_recovered", sa.Boolean(), server_default=sa.true(), nullable=False))
    for risk in RISK_ORDER:
        op.execute(
            sa.text(
                f"""
                UPDATE project_notification_settings
                SET risk_{risk.lower()}_enabled =
                    CASE minimum_business_risk_level
                        WHEN 'LOW' THEN true
                        WHEN 'LOW_MEDIUM' THEN :risk_order >= 1
                        WHEN 'MEDIUM' THEN :risk_order >= 2
                        WHEN 'HIGH' THEN :risk_order >= 3
                        WHEN 'VERY_HIGH' THEN :risk_order >= 4
                        WHEN 'EXTREME' THEN :risk_order >= 5
                        ELSE true
                    END
                """
            ).bindparams(risk_order=RISK_ORDER.index(risk))
        )


def downgrade() -> None:
    op.drop_column("project_notification_settings", "notify_alert_recovered")
    for risk in reversed(RISK_ORDER):
        op.drop_column("project_notification_settings", f"risk_{risk.lower()}_enabled")
    op.drop_index("ix_device_template_actuators_electrical_profile_id", table_name="device_template_actuators")
    op.drop_constraint("fk_device_template_actuators_electrical_profile", "device_template_actuators", type_="foreignkey")
    op.drop_constraint("uq_device_template_actuator_code", "device_template_actuators", type_="unique")
    op.create_unique_constraint("uq_device_template_actuator_model", "device_template_actuators", ["device_template_id", "actuator_model_id"])
    for column in ("is_enabled", "electrical_profile_id", "monitor_current", "command_capability", "default_state", "actuator_type", "code"):
        op.drop_column("device_template_actuators", column)
