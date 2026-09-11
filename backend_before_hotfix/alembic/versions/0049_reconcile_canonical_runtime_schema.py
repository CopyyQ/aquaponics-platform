"""Reconcile historical runtime artifacts with the canonical ORM schema."""

from alembic import op
import sqlalchemy as sa


revision = "0049"
down_revision = "0048"
branch_labels = None
depends_on = None


def _drop_constraint_if_present(table: str, name: str) -> None:
    bind = op.get_bind()
    names = {item["name"] for item in sa.inspect(bind).get_check_constraints(table)}
    if name in names:
        # Alembic's naming convention would prepend ``ck_<table>_`` to an
        # already fully-qualified historical constraint name.  Use PostgreSQL
        # DDL directly so the exact inspected name is dropped.
        bind.execute(sa.text(f'ALTER TABLE "{table}" DROP CONSTRAINT IF EXISTS "{name}"'))


def _drop_index_if_present(table: str, name: str) -> None:
    bind = op.get_bind()
    names = {item["name"] for item in sa.inspect(bind).get_indexes(table)}
    if name in names:
        op.drop_index(name, table_name=table)


def upgrade() -> None:
    bind = op.get_bind()

    # Feedback purpose was only meaningful to the retired Sensor-backed
    # actuator architecture. Existing measurements were copied in 0041.
    sensor_columns = {item["name"] for item in sa.inspect(bind).get_columns("sensors")}
    if "purpose" in sensor_columns:
        _drop_index_if_present("sensors", "ix_sensors_purpose")
        op.drop_column("sensors", "purpose")
    archive_tables = set(sa.inspect(bind).get_table_names())
    if "legacy_sensor_classifications" in archive_tables:
        archive_columns = {
            item["name"] for item in sa.inspect(bind).get_columns("legacy_sensor_classifications")
        }
        if "legacy_purpose" in archive_columns:
            op.alter_column(
                "legacy_sensor_classifications",
                "legacy_purpose",
                existing_type=sa.Enum(name="sensor_purpose"),
                type_=sa.String(40),
                postgresql_using="legacy_purpose::text",
            )
    bind.execute(sa.text("DROP TYPE IF EXISTS sensor_purpose"))

    for name in (
        "ck_actuators_current_high_risk_allowed",
        "ck_actuators_current_low_risk_allowed",
        "ck_actuators_current_threshold_order",
        "ck_actuators_voltage_high_risk_allowed",
        "ck_actuators_voltage_low_risk_allowed",
        "ck_actuators_voltage_threshold_order",
    ):
        _drop_constraint_if_present("actuators", name)
    for name in (
        "ck_sensors_above_risk_allowed",
        "ck_sensors_below_risk_allowed",
        "ck_sensors_sensor_alert_risk_allowed",
    ):
        _drop_constraint_if_present("sensors", name)
    for name in (
        "ck_device_template_sensors_template_sensor_above_risk_allowed",
        "ck_device_template_sensors_template_sensor_below_risk_allowed",
        "ck_device_template_sensors_template_sensor_default_aler_155f",
    ):
        _drop_constraint_if_present("device_template_sensors", name)
    _drop_constraint_if_present("sensor_models", "ck_sensor_models_sensor_model_default_alert_risk_allowed")

    op.alter_column("device_template_sensors", "slot_code", existing_type=sa.String(80), nullable=True)
    if "alerts_enabled" not in sensor_columns:
        op.add_column("sensors", sa.Column("alerts_enabled", sa.Boolean(), nullable=False, server_default=sa.true()))
    op.alter_column("sensors", "alerts_enabled", server_default=None)
    op.alter_column("sensor_models", "default_warning_enabled", server_default=None)
    op.alter_column("roles", "is_system", server_default=None)
    op.alter_column("roles", "enabled", server_default=None)

    # Current models use a non-native VARCHAR role value. Convert the old enum
    # after preserving every existing value, including TECHNICIAN.
    bind.execute(sa.text("ALTER TABLE users ALTER COLUMN system_role TYPE VARCHAR(10) USING system_role::text"))
    bind.execute(sa.text("DROP TYPE IF EXISTS user_system_role"))

    _drop_index_if_present("operational_incidents", "uq_active_sensor_threshold_incident")
    for table, name, columns in (
        ("actuator_readings", "ix_actuator_readings_actuator_id", ["actuator_id"]),
        ("role_permissions", "ix_role_permissions_role_id", ["role_id"]),
        ("role_permissions", "ix_role_permissions_permission_id", ["permission_id"]),
        ("users", "ix_users_role_id", ["role_id"]),
    ):
        if name not in {item["name"] for item in sa.inspect(bind).get_indexes(table)}:
            op.create_index(name, table, columns)


def downgrade() -> None:
    raise RuntimeError("0049 reconciles historical schema artifacts; restore a verified backup to roll back.")
