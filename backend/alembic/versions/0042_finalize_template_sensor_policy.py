"""Finalize typed template mappings and directional Sensor policy.

Revision ID: 0042
Revises: 0041
"""

from alembic import op
import sqlalchemy as sa

revision = "0042"
down_revision = "0041"
branch_labels = None
depends_on = None

_RISK = "('EXTREME','VERY_HIGH','HIGH','MEDIUM','LOW_MEDIUM','LOW')"


def upgrade() -> None:
    bind = op.get_bind()
    columns = {item["name"] for item in sa.inspect(bind).get_columns("device_template_sensors")}
    additions = {
        "default_alerts_enabled": sa.Boolean(),
        "default_below_risk_level": sa.String(30),
        "default_above_risk_level": sa.String(30),
    }
    for name, type_ in additions.items():
        if name not in columns:
            op.add_column("device_template_sensors", sa.Column(name, type_, nullable=True))
    bind.execute(sa.text("""
        UPDATE device_template_sensors
        SET default_alerts_enabled = COALESCE(default_alerts_enabled, default_warning_enabled),
            default_below_risk_level = COALESCE(default_below_risk_level, default_alert_risk_level),
            default_above_risk_level = COALESCE(default_above_risk_level, default_alert_risk_level)
    """))
    checks = {item["name"] for item in sa.inspect(bind).get_check_constraints("device_template_sensors")}
    for name, column in (("template_sensor_below_risk_allowed", "default_below_risk_level"), ("template_sensor_above_risk_allowed", "default_above_risk_level")):
        if name not in checks:
            op.create_check_constraint(name, "device_template_sensors", f"{column} IS NULL OR {column} IN {_RISK}")

    # Enforce template/device topology for all future writes. Existing mixed
    # hardware stays readable under its explicit compatibility marker.
    bind.execute(sa.text("""
        CREATE OR REPLACE FUNCTION enforce_device_component_type() RETURNS trigger AS $$
        BEGIN
          IF TG_TABLE_NAME = 'sensors' AND NOT EXISTS (
            SELECT 1 FROM devices d WHERE d.id = NEW.device_id
              AND (d.device_type = 'SENSOR_DEVICE' OR d.is_legacy_mixed)
          ) THEN RAISE EXCEPTION 'Sensors require SENSOR_DEVICE'; END IF;
          IF TG_TABLE_NAME = 'actuators' AND NOT EXISTS (
            SELECT 1 FROM devices d WHERE d.id = NEW.device_id
              AND (d.device_type = 'ACTUATOR_DEVICE' OR d.is_legacy_mixed)
          ) THEN RAISE EXCEPTION 'Actuators require ACTUATOR_DEVICE'; END IF;
          RETURN NEW;
        END; $$ LANGUAGE plpgsql
    """))
    bind.execute(sa.text("DROP TRIGGER IF EXISTS sensors_device_type_guard ON sensors"))
    bind.execute(sa.text("""
        CREATE TRIGGER sensors_device_type_guard BEFORE INSERT OR UPDATE OF device_id ON sensors
        FOR EACH ROW EXECUTE FUNCTION enforce_device_component_type()
    """))
    bind.execute(sa.text("DROP TRIGGER IF EXISTS actuators_device_type_guard ON actuators"))
    bind.execute(sa.text("""
        CREATE TRIGGER actuators_device_type_guard BEFORE INSERT OR UPDATE OF device_id ON actuators
        FOR EACH ROW EXECUTE FUNCTION enforce_device_component_type()
    """))


def downgrade() -> None:
    raise RuntimeError("0042 introduces final topology guards; restore the verified backup for rollback.")
