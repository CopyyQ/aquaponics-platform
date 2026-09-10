"""Complete canonical Telegram alert reconciliation.

Revision ID: 0053
Revises: 0052
"""

from alembic import op
import sqlalchemy as sa

revision = "0053"
down_revision = "0052"
branch_labels = None
depends_on = None


def _columns(table: str) -> set[str]:
    return {column["name"] for column in sa.inspect(op.get_bind()).get_columns(table)}


def upgrade() -> None:
    threshold_columns = _columns("threshold_alert_configs")
    if "delay_seconds" not in threshold_columns:
        op.add_column(
            "threshold_alert_configs",
            sa.Column("delay_seconds", sa.Integer(), nullable=False, server_default="0"),
        )
        op.create_check_constraint(
            "delay_nonnegative",
            "threshold_alert_configs",
            "delay_seconds >= 0",
        )
        op.execute(sa.text("""
            UPDATE threshold_alert_configs AS config
            SET delay_seconds = COALESCE(sensor.alert_delay_seconds, 0)
            FROM sensors AS sensor
            WHERE config.sensor_id = sensor.id
        """))

    settings_columns = _columns("project_notification_settings")
    if "enabled" not in settings_columns:
        op.add_column(
            "project_notification_settings",
            sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        )
    if "notification_generation" not in settings_columns:
        op.add_column(
            "project_notification_settings",
            sa.Column("notification_generation", sa.Integer(), nullable=False, server_default="0"),
        )
        op.create_check_constraint(
            "notification_generation_nonnegative",
            "project_notification_settings",
            "notification_generation >= 0",
        )

    outbox_columns = _columns("notification_outbox")
    if "target_recipient_id" not in outbox_columns:
        op.add_column(
            "notification_outbox",
            sa.Column(
                "target_recipient_id",
                sa.BigInteger(),
                sa.ForeignKey("project_notification_recipients.id", ondelete="SET NULL"),
                nullable=True,
            ),
        )
        op.create_index(
            "ix_notification_outbox_target_recipient_id",
            "notification_outbox",
            ["target_recipient_id"],
        )

    delivery_columns = _columns("notification_deliveries")
    if "provider_status_code" not in delivery_columns:
        op.add_column("notification_deliveries", sa.Column("provider_status_code", sa.Integer()))
    if "error_message" not in delivery_columns:
        op.add_column("notification_deliveries", sa.Column("error_message", sa.Text()))

    actuator_model_columns = _columns("actuator_models")
    for name in (
        "nominal_voltage_v",
        "voltage_tolerance_v",
        "zero_voltage_max_v",
        "minimum_running_current_a",
        "maximum_running_current_a",
    ):
        if name not in actuator_model_columns:
            op.add_column("actuator_models", sa.Column(name, sa.Float()))
    constraints = {
        item["name"] for item in sa.inspect(op.get_bind()).get_check_constraints("actuator_models")
    }
    if "ck_actuator_models_electrical_values_nonnegative" not in constraints:
        op.create_check_constraint(
            "electrical_values_nonnegative",
            "actuator_models",
            "(nominal_voltage_v IS NULL OR nominal_voltage_v > 0) AND "
            "(voltage_tolerance_v IS NULL OR voltage_tolerance_v >= 0) AND "
            "(zero_voltage_max_v IS NULL OR zero_voltage_max_v >= 0) AND "
            "(minimum_running_current_a IS NULL OR minimum_running_current_a >= 0) AND "
            "(maximum_running_current_a IS NULL OR maximum_running_current_a >= 0) AND "
            "(minimum_running_current_a IS NULL OR maximum_running_current_a IS NULL OR "
            "minimum_running_current_a <= maximum_running_current_a)",
        )
    op.execute(sa.text("""
        UPDATE actuator_models
        SET nominal_voltage_v = COALESCE(nominal_voltage_v, 12.0),
            voltage_tolerance_v = COALESCE(voltage_tolerance_v, 1.5),
            zero_voltage_max_v = COALESCE(zero_voltage_max_v, 1.0),
            minimum_running_current_a = COALESCE(minimum_running_current_a, 0.10),
            maximum_running_current_a = COALESCE(maximum_running_current_a, 10.0)
        WHERE code IN ('FISH_TANK_PUMP','IRRIGATION_PUMP','MIST_SYSTEM','GROW_LIGHT','AIR_PUMP')
    """))

    # NORMALIZED is historical recovery evidence, not an active generation.
    # Removing it from the partial uniqueness predicates permits a later relapse
    # to create a new incident generation.
    indexes = {item["name"] for item in sa.inspect(op.get_bind()).get_indexes("operational_incidents")}
    for name in (
        "uq_active_operational_incident",
        "uq_active_operational_incident_project_context",
    ):
        if name in indexes:
            op.drop_index(name, table_name="operational_incidents")
    op.create_index(
        "uq_active_operational_incident",
        "operational_incidents",
        ["rule_id", "context_key"],
        unique=True,
        postgresql_where=sa.text("status IN ('PENDING','OPEN','ACKNOWLEDGED')"),
    )
    op.create_index(
        "uq_active_operational_incident_project_context",
        "operational_incidents",
        ["aquaponics_system_id", "context_key"],
        unique=True,
        postgresql_where=sa.text("status IN ('PENDING','OPEN','ACKNOWLEDGED')"),
    )


def downgrade() -> None:
    raise RuntimeError("0053 is a retained-data forward migration; restore a verified backup for rollback.")
