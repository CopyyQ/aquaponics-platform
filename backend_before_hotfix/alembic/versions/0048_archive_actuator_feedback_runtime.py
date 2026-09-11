"""Archive the obsolete Sensor-backed actuator feedback runtime.

Revision ID: 0048
Revises: 0047

Revision 0041 already copied every feedback telemetry sample into
``actuator_readings`` and refreshed the direct Actuator electrical snapshot.
This revision keeps the old configuration rows as explicitly named archive
tables while removing their evaluator types from active runtime policy.
"""

from alembic import op
import sqlalchemy as sa


revision = "0048"
down_revision = "0047"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()

    bind.execute(sa.text("""
        CREATE TABLE legacy_alert_rule_evaluator_classifications AS
        SELECT id AS alert_rule_id, evaluator_type AS legacy_evaluator_type
        FROM alert_rules
        WHERE evaluator_type IN ('ACTUATOR_FEEDBACK', 'SCHEDULE_FEEDBACK')
    """))
    bind.execute(sa.text("""
        UPDATE alert_rules
        SET is_enabled = false,
            evaluator_type = 'DIGITAL_STATE'
        WHERE evaluator_type IN ('ACTUATOR_FEEDBACK', 'SCHEDULE_FEEDBACK')
    """))

    op.drop_constraint("alert_rule_evaluator_type_allowed", "alert_rules", type_="check")
    op.create_check_constraint(
        "alert_rule_evaluator_type_allowed",
        "alert_rules",
        "evaluator_type IN ('THRESHOLD','THRESHOLD_BANDS','RANGE_BANDS','DIGITAL_STATE','THRESHOLD_DURATION','BASELINE_DEVIATION','WINDOW_DURATION','TREND')",
    )

    op.rename_table("actuator_feedback_bindings", "legacy_actuator_feedback_bindings")
    op.rename_table("actuator_model_feedback_definitions", "legacy_actuator_model_feedback_definitions")


def downgrade() -> None:
    raise RuntimeError(
        "0048 archives obsolete actuator feedback configuration. Restore the verified backup to roll back."
    )
