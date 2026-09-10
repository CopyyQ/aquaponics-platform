"""Store direct Actuator electrical snapshot and configured threshold policy.

Revision ID: 0039
Revises: 0038
"""

from alembic import op
import sqlalchemy as sa

revision = "0039"
down_revision = "0038"
branch_labels = None
depends_on = None

_RISK = "('EXTREME','VERY_HIGH','HIGH','MEDIUM','LOW_MEDIUM','LOW')"


def upgrade() -> None:
    bind = op.get_bind()
    columns = {item["name"] for item in sa.inspect(bind).get_columns("actuators")}
    additions = {
        "voltage_v": sa.Float(), "current_a": sa.Float(),
        "electrical_recorded_at": sa.DateTime(timezone=True),
        "electrical_received_at": sa.DateTime(timezone=True),
        "status_received_at": sa.DateTime(timezone=True),
        "electrical_alerts_enabled": sa.Boolean(),
        "voltage_lower_threshold": sa.Float(), "voltage_upper_threshold": sa.Float(),
        "voltage_low_message": sa.Text(), "voltage_high_message": sa.Text(),
        "voltage_low_risk_level": sa.String(30), "voltage_high_risk_level": sa.String(30),
        "current_lower_threshold": sa.Float(), "current_upper_threshold": sa.Float(),
        "current_low_message": sa.Text(), "current_high_message": sa.Text(),
        "current_low_risk_level": sa.String(30), "current_high_risk_level": sa.String(30),
    }
    for name, type_ in additions.items():
        if name not in columns:
            op.add_column("actuators", sa.Column(name, type_, nullable=True))
    bind.execute(sa.text("""
        UPDATE actuators
        SET status_received_at = last_reported_at
        WHERE status_received_at IS NULL AND last_reported_at IS NOT NULL
    """))
    bind.execute(sa.text("UPDATE actuators SET electrical_alerts_enabled = false WHERE electrical_alerts_enabled IS NULL"))
    op.alter_column("actuators", "electrical_alerts_enabled", nullable=False, server_default=sa.false())
    checks = {item["name"] for item in sa.inspect(bind).get_check_constraints("actuators")}
    for name, condition in {
        "voltage_threshold_order": "voltage_lower_threshold IS NULL OR voltage_upper_threshold IS NULL OR voltage_lower_threshold < voltage_upper_threshold",
        "current_threshold_order": "current_lower_threshold IS NULL OR current_upper_threshold IS NULL OR current_lower_threshold < current_upper_threshold",
        "voltage_low_risk_allowed": f"voltage_low_risk_level IS NULL OR voltage_low_risk_level IN {_RISK}",
        "voltage_high_risk_allowed": f"voltage_high_risk_level IS NULL OR voltage_high_risk_level IN {_RISK}",
        "current_low_risk_allowed": f"current_low_risk_level IS NULL OR current_low_risk_level IN {_RISK}",
        "current_high_risk_allowed": f"current_high_risk_level IS NULL OR current_high_risk_level IN {_RISK}",
    }.items():
        if name not in checks:
            op.create_check_constraint(name, "actuators", condition)


def downgrade() -> None:
    raise RuntimeError("0039 is a retained-data forward migration; restore the verified backup if needed.")
