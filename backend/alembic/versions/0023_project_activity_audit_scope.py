"""Scope existing audit logs to Projects for Project activity notifications."""

from alembic import op
import sqlalchemy as sa

revision = "0023"
down_revision = "0022"
branch_labels = None
depends_on = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    columns = {column["name"] for column in inspector.get_columns("audit_logs")}
    if "project_id" not in columns:
        op.add_column("audit_logs", sa.Column("project_id", sa.BigInteger(), nullable=True))
        op.create_foreign_key(
            "fk_audit_logs_project_id_projects",
            "audit_logs",
            "projects",
            ["project_id"],
            ["id"],
            ondelete="CASCADE",
        )
    indexes = {index["name"] for index in sa.inspect(op.get_bind()).get_indexes("audit_logs")}
    if "ix_audit_logs_project_id_created_at" not in indexes:
        op.create_index(
            "ix_audit_logs_project_id_created_at",
            "audit_logs",
            ["project_id", "created_at"],
        )


def downgrade() -> None:
    op.drop_index("ix_audit_logs_project_id_created_at", table_name="audit_logs")
    op.drop_constraint("fk_audit_logs_project_id_projects", "audit_logs", type_="foreignkey")
    op.drop_column("audit_logs", "project_id")
