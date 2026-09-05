"""Separate measurement normalization from manual Alert resolution."""

from alembic import op
import sqlalchemy as sa

revision = "0024"
down_revision = "0023"
branch_labels = None
depends_on = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    columns = {column["name"] for column in inspector.get_columns("sensor_alerts")}
    if "condition_active" not in columns:
        op.add_column(
            "sensor_alerts",
            sa.Column("condition_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        )
    if "normalized_at" not in columns:
        op.add_column("sensor_alerts", sa.Column("normalized_at", sa.DateTime(timezone=True), nullable=True))
    if "resolved_by_user_id" not in columns:
        op.add_column("sensor_alerts", sa.Column("resolved_by_user_id", sa.BigInteger(), nullable=True))
        op.create_foreign_key(
            "fk_sensor_alerts_resolved_by_user_id_users",
            "sensor_alerts",
            "users",
            ["resolved_by_user_id"],
            ["id"],
            ondelete="SET NULL",
        )
    if "resolution_note" not in columns:
        op.add_column("sensor_alerts", sa.Column("resolution_note", sa.Text(), nullable=True))
    op.execute("UPDATE sensor_alerts SET condition_active = false WHERE status = 'RESOLVED'")
    op.alter_column("sensor_alerts", "condition_active", server_default=None)


def downgrade() -> None:
    op.drop_column("sensor_alerts", "resolution_note")
    op.drop_constraint("fk_sensor_alerts_resolved_by_user_id_users", "sensor_alerts", type_="foreignkey")
    op.drop_column("sensor_alerts", "resolved_by_user_id")
    op.drop_column("sensor_alerts", "normalized_at")
    op.drop_column("sensor_alerts", "condition_active")

