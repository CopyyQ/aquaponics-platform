"""Add device template catalog and account lifecycle support.

Revision ID: 0005
Revises: 0004
"""

from alembic import op
import sqlalchemy as sa


revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())
    if bind.dialect.name == "postgresql":
        op.execute("ALTER TYPE user_status ADD VALUE IF NOT EXISTS 'LOCKED'")
    if "device_templates" not in tables:
        op.create_table(
            "device_templates",
            sa.Column("id", sa.BigInteger(), sa.Identity(always=True), primary_key=True),
            sa.Column("code", sa.String(80), nullable=False),
            sa.Column("name", sa.String(255), nullable=False),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("notes", sa.Text(), nullable=True),
            sa.Column("is_active", sa.Boolean(), server_default=sa.true(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("is_deleted", sa.Boolean(), server_default=sa.false(), nullable=False),
            sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
            sa.UniqueConstraint("code", name="uq_device_templates_code"),
        )
        op.create_index("ix_device_templates_code", "device_templates", ["code"])
        op.create_index("ix_device_templates_is_deleted", "device_templates", ["is_deleted"])
    inspector = sa.inspect(bind)
    sensor_model_columns = {column["name"] for column in inspector.get_columns("sensor_models")}
    for name, column in {
        "value_type": sa.Column("value_type", sa.String(30), server_default="NUMBER", nullable=False),
        "chart_type": sa.Column("chart_type", sa.String(30), server_default="LINE", nullable=False),
        "is_active": sa.Column("is_active", sa.Boolean(), server_default=sa.true(), nullable=False),
    }.items():
        if name not in sensor_model_columns:
            op.add_column("sensor_models", column)
    tables = set(sa.inspect(bind).get_table_names())
    if "device_template_sensors" not in tables:
        op.create_table(
            "device_template_sensors",
            sa.Column("id", sa.BigInteger(), sa.Identity(always=True), primary_key=True),
            sa.Column("device_template_id", sa.BigInteger(), sa.ForeignKey("device_templates.id", ondelete="CASCADE"), nullable=False),
            sa.Column("sensor_model_id", sa.BigInteger(), sa.ForeignKey("sensor_models.id", ondelete="RESTRICT"), nullable=False),
            sa.Column("display_name", sa.String(255), nullable=True),
            sa.Column("default_location", sa.String(255), nullable=True),
            sa.Column("default_lower_threshold", sa.Float(), nullable=True),
            sa.Column("default_upper_threshold", sa.Float(), nullable=True),
            sa.Column("sort_order", sa.Integer(), server_default="0", nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.UniqueConstraint("device_template_id", "sensor_model_id", name="uq_device_template_sensor_model"),
        )
        op.create_index("ix_device_template_sensors_device_template_id", "device_template_sensors", ["device_template_id"])
        op.create_index("ix_device_template_sensors_sensor_model_id", "device_template_sensors", ["sensor_model_id"])
    device_columns = {column["name"] for column in sa.inspect(bind).get_columns("devices")}
    if "device_template_id" not in device_columns:
        op.add_column("devices", sa.Column("device_template_id", sa.BigInteger(), nullable=True))
        op.create_foreign_key("fk_devices_device_template_id_device_templates", "devices", "device_templates", ["device_template_id"], ["id"], ondelete="SET NULL")
        op.create_index("ix_devices_device_template_id", "devices", ["device_template_id"])


def downgrade() -> None:
    op.drop_index("ix_devices_device_template_id", table_name="devices")
    op.drop_constraint("fk_devices_device_template_id_device_templates", "devices", type_="foreignkey")
    op.drop_column("devices", "device_template_id")
    op.drop_table("device_template_sensors")
    for column in ("is_active", "chart_type", "value_type"):
        op.drop_column("sensor_models", column)
    op.drop_table("device_templates")
    # PostgreSQL enum values are intentionally retained because removing an enum value is unsafe.
