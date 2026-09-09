"""Restore the enum storage used by the canonical User ORM model."""

from alembic import op
import sqlalchemy as sa


revision = "0050"
down_revision = "0049"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    enum_name = "user_system_role"
    enum_exists = bind.execute(
        sa.text("SELECT 1 FROM pg_type WHERE typname = :name"), {"name": enum_name}
    ).scalar()
    if not enum_exists:
        op.execute("CREATE TYPE user_system_role AS ENUM ('ADMIN', 'OWNER', 'TECHNICIAN', 'VIEWER')")
    op.execute(
        "ALTER TABLE users ALTER COLUMN system_role TYPE user_system_role "
        "USING system_role::text::user_system_role"
    )


def downgrade() -> None:
    raise RuntimeError("0050 restores the canonical enum storage; restore a verified backup to roll back.")
