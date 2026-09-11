"""Add explicit project disable lifecycle fields.

Revision ID: 0007
Revises: 0006
"""

from alembic import op
import sqlalchemy as sa


revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute("ALTER TYPE project_status ADD VALUE IF NOT EXISTS 'DISABLED'")
    columns = {column["name"] for column in sa.inspect(bind).get_columns("projects")}
    if "disabled_at" not in columns:
        op.add_column("projects", sa.Column("disabled_at", sa.DateTime(timezone=True), nullable=True))
    if "disabled_by_user_id" not in columns:
        op.add_column("projects", sa.Column("disabled_by_user_id", sa.BigInteger(), nullable=True))
        op.create_foreign_key(
            "fk_projects_disabled_by_user_id_users", "projects", "users",
            ["disabled_by_user_id"], ["id"], ondelete="SET NULL",
        )
        op.create_index("ix_projects_disabled_by_user_id", "projects", ["disabled_by_user_id"])
    if "disabled_reason" not in columns:
        op.add_column("projects", sa.Column("disabled_reason", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_index("ix_projects_disabled_by_user_id", table_name="projects")
    op.drop_constraint("fk_projects_disabled_by_user_id_users", "projects", type_="foreignkey")
    op.drop_column("projects", "disabled_reason")
    op.drop_column("projects", "disabled_by_user_id")
    op.drop_column("projects", "disabled_at")
    # Enum value is retained because removing PostgreSQL enum values is unsafe.
