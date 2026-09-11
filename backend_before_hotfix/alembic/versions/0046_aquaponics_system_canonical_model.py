"""Adopt Aquaponics Systems and allow mixed physical devices.

Revision ID: 0046
Revises: 0045
"""

from alembic import op
import sqlalchemy as sa

revision = "0046"
down_revision = "0045"
branch_labels = None
depends_on = None


def _column_exists(bind: sa.Connection, table: str, column: str) -> bool:
    return column in {item["name"] for item in sa.inspect(bind).get_columns(table)}


def upgrade() -> None:
    bind = op.get_bind()

    # The old classification guards must be removed before a retained
    # actuator is moved back onto its physical controller.
    op.execute("DROP TRIGGER IF EXISTS sensors_device_type_guard ON sensors")
    op.execute("DROP TRIGGER IF EXISTS actuators_device_type_guard ON actuators")
    op.execute("DROP FUNCTION IF EXISTS enforce_device_component_type()")

    # 0045 retained the original Sensor Device and made a deterministic
    # <code>-ACTUATORS clone. Rejoin the children before removing clones.
    pairs = bind.execute(sa.text("""
        SELECT sensor_device.id AS sensor_device_id, actuator_device.id AS actuator_device_id
        FROM devices sensor_device
        JOIN devices actuator_device
          ON actuator_device.code = sensor_device.code || '-ACTUATORS'
    """)).mappings().all()
    for pair in pairs:
        bind.execute(sa.text("UPDATE actuators SET device_id = :target WHERE device_id = :source"), {"target": pair["sensor_device_id"], "source": pair["actuator_device_id"]})
        bind.execute(sa.text("""
            UPDATE operational_incidents
            SET device_id = :target
            WHERE device_id = :source AND actuator_id IS NOT NULL
        """), {"target": pair["sensor_device_id"], "source": pair["actuator_device_id"]})
        bind.execute(sa.text("""
            UPDATE audit_logs SET entity_id = :target
            WHERE entity_type = 'DEVICE' AND entity_id = :source
        """), {"target": pair["sensor_device_id"], "source": pair["actuator_device_id"]})
        bind.execute(sa.text("DELETE FROM devices WHERE id = :source"), {"source": pair["actuator_device_id"]})

    for table, column in (
        ("devices", "device_type"),
        ("devices", "is_legacy_mixed"),
        ("devices", "is_legacy_energy_monitor"),
        ("device_templates", "device_type"),
        ("device_templates", "is_legacy_mixed"),
        ("device_templates", "is_legacy_energy_monitor"),
    ):
        if _column_exists(bind, table, column):
            op.drop_column(table, column)

    # Keep historical classifications in an explicit archive before removing
    # the runtime field. These values are not used by canonical APIs.
    if _column_exists(bind, "device_templates", "legacy_device_kind"):
        op.execute("""
            CREATE TABLE legacy_device_template_classifications AS
            SELECT id AS device_template_id, legacy_device_kind AS legacy_kind
            FROM device_templates
            WHERE legacy_device_kind IS NOT NULL
        """)
        op.drop_column("device_templates", "legacy_device_kind")

    if _column_exists(bind, "sensors", "purpose"):
        op.execute("""
            CREATE TABLE legacy_sensor_classifications AS
            SELECT id AS sensor_id, purpose AS legacy_purpose
            FROM sensors
            WHERE purpose IS NOT NULL
        """)
        op.drop_column("sensors", "purpose")

    op.rename_table("projects", "aquaponics_systems")
    for table in (
        "devices", "project_members", "audit_logs", "operational_incidents",
        "notification_outbox", "project_notification_recipients",
        "project_notification_risk_policies", "project_notification_settings",
        "project_public_settings", "scada_dashboards", "alert_rule_project_overrides",
    ):
        if _column_exists(bind, table, "project_id"):
            op.alter_column(table, "project_id", new_column_name="aquaponics_system_id")


def downgrade() -> None:
    raise RuntimeError("0046 is a retained-data forward migration; restore a verified backup for rollback.")
