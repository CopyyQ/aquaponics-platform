"""Add default notes to actuator template mappings."""

from alembic import op
import sqlalchemy as sa

revision = "0013"
down_revision = "0012"
branch_labels = None
depends_on = None


def upgrade() -> None:
    columns = {column["name"] for column in sa.inspect(op.get_bind()).get_columns("device_template_actuators")}
    if "default_notes" not in columns:
        op.add_column("device_template_actuators", sa.Column("default_notes", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("device_template_actuators", "default_notes")
