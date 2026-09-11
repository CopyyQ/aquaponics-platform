"""Add public, retireable AlertRule scenario identity and composite evaluator.

Revision ID: 0059
Revises: 0058
"""
from uuid import uuid4
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0059"
down_revision = "0058"
branch_labels = None
depends_on = None

OLD = "evaluator_type IN ('THRESHOLD','THRESHOLD_BANDS','RANGE_BANDS','DIGITAL_STATE','THRESHOLD_DURATION','BASELINE_DEVIATION','WINDOW_DURATION','TREND')"
NEW = "evaluator_type IN ('THRESHOLD','THRESHOLD_BANDS','RANGE_BANDS','DIGITAL_STATE','THRESHOLD_DURATION','BASELINE_DEVIATION','WINDOW_DURATION','TREND','MULTI_CONDITION')"

def upgrade() -> None:
    bind = op.get_bind()
    op.add_column("alert_rules", sa.Column("public_id", postgresql.UUID(as_uuid=True), nullable=True))
    table = sa.table("alert_rules", sa.column("id", sa.BigInteger()), sa.column("public_id", postgresql.UUID(as_uuid=True)))
    for internal_id in bind.execute(sa.select(table.c.id)).scalars():
        bind.execute(table.update().where(table.c.id == internal_id).values(public_id=uuid4()))
    if bind.scalar(sa.select(sa.func.count()).select_from(table).where(table.c.public_id.is_(None))):
        raise RuntimeError("Invalid alert_rules.public_id backfill")
    op.create_index("ix_alert_rules_public_id", "alert_rules", ["public_id"], unique=True)
    op.alter_column("alert_rules", "public_id", nullable=False)
    op.add_column("alert_rules", sa.Column("retired_at", sa.DateTime(timezone=True), nullable=True))
    op.drop_constraint("alert_rule_evaluator_type_allowed", "alert_rules", type_="check")
    op.create_check_constraint("alert_rule_evaluator_type_allowed", "alert_rules", NEW)

def downgrade() -> None:
    op.drop_constraint("alert_rule_evaluator_type_allowed", "alert_rules", type_="check")
    op.create_check_constraint("alert_rule_evaluator_type_allowed", "alert_rules", OLD)
    op.drop_column("alert_rules", "retired_at")
    op.drop_index("ix_alert_rules_public_id", table_name="alert_rules")
    op.drop_column("alert_rules", "public_id")
