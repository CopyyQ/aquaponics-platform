"""Complete actuator catalog fields and device-template mappings."""

from alembic import op
import sqlalchemy as sa

revision = "0011"
down_revision = "0010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    columns = {column["name"] for column in sa.inspect(bind).get_columns("actuator_models")}
    additions = {
        "description": sa.Column("description", sa.Text(), nullable=True),
        "data_type": sa.Column("data_type", sa.String(30), nullable=True),
        "default_state": sa.Column("default_state", sa.Boolean(), nullable=True),
        "is_deleted": sa.Column("is_deleted", sa.Boolean(), nullable=True),
        "deleted_at": sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    }
    for name, column in additions.items():
        if name not in columns:
            op.add_column("actuator_models", column)
    op.execute(sa.text("UPDATE actuator_models SET data_type = 'BOOLEAN' WHERE data_type IS NULL"))
    op.execute(sa.text("UPDATE actuator_models SET default_state = FALSE WHERE default_state IS NULL"))
    op.execute(sa.text("UPDATE actuator_models SET is_deleted = FALSE WHERE is_deleted IS NULL"))
    op.alter_column("actuator_models", "data_type", nullable=False, server_default="BOOLEAN")
    op.alter_column("actuator_models", "default_state", nullable=False, server_default=sa.false())
    op.alter_column("actuator_models", "is_deleted", nullable=False, server_default=sa.false())

    tables = set(sa.inspect(bind).get_table_names())
    if "device_template_actuators" not in tables:
        op.create_table(
            "device_template_actuators",
            sa.Column("id", sa.BigInteger(), sa.Identity(always=True), primary_key=True),
            sa.Column("device_template_id", sa.BigInteger(), nullable=False),
            sa.Column("actuator_model_id", sa.BigInteger(), nullable=False),
            sa.Column("default_name", sa.String(255), nullable=True),
            sa.Column("default_location", sa.String(255), nullable=True),
            sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("is_required", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.ForeignKeyConstraint(["device_template_id"], ["device_templates.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["actuator_model_id"], ["actuator_models.id"], ondelete="RESTRICT"),
            sa.UniqueConstraint("device_template_id", "actuator_model_id", name="uq_device_template_actuator_model"),
        )
        op.create_index("ix_device_template_actuators_template_id", "device_template_actuators", ["device_template_id"])


def downgrade() -> None:
    op.drop_index("ix_device_template_actuators_template_id", table_name="device_template_actuators")
    op.drop_table("device_template_actuators")
