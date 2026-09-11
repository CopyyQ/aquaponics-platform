"""Add confirmed actuator state transition history."""

from alembic import op
import sqlalchemy as sa

revision = "0016"
down_revision = "0015"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "actuator_state_history" not in inspector.get_table_names():
        op.create_table(
            "actuator_state_history",
            sa.Column("id", sa.BigInteger(), sa.Identity(always=True), nullable=False),
            sa.Column("actuator_id", sa.BigInteger(), nullable=False),
            sa.Column("state", sa.Boolean(), nullable=False),
            sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("source", sa.String(length=30), nullable=False),
            sa.Column("command_id", sa.BigInteger(), nullable=True),
            sa.ForeignKeyConstraint(
                ["actuator_id"],
                ["actuators.id"],
                name="fk_actuator_state_history_actuator_id_actuators",
                ondelete="CASCADE",
            ),
            sa.ForeignKeyConstraint(
                ["command_id"],
                ["actuator_commands.id"],
                name="fk_actuator_state_history_command_id_actuator_commands",
                ondelete="SET NULL",
            ),
            sa.PrimaryKeyConstraint("id", name="pk_actuator_state_history"),
        )
    indexes = {index["name"] for index in sa.inspect(bind).get_indexes("actuator_state_history")}
    if "ix_actuator_state_history_actuator_id" not in indexes:
        op.create_index("ix_actuator_state_history_actuator_id", "actuator_state_history", ["actuator_id"])
    if "ix_actuator_state_history_actuator_recorded" not in indexes:
        op.create_index("ix_actuator_state_history_actuator_recorded", "actuator_state_history", ["actuator_id", "recorded_at"])


def downgrade() -> None:
    op.drop_index(
        "ix_actuator_state_history_actuator_recorded",
        table_name="actuator_state_history",
    )
    op.drop_index(
        "ix_actuator_state_history_actuator_id",
        table_name="actuator_state_history",
    )
    op.drop_table("actuator_state_history")
