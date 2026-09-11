"""Create direct electrical Actuator history with idempotent legacy provenance.

Revision ID: 0040
Revises: 0039
"""

from alembic import op
import sqlalchemy as sa

revision = "0040"
down_revision = "0039"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    if "actuator_readings" in sa.inspect(bind).get_table_names():
        return
    op.create_table(
        "actuator_readings",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=True), primary_key=True),
        sa.Column("actuator_id", sa.BigInteger(), sa.ForeignKey("actuators.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("voltage_v", sa.Float()),
        sa.Column("current_a", sa.Float()),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("quality", sa.String(20), nullable=False, server_default="UNVALIDATED"),
        sa.Column("legacy_source_key", sa.String(180), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("quality IN ('VALID', 'UNVALIDATED', 'INVALID')", name="quality_allowed"),
        sa.UniqueConstraint("legacy_source_key", name="uq_actuator_reading_legacy_source_key"),
    )
    op.create_index("ix_actuator_readings_actuator_recorded_desc", "actuator_readings", ["actuator_id", "recorded_at"])


def downgrade() -> None:
    raise RuntimeError("0040 contains retained electrical history. Restore the verified backup if rollback is required.")
