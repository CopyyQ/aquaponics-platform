"""Add publish and failure timestamps for actuator commands."""

from alembic import op
import sqlalchemy as sa

revision = "0012"
down_revision = "0011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    columns = {column["name"] for column in sa.inspect(bind).get_columns("actuator_commands")}
    for name, column in {
        "published_at": sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        "failed_at": sa.Column("failed_at", sa.DateTime(timezone=True), nullable=True),
        "timed_out_at": sa.Column("timed_out_at", sa.DateTime(timezone=True), nullable=True),
        "failure_reason": sa.Column("failure_reason", sa.Text(), nullable=True),
    }.items():
        if name not in columns:
            op.add_column("actuator_commands", column)


def downgrade() -> None:
    for name in ("failure_reason", "timed_out_at", "failed_at", "published_at"):
        op.drop_column("actuator_commands", name)
