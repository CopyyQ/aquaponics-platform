"""Replace Device/Sensor visibility with an operational enabled lifecycle."""

from alembic import op
import sqlalchemy as sa

revision = "0009"
down_revision = "0008"
branch_labels = None
depends_on = None


def _upgrade_table(table: str) -> None:
    bind = op.get_bind()
    columns = {column["name"] for column in sa.inspect(bind).get_columns(table)}
    if "is_enabled" not in columns:
        if "is_visible" in columns:
            op.alter_column(table, "is_visible", new_column_name="is_enabled")
        else:
            op.add_column(table, sa.Column("is_enabled", sa.Boolean(), nullable=True))
            op.execute(sa.text(f"UPDATE {table} SET is_enabled = TRUE WHERE is_enabled IS NULL"))
            op.alter_column(table, "is_enabled", nullable=False)
    columns = {column["name"] for column in sa.inspect(bind).get_columns(table)}
    for name, column in {
        "disabled_at": sa.Column("disabled_at", sa.DateTime(timezone=True), nullable=True),
        "disabled_by_user_id": sa.Column("disabled_by_user_id", sa.BigInteger(), nullable=True),
        "disabled_reason": sa.Column("disabled_reason", sa.Text(), nullable=True),
    }.items():
        if name not in columns:
            op.add_column(table, column)
    fk_name = f"fk_{table}_disabled_by_user_id_users"
    if fk_name not in {fk["name"] for fk in sa.inspect(bind).get_foreign_keys(table)}:
        op.create_foreign_key(fk_name, table, "users", ["disabled_by_user_id"], ["id"], ondelete="SET NULL")


def upgrade() -> None:
    _upgrade_table("devices")
    _upgrade_table("sensors")


def _downgrade_table(table: str) -> None:
    op.drop_constraint(f"fk_{table}_disabled_by_user_id_users", table, type_="foreignkey")
    for name in ("disabled_reason", "disabled_by_user_id", "disabled_at"):
        op.drop_column(table, name)
    op.alter_column(table, "is_enabled", new_column_name="is_visible")


def downgrade() -> None:
    _downgrade_table("sensors")
    _downgrade_table("devices")
