"""Allow the canonical outbox to deliver non-incident operational events.

Revision ID: 0044
Revises: 0043
"""

from alembic import op
import sqlalchemy as sa

revision = "0044"
down_revision = "0043"
branch_labels = None
depends_on = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    columns = {column["name"] for column in inspector.get_columns("notification_outbox")}
    if "project_id" not in columns:
        op.add_column("notification_outbox", sa.Column("project_id", sa.BigInteger(), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=True))
    if "source_type" not in columns:
        op.add_column("notification_outbox", sa.Column("source_type", sa.String(30), nullable=False, server_default="INCIDENT"))
    indexes = {index["name"] for index in inspector.get_indexes("notification_outbox")}
    if "ix_notification_outbox_project_id" not in indexes:
        op.create_index("ix_notification_outbox_project_id", "notification_outbox", ["project_id"])
    op.execute("UPDATE notification_outbox o SET project_id = i.project_id FROM operational_incidents i WHERE o.incident_id = i.id")
    outbox_incident = next(column for column in inspector.get_columns("notification_outbox") if column["name"] == "incident_id")
    delivery_incident = next(column for column in inspector.get_columns("notification_deliveries") if column["name"] == "incident_id")
    if not outbox_incident["nullable"]:
        op.alter_column("notification_outbox", "incident_id", existing_type=sa.BigInteger(), nullable=True)
    if not delivery_incident["nullable"]:
        op.alter_column("notification_deliveries", "incident_id", existing_type=sa.BigInteger(), nullable=True)


def downgrade() -> None:
    raise RuntimeError("0044 is a retained-data forward migration; restore a verified backup for rollback.")
