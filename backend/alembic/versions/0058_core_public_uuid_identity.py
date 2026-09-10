"""Add persistent UUIDv4 public identities to core entities.

Revision ID: 0058
Revises: 0057
"""

from uuid import uuid4

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0058"
down_revision = "0057"
branch_labels = None
depends_on = None

TABLES = ("users", "aquaponics_systems", "devices", "sensors", "actuators")


def upgrade() -> None:
    bind = op.get_bind()
    for table_name in TABLES:
        op.add_column(table_name, sa.Column("public_id", postgresql.UUID(as_uuid=True), nullable=True))
        table = sa.table(table_name, sa.column("id", sa.BigInteger()), sa.column("public_id", postgresql.UUID(as_uuid=True)))
        ids = bind.execute(sa.select(table.c.id).where(table.c.public_id.is_(None))).scalars().all()
        for internal_id in ids:
            bind.execute(table.update().where(table.c.id == internal_id).values(public_id=uuid4()))
        null_count = bind.scalar(sa.select(sa.func.count()).select_from(table).where(table.c.public_id.is_(None)))
        duplicate_count = bind.scalar(sa.select(sa.func.count()).select_from(
            sa.select(table.c.public_id).group_by(table.c.public_id).having(sa.func.count() > 1).subquery()
        ))
        if null_count or duplicate_count:
            raise RuntimeError(f"Invalid {table_name}.public_id backfill")
        op.create_index(f"ix_{table_name}_public_id", table_name, ["public_id"], unique=True)
        op.alter_column(table_name, "public_id", nullable=False)


def downgrade() -> None:
    for table_name in reversed(TABLES):
        op.drop_index(f"ix_{table_name}_public_id", table_name=table_name)
        op.drop_column(table_name, "public_id")
