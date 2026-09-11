"""Add Project public monitoring and Telegram recipient settings."""

from alembic import op
import sqlalchemy as sa

revision = "0022"
down_revision = "0021"
branch_labels = None
depends_on = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    expected = {
        "project_public_settings": {"id", "project_id", "enabled", "public_slug", "created_at", "updated_at"},
        "project_notification_settings": {"id", "project_id", "telegram_enabled", "notify_alert_opened", "notify_alert_resolved", "created_at", "updated_at"},
        "project_notification_recipients": {"id", "project_id", "name", "telegram_chat_id", "enabled", "created_at", "updated_at"},
    }
    existing = {table for table in expected if inspector.has_table(table)}
    if existing:
        if existing != set(expected):
            raise RuntimeError(f"Partial monitoring/notification schema found: {sorted(existing)}")
        for table, required_columns in expected.items():
            columns = {column["name"] for column in inspector.get_columns(table)}
            if not required_columns.issubset(columns):
                raise RuntimeError(f"Existing {table} is missing columns: {sorted(required_columns - columns)}")
        expected_uniques = {
            "project_public_settings": {"uq_project_public_settings_project_id", "uq_project_public_settings_public_slug"},
            "project_notification_settings": {"uq_project_notification_settings_project_id"},
            "project_notification_recipients": {"uq_project_notification_recipient_chat"},
        }
        for table, required_uniques in expected_uniques.items():
            uniques = {item["name"] for item in inspector.get_unique_constraints(table)}
            if not required_uniques.issubset(uniques):
                raise RuntimeError(f"Existing {table} is missing unique constraints: {sorted(required_uniques - uniques)}")
        return
    op.create_table(
        "project_public_settings",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=True), nullable=False),
        sa.Column("project_id", sa.BigInteger(), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("public_slug", sa.String(length=120), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], name="fk_project_public_settings_project_id_projects", ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name="pk_project_public_settings"),
        sa.UniqueConstraint("project_id", name="uq_project_public_settings_project_id"),
        sa.UniqueConstraint("public_slug", name="uq_project_public_settings_public_slug"),
    )
    op.create_index("ix_project_public_settings_project_id", "project_public_settings", ["project_id"])
    op.create_table(
        "project_notification_settings",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=True), nullable=False),
        sa.Column("project_id", sa.BigInteger(), nullable=False),
        sa.Column("telegram_enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("notify_alert_opened", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("notify_alert_resolved", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], name="fk_project_notification_settings_project_id_projects", ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name="pk_project_notification_settings"),
        sa.UniqueConstraint("project_id", name="uq_project_notification_settings_project_id"),
    )
    op.create_index("ix_project_notification_settings_project_id", "project_notification_settings", ["project_id"])
    op.create_table(
        "project_notification_recipients",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=True), nullable=False),
        sa.Column("project_id", sa.BigInteger(), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("telegram_chat_id", sa.String(length=64), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], name="fk_project_notification_recipients_project_id_projects", ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name="pk_project_notification_recipients"),
        sa.UniqueConstraint("project_id", "telegram_chat_id", name="uq_project_notification_recipient_chat"),
    )
    op.create_index("ix_project_notification_recipients_project_id", "project_notification_recipients", ["project_id"])


def downgrade() -> None:
    op.drop_index("ix_project_notification_recipients_project_id", table_name="project_notification_recipients")
    op.drop_table("project_notification_recipients")
    op.drop_index("ix_project_notification_settings_project_id", table_name="project_notification_settings")
    op.drop_table("project_notification_settings")
    op.drop_index("ix_project_public_settings_project_id", table_name="project_public_settings")
    op.drop_table("project_public_settings")
