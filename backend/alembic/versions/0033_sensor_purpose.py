"""Classify generated actuator-feedback sensors without changing telemetry ownership.

Revision ID: 0033
Revises: 0032
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0033"
down_revision = "0032"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {item["name"] for item in inspector.get_columns("sensors")}
    if "purpose" not in columns:
        sensor_purpose = sa.Enum("GENERAL", "ACTUATOR_FEEDBACK", name="sensor_purpose")
        sensor_purpose.create(bind, checkfirst=True)
        op.add_column("sensors", sa.Column("purpose", sensor_purpose, nullable=False, server_default="GENERAL"))
    inspector = sa.inspect(bind)
    indexes = {item["name"] for item in inspector.get_indexes("sensors")}
    if "ix_sensors_purpose" not in indexes:
        op.create_index("ix_sensors_purpose", "sensors", ["purpose"])


def downgrade() -> None:
    indexes = {item["name"] for item in sa.inspect(op.get_bind()).get_indexes("sensors")}
    if "ix_sensors_purpose" in indexes:
        op.drop_index("ix_sensors_purpose", table_name="sensors")
