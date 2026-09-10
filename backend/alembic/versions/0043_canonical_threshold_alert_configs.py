"""Create the sole runtime threshold configuration table.

Revision ID: 0043
Revises: 0042
"""

from alembic import op
import sqlalchemy as sa

revision = "0043"
down_revision = "0042"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Historical 0001 imports current metadata on a fresh database.  In that
    # path the table already exists and there is no pre-0043 runtime data to
    # backfill; leave it intact for the remaining revision chain.
    if sa.inspect(op.get_bind()).has_table("threshold_alert_configs"):
        # The table may have been materialized by 0001's metadata bootstrap.
        # Still perform the data-only part of this revision for a 0035 upgrade.
        op.execute(sa.text("""
            INSERT INTO threshold_alert_configs (sensor_id, metric_type, enabled, lower_threshold, upper_threshold, below_risk_level, above_risk_level, below_message, above_message)
            SELECT id, 'SENSOR_VALUE', COALESCE(alerts_enabled, warning_enabled, true), lower_threshold, upper_threshold, below_risk_level, above_risk_level, below_threshold_message, above_threshold_message
            FROM sensors WHERE lower_threshold IS NOT NULL OR upper_threshold IS NOT NULL OR below_risk_level IS NOT NULL OR above_risk_level IS NOT NULL OR below_threshold_message IS NOT NULL OR above_threshold_message IS NOT NULL
            ON CONFLICT (sensor_id) DO NOTHING
        """))
        op.execute(sa.text("""
            INSERT INTO threshold_alert_configs (actuator_id, metric_type, enabled, lower_threshold, upper_threshold, below_risk_level, above_risk_level, below_message, above_message)
            SELECT id, 'VOLTAGE', electrical_alerts_enabled, voltage_lower_threshold, voltage_upper_threshold, voltage_low_risk_level, voltage_high_risk_level, voltage_low_message, voltage_high_message
            FROM actuators WHERE voltage_lower_threshold IS NOT NULL OR voltage_upper_threshold IS NOT NULL OR voltage_low_risk_level IS NOT NULL OR voltage_high_risk_level IS NOT NULL OR voltage_low_message IS NOT NULL OR voltage_high_message IS NOT NULL
            ON CONFLICT (actuator_id, metric_type) DO NOTHING
        """))
        op.execute(sa.text("""
            INSERT INTO threshold_alert_configs (actuator_id, metric_type, enabled, lower_threshold, upper_threshold, below_risk_level, above_risk_level, below_message, above_message)
            SELECT id, 'CURRENT', electrical_alerts_enabled, current_lower_threshold, current_upper_threshold, current_low_risk_level, current_high_risk_level, current_low_message, current_high_message
            FROM actuators WHERE current_lower_threshold IS NOT NULL OR current_upper_threshold IS NOT NULL OR current_low_risk_level IS NOT NULL OR current_high_risk_level IS NOT NULL OR current_low_message IS NOT NULL OR current_high_message IS NOT NULL
            ON CONFLICT (actuator_id, metric_type) DO NOTHING
        """))
        return
    op.create_table(
        "threshold_alert_configs",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=True), primary_key=True),
        sa.Column("sensor_id", sa.BigInteger(), sa.ForeignKey("sensors.id", ondelete="CASCADE")),
        sa.Column("actuator_id", sa.BigInteger(), sa.ForeignKey("actuators.id", ondelete="CASCADE")),
        sa.Column("metric_type", sa.String(30), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("lower_threshold", sa.Float()), sa.Column("upper_threshold", sa.Float()),
        sa.Column("below_risk_level", sa.String(30)), sa.Column("above_risk_level", sa.String(30)),
        sa.Column("below_message", sa.Text()), sa.Column("above_message", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("(sensor_id IS NOT NULL AND actuator_id IS NULL) OR (sensor_id IS NULL AND actuator_id IS NOT NULL)", name="exactly_one_resource"),
        sa.CheckConstraint("(sensor_id IS NOT NULL AND metric_type = 'SENSOR_VALUE') OR (actuator_id IS NOT NULL AND metric_type IN ('VOLTAGE','CURRENT'))", name="metric_matches_resource"),
        sa.CheckConstraint("lower_threshold IS NULL OR upper_threshold IS NULL OR lower_threshold <= upper_threshold", name="threshold_order"),
        sa.CheckConstraint("below_risk_level IS NULL OR below_risk_level IN ('EXTREME','VERY_HIGH','HIGH','MEDIUM','LOW_MEDIUM','LOW')", name="below_risk_allowed"),
        sa.CheckConstraint("above_risk_level IS NULL OR above_risk_level IN ('EXTREME','VERY_HIGH','HIGH','MEDIUM','LOW_MEDIUM','LOW')", name="above_risk_allowed"),
        sa.UniqueConstraint("sensor_id", name="uq_threshold_alert_config_sensor"),
        sa.UniqueConstraint("actuator_id", "metric_type", name="uq_threshold_alert_config_actuator_metric"),
    )
    op.create_index("ix_threshold_alert_configs_sensor", "threshold_alert_configs", ["sensor_id"])
    op.create_index("ix_threshold_alert_configs_actuator_metric", "threshold_alert_configs", ["actuator_id", "metric_type"])
    # Backfill only explicit Sensor policy. Catalog/template defaults are not
    # runtime sources and are deliberately not materialized.
    op.execute(sa.text("""
        INSERT INTO threshold_alert_configs (
          sensor_id, metric_type, enabled, lower_threshold, upper_threshold,
          below_risk_level, above_risk_level, below_message, above_message
        )
        SELECT id, 'SENSOR_VALUE', COALESCE(alerts_enabled, warning_enabled, true),
          lower_threshold, upper_threshold, below_risk_level, above_risk_level,
          below_threshold_message, above_threshold_message
        FROM sensors
        WHERE lower_threshold IS NOT NULL OR upper_threshold IS NOT NULL
           OR below_risk_level IS NOT NULL OR above_risk_level IS NOT NULL
           OR below_threshold_message IS NOT NULL OR above_threshold_message IS NOT NULL
        ON CONFLICT (sensor_id) DO NOTHING
    """))
    # Explicit Actuator policy wins over historical feedback bindings.  The
    # latter are deliberately not read here: they can represent generated
    # Sensors and are retained only as historical compatibility data.
    op.execute(sa.text("""
        INSERT INTO threshold_alert_configs (
          actuator_id, metric_type, enabled, lower_threshold, upper_threshold,
          below_risk_level, above_risk_level, below_message, above_message
        )
        SELECT id, 'VOLTAGE', electrical_alerts_enabled,
          voltage_lower_threshold, voltage_upper_threshold,
          voltage_low_risk_level, voltage_high_risk_level,
          voltage_low_message, voltage_high_message
        FROM actuators
        WHERE voltage_lower_threshold IS NOT NULL OR voltage_upper_threshold IS NOT NULL
           OR voltage_low_risk_level IS NOT NULL OR voltage_high_risk_level IS NOT NULL
           OR voltage_low_message IS NOT NULL OR voltage_high_message IS NOT NULL
        ON CONFLICT (actuator_id, metric_type) DO NOTHING
    """))
    op.execute(sa.text("""
        INSERT INTO threshold_alert_configs (
          actuator_id, metric_type, enabled, lower_threshold, upper_threshold,
          below_risk_level, above_risk_level, below_message, above_message
        )
        SELECT id, 'CURRENT', electrical_alerts_enabled,
          current_lower_threshold, current_upper_threshold,
          current_low_risk_level, current_high_risk_level,
          current_low_message, current_high_message
        FROM actuators
        WHERE current_lower_threshold IS NOT NULL OR current_upper_threshold IS NOT NULL
           OR current_low_risk_level IS NOT NULL OR current_high_risk_level IS NOT NULL
           OR current_low_message IS NOT NULL OR current_high_message IS NOT NULL
        ON CONFLICT (actuator_id, metric_type) DO NOTHING
    """))


def downgrade() -> None:
    raise RuntimeError("0043 is a retained-data forward migration; restore a verified backup for rollback.")
