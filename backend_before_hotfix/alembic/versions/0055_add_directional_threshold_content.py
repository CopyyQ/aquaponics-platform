"""Add user-owned directional Threshold Alert content.

Revision ID: 0055
Revises: 0054
"""

import sqlalchemy as sa

from alembic import op

revision = "0055"
down_revision = "0054"
branch_labels = None
depends_on = None


def upgrade() -> None:
    for column_name in (
        "below_consequence",
        "above_consequence",
        "below_recommended_actions",
        "above_recommended_actions",
    ):
        op.add_column(
            "threshold_alert_configs",
            sa.Column(column_name, sa.Text(), nullable=True),
        )


def downgrade() -> None:
    for column_name in reversed((
        "below_consequence",
        "above_consequence",
        "below_recommended_actions",
        "above_recommended_actions",
    )):
        op.drop_column("threshold_alert_configs", column_name)
