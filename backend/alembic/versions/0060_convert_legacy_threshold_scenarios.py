"""Convert representable legacy directional thresholds to scenarios.

Revision ID: 0060
Revises: 0059
"""
from alembic import op
from app.services.legacy_threshold_conversion import convert_legacy_threshold_configs

revision = "0060"
down_revision = "0059"
branch_labels = None
depends_on = None


def upgrade() -> None:
    convert_legacy_threshold_configs(op.get_bind())


def downgrade() -> None:
    # Converted rules may already own incident history. Preserve their identity.
    pass
