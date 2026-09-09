"""Make runtime Device type explicit and retain legacy classification markers.

Revision ID: 0037
Revises: 0036
"""

from alembic import op
import sqlalchemy as sa

revision = "0037"
down_revision = "0036"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    template_checks = {item["name"] for item in inspector.get_check_constraints("device_templates")}
    if "ck_device_templates_device_kind_allowed" in template_checks:
        op.drop_constraint("device_kind_allowed", "device_templates", type_="check")
    template_columns = {item["name"] for item in inspector.get_columns("device_templates")}
    if "device_kind" in template_columns and "legacy_device_kind" not in template_columns:
        op.alter_column("device_templates", "device_kind", new_column_name="legacy_device_kind")
    if "device_type" not in template_columns:
        op.add_column("device_templates", sa.Column("device_type", sa.String(40), nullable=True))
    if "is_legacy_mixed" not in template_columns:
        op.add_column("device_templates", sa.Column("is_legacy_mixed", sa.Boolean(), nullable=False, server_default=sa.false()))
    if "is_legacy_energy_monitor" not in template_columns:
        op.add_column("device_templates", sa.Column("is_legacy_energy_monitor", sa.Boolean(), nullable=False, server_default=sa.false()))

    bind.execute(sa.text("""
        UPDATE device_templates dt
        SET device_type = CASE
            WHEN EXISTS (SELECT 1 FROM device_template_actuators a WHERE a.device_template_id = dt.id)
                 THEN 'ACTUATOR_DEVICE'
            ELSE 'SENSOR_DEVICE'
        END,
        is_legacy_mixed = EXISTS (
            SELECT 1 FROM device_template_sensors s WHERE s.device_template_id = dt.id
        ) AND EXISTS (
            SELECT 1 FROM device_template_actuators a WHERE a.device_template_id = dt.id
        ),
        is_legacy_energy_monitor = COALESCE(legacy_device_kind = 'ENERGY_MONITOR', false)
        WHERE device_type IS NULL
    """))
    op.alter_column("device_templates", "device_type", nullable=False)
    template_checks = {item["name"] for item in sa.inspect(bind).get_check_constraints("device_templates")}
    if not ({"device_type_allowed", "ck_device_templates_device_type_allowed"} & template_checks):
        op.create_check_constraint(
            "device_type_allowed", "device_templates",
            "device_type IN ('SENSOR_DEVICE', 'ACTUATOR_DEVICE')",
        )

    inspector = sa.inspect(bind)
    device_columns = {item["name"] for item in inspector.get_columns("devices")}
    if "device_type" not in device_columns:
        op.add_column("devices", sa.Column("device_type", sa.String(40), nullable=True))
    if "is_legacy_mixed" not in device_columns:
        op.add_column("devices", sa.Column("is_legacy_mixed", sa.Boolean(), nullable=False, server_default=sa.false()))
    if "is_legacy_energy_monitor" not in device_columns:
        op.add_column("devices", sa.Column("is_legacy_energy_monitor", sa.Boolean(), nullable=False, server_default=sa.false()))
    bind.execute(sa.text("""
        UPDATE devices d
        SET device_type = CASE
            WHEN EXISTS (
                SELECT 1 FROM actuators a
                WHERE a.device_id = d.id AND a.is_deleted = false AND a.removed_at IS NULL
            ) THEN 'ACTUATOR_DEVICE'
            WHEN EXISTS (
                SELECT 1 FROM sensors s
                WHERE s.device_id = d.id AND s.is_deleted = false
            ) THEN 'SENSOR_DEVICE'
            WHEN dt.device_type IS NOT NULL THEN dt.device_type
            ELSE 'SENSOR_DEVICE'
        END,
        is_legacy_mixed = EXISTS (
            SELECT 1 FROM sensors s
            WHERE s.device_id = d.id AND s.is_deleted = false
        ) AND EXISTS (
            SELECT 1 FROM actuators a
            WHERE a.device_id = d.id AND a.is_deleted = false AND a.removed_at IS NULL
        ),
        is_legacy_energy_monitor = COALESCE(dt.is_legacy_energy_monitor, false)
        FROM device_templates dt
        WHERE d.device_template_id = dt.id AND d.device_type IS NULL
    """))
    bind.execute(sa.text("UPDATE devices SET device_type = 'SENSOR_DEVICE' WHERE device_type IS NULL"))
    op.alter_column("devices", "device_type", nullable=False)
    device_checks = {item["name"] for item in sa.inspect(bind).get_check_constraints("devices")}
    if not ({"device_type_allowed", "ck_devices_device_type_allowed"} & device_checks):
        op.create_check_constraint(
            "device_type_allowed", "devices",
            "device_type IN ('SENSOR_DEVICE', 'ACTUATOR_DEVICE')",
        )


def downgrade() -> None:
    raise RuntimeError(
        "0037 preserves a data classification decision. Restore the verified backup "
        "or use a forward migration; do not silently reintroduce legacy kinds."
    )
