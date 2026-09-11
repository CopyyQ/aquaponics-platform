"""Track repeated abnormal readings on one unresolved alert incident."""

import sqlalchemy as sa

from alembic import op

revision = "0026"
down_revision = "0025"
branch_labels = None
depends_on = None


def upgrade() -> None:
    columns = {
        column["name"]
        for column in sa.inspect(op.get_bind()).get_columns("sensor_alerts")
    }
    if "last_triggered_at" not in columns:
        op.add_column(
            "sensor_alerts",
            sa.Column("last_triggered_at", sa.DateTime(timezone=True), nullable=True),
        )
    if "occurrence_count" not in columns:
        op.add_column(
            "sensor_alerts",
            sa.Column(
                "occurrence_count", sa.Integer(), nullable=False, server_default="1"
            ),
        )
    op.execute(
        "UPDATE sensor_alerts SET last_triggered_at = started_at "
        "WHERE last_triggered_at IS NULL"
    )
    op.alter_column("sensor_alerts", "occurrence_count", server_default=None)


def downgrade() -> None:
    op.drop_column("sensor_alerts", "occurrence_count")
    op.drop_column("sensor_alerts", "last_triggered_at")
