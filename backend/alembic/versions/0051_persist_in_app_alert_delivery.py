"""Persist in-app alert delivery setting.

Revision ID: 0051
Revises: 0050
"""
from alembic import op
import sqlalchemy as sa

revision = "0051"
down_revision = "0050"
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.add_column("project_notification_settings", sa.Column("in_app_enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")))

def downgrade() -> None:
    op.drop_column("project_notification_settings", "in_app_enabled")
