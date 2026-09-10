"""Add template slot identity and split Sensor threshold risk directions.

Revision ID: 0038
Revises: 0037
"""

from alembic import op
import sqlalchemy as sa

revision = "0038"
down_revision = "0037"
branch_labels = None
depends_on = None

_RISK = "('EXTREME','VERY_HIGH','HIGH','MEDIUM','LOW_MEDIUM','LOW')"


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {item["name"] for item in inspector.get_columns("device_template_sensors")}
    if "slot_code" not in columns:
        op.add_column("device_template_sensors", sa.Column("slot_code", sa.String(80), nullable=True))
    bind.execute(sa.text("UPDATE device_template_sensors SET slot_code = 'SLOT-' || id::text WHERE slot_code IS NULL"))
    op.alter_column("device_template_sensors", "slot_code", nullable=False)
    uniques = {item["name"] for item in inspector.get_unique_constraints("device_template_sensors")}
    if "uq_device_template_sensor_model" in uniques:
        op.drop_constraint("uq_device_template_sensor_model", "device_template_sensors", type_="unique")
    if "uq_device_template_sensor_slot" not in uniques:
        op.create_unique_constraint("uq_device_template_sensor_slot", "device_template_sensors", ["device_template_id", "slot_code"])

    inspector = sa.inspect(bind)
    sensor_columns = {item["name"] for item in inspector.get_columns("sensors")}
    if "alerts_enabled" not in sensor_columns:
        op.add_column("sensors", sa.Column("alerts_enabled", sa.Boolean(), nullable=True))
        bind.execute(sa.text("UPDATE sensors SET alerts_enabled = COALESCE(warning_enabled, true)"))
        op.alter_column("sensors", "alerts_enabled", nullable=False, server_default=sa.true())
    for name in ("below_risk_level", "above_risk_level"):
        if name not in sensor_columns:
            op.add_column("sensors", sa.Column(name, sa.String(30), nullable=True))
    bind.execute(sa.text("""
        UPDATE sensors
        SET below_risk_level = COALESCE(below_risk_level, alert_risk_level),
            above_risk_level = COALESCE(above_risk_level, alert_risk_level)
    """))
    checks = {item["name"] for item in sa.inspect(bind).get_check_constraints("sensors")}
    for name, column in (("below_risk_allowed", "below_risk_level"), ("above_risk_allowed", "above_risk_level")):
        if name not in checks:
            op.create_check_constraint(name, "sensors", f"{column} IS NULL OR {column} IN {_RISK}")


def downgrade() -> None:
    raise RuntimeError(
        "0038 materializes slot identifiers and split risk directions. Restore the "
        "verified backup or use a forward migration."
    )
