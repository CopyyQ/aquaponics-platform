"""Separate device state ordering from backend status freshness.

Revision ID: 0034
Revises: 0033
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "0034"
down_revision = "0033"
branch_labels = None
depends_on = None


def upgrade() -> None:
    columns = {
        item["name"]
        for item in sa.inspect(op.get_bind()).get_columns("actuators")
    }
    if "reported_state_at" not in columns:
        op.add_column(
            "actuators",
            sa.Column("reported_state_at", sa.DateTime(timezone=True), nullable=True),
        )


def downgrade() -> None:
    columns = {
        item["name"]
        for item in sa.inspect(op.get_bind()).get_columns("actuators")
    }
    if "reported_state_at" in columns:
        op.drop_column("actuators", "reported_state_at")
