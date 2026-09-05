"""Persist Device connectivity and Project health notification state."""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "0025"
down_revision = "0024"
branch_labels = None
depends_on = None


def upgrade() -> None:
    connection = op.get_bind()
    inspector = sa.inspect(connection)
    device_columns = {column["name"] for column in inspector.get_columns("devices")}
    if "disconnected_at" not in device_columns:
        op.add_column(
            "devices",
            sa.Column("disconnected_at", sa.DateTime(timezone=True), nullable=True),
        )
    settings_columns = {
        column["name"]
        for column in inspector.get_columns("project_notification_settings")
    }
    columns = {
        "last_health_status": sa.Column(
            "last_health_status", sa.String(length=30), nullable=True
        ),
        "last_health_fingerprint": sa.Column(
            "last_health_fingerprint", sa.String(length=64), nullable=True
        ),
        "last_health_snapshot": sa.Column(
            "last_health_snapshot",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
        "last_health_evaluated_at": sa.Column(
            "last_health_evaluated_at", sa.DateTime(timezone=True), nullable=True
        ),
        "last_health_notified_at": sa.Column(
            "last_health_notified_at", sa.DateTime(timezone=True), nullable=True
        ),
    }
    for name, column in columns.items():
        if name not in settings_columns:
            op.add_column("project_notification_settings", column)


def downgrade() -> None:
    op.drop_column("project_notification_settings", "last_health_notified_at")
    op.drop_column("project_notification_settings", "last_health_evaluated_at")
    op.drop_column("project_notification_settings", "last_health_snapshot")
    op.drop_column("project_notification_settings", "last_health_fingerprint")
    op.drop_column("project_notification_settings", "last_health_status")
    op.drop_column("devices", "disconnected_at")
