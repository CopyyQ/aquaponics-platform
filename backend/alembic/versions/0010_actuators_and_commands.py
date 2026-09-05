"""Add Actuator resources and command history."""

from alembic import op
import sqlalchemy as sa

revision = "0010"
down_revision = "0009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())

    if "actuator_models" not in tables:
        op.create_table(
            "actuator_models",
            sa.Column("id", sa.BigInteger(), sa.Identity(always=True), primary_key=True),
            sa.Column("code", sa.String(length=80), nullable=False),
            sa.Column("name", sa.String(length=255), nullable=False),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.UniqueConstraint("code", name="uq_actuator_models_code"),
        )

    if "actuators" not in tables:
        op.create_table(
            "actuators",
            sa.Column("id", sa.BigInteger(), sa.Identity(always=True), primary_key=True),
            sa.Column("device_id", sa.BigInteger(), nullable=False),
            sa.Column("actuator_model_id", sa.BigInteger(), nullable=True),
            sa.Column("code", sa.String(length=80), nullable=False),
            sa.Column("name", sa.String(length=255), nullable=False),
            sa.Column("location", sa.String(length=255), nullable=True),
            sa.Column("notes", sa.Text(), nullable=True),
            sa.Column("is_enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("desired_state", sa.Boolean(), nullable=True),
            sa.Column("reported_state", sa.Boolean(), nullable=True),
            sa.Column("last_command_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("last_reported_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("disabled_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("disabled_by_user_id", sa.BigInteger(), nullable=True),
            sa.Column("disabled_reason", sa.Text(), nullable=True),
            sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.ForeignKeyConstraint(["device_id"], ["devices.id"], ondelete="RESTRICT"),
            sa.ForeignKeyConstraint(["actuator_model_id"], ["actuator_models.id"], ondelete="SET NULL"),
            sa.ForeignKeyConstraint(["disabled_by_user_id"], ["users.id"], ondelete="SET NULL"),
            sa.UniqueConstraint("device_id", "code", name="uq_actuator_device_code"),
        )
        op.create_index("ix_actuators_device_id", "actuators", ["device_id"])

    if "actuator_commands" not in tables:
        op.create_table(
            "actuator_commands",
            sa.Column("id", sa.BigInteger(), sa.Identity(always=True), primary_key=True),
            sa.Column("actuator_id", sa.BigInteger(), nullable=False),
            sa.Column("desired_state", sa.Boolean(), nullable=False),
            sa.Column("reported_state", sa.Boolean(), nullable=True),
            sa.Column("status", sa.String(length=30), nullable=False, server_default="PENDING"),
            sa.Column("requested_by_user_id", sa.BigInteger(), nullable=False),
            sa.Column("requested_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("acknowledged_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.ForeignKeyConstraint(["actuator_id"], ["actuators.id"], ondelete="RESTRICT"),
            sa.ForeignKeyConstraint(["requested_by_user_id"], ["users.id"], ondelete="RESTRICT"),
        )
        op.create_index("ix_actuator_commands_actuator_id", "actuator_commands", ["actuator_id"])


def downgrade() -> None:
    op.drop_index("ix_actuator_commands_actuator_id", table_name="actuator_commands")
    op.drop_table("actuator_commands")
    op.drop_index("ix_actuators_device_id", table_name="actuators")
    op.drop_table("actuators")
    op.drop_table("actuator_models")
