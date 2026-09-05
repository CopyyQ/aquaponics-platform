"""Persist account lifecycle metadata and soft-deleted status."""

from alembic import op
import sqlalchemy as sa

revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute("ALTER TYPE user_status ADD VALUE IF NOT EXISTS 'SOFT_DELETED'")
    columns = {column["name"] for column in sa.inspect(bind).get_columns("users")}
    additions = {
        "disabled_at": sa.Column("disabled_at", sa.DateTime(timezone=True), nullable=True),
        "disabled_by_user_id": sa.Column("disabled_by_user_id", sa.BigInteger(), nullable=True),
        "disabled_reason": sa.Column("disabled_reason", sa.Text(), nullable=True),
        "locked_at": sa.Column("locked_at", sa.DateTime(timezone=True), nullable=True),
        "locked_by_user_id": sa.Column("locked_by_user_id", sa.BigInteger(), nullable=True),
        "locked_reason": sa.Column("locked_reason", sa.Text(), nullable=True),
    }
    for name, column in additions.items():
        if name not in columns:
            op.add_column("users", column)
    inspector = sa.inspect(bind)
    fks = {fk["name"] for fk in inspector.get_foreign_keys("users")}
    if "fk_users_disabled_by_user_id_users" not in fks:
        op.create_foreign_key("fk_users_disabled_by_user_id_users", "users", "users", ["disabled_by_user_id"], ["id"], ondelete="SET NULL")
    if "fk_users_locked_by_user_id_users" not in fks:
        op.create_foreign_key("fk_users_locked_by_user_id_users", "users", "users", ["locked_by_user_id"], ["id"], ondelete="SET NULL")


def downgrade() -> None:
    op.drop_constraint("fk_users_locked_by_user_id_users", "users", type_="foreignkey")
    op.drop_constraint("fk_users_disabled_by_user_id_users", "users", type_="foreignkey")
    for name in ("locked_reason", "locked_by_user_id", "locked_at", "disabled_reason", "disabled_by_user_id", "disabled_at"):
        op.drop_column("users", name)
