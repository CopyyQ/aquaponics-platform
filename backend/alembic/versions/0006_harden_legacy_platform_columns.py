"""Harden legacy installations for account lifecycle and template references.

Some installations were created from an older 0001/0002 schema where the
project migration returned early after detecting the tables.  This migration
is deliberately idempotent so those databases can be upgraded without
recreating tables or dropping existing telemetry.
"""

from alembic import op
import sqlalchemy as sa


revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


def _columns(bind, table: str) -> set[str]:
    return {column["name"] for column in sa.inspect(bind).get_columns(table)}


def _tables(bind) -> set[str]:
    return set(sa.inspect(bind).get_table_names())


def upgrade() -> None:
    bind = op.get_bind()
    tables = _tables(bind)

    if "users" in tables:
        columns = _columns(bind, "users")
        if "must_change_password" not in columns:
            op.add_column(
                "users",
                sa.Column("must_change_password", sa.Boolean(), server_default=sa.false(), nullable=False),
            )
        if "token_version" not in columns:
            op.add_column(
                "users",
                sa.Column("token_version", sa.Integer(), server_default="0", nullable=False),
            )
        if "last_login_at" not in columns:
            op.add_column("users", sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True))
        if "password_changed_at" not in columns:
            op.add_column("users", sa.Column("password_changed_at", sa.DateTime(timezone=True), nullable=True))

    if "devices" in tables and "device_templates" in tables:
        columns = _columns(bind, "devices")
        if "device_template_id" not in columns:
            op.add_column("devices", sa.Column("device_template_id", sa.BigInteger(), nullable=True))
            op.create_foreign_key(
                "fk_devices_device_template_id_device_templates",
                "devices",
                "device_templates",
                ["device_template_id"],
                ["id"],
                ondelete="SET NULL",
            )
            op.create_index("ix_devices_device_template_id", "devices", ["device_template_id"])

    if "telemetry_readings" in tables:
        indexes = {index["name"] for index in sa.inspect(bind).get_indexes("telemetry_readings")}
        if "ix_telemetry_readings_sensor_recorded_at" not in indexes:
            op.create_index(
                "ix_telemetry_readings_sensor_recorded_at",
                "telemetry_readings",
                ["sensor_id", "recorded_at"],
            )


def downgrade() -> None:
    # Keep this downgrade conservative: columns may have existed before this
    # migration and removing them would break running installations.
    pass
