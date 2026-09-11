"""Unify canonical threshold runtime defaults.

Revision ID: 0052
Revises: 0051

Repairs historical rows that had a threshold bound but no directional risk,
and materializes any explicit legacy Sensor threshold that is still missing
from the canonical threshold_alert_configs table.  Runtime code continues to
read threshold_alert_configs only.
"""

from alembic import op
import sqlalchemy as sa

revision = "0052"
down_revision = "0051"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Safety backfill for Sensors created after the original 0043 migration by
    # older provisioning paths.  Do not overwrite an existing canonical row.
    op.execute(sa.text("""
        INSERT INTO threshold_alert_configs (
          sensor_id, metric_type, enabled, lower_threshold, upper_threshold,
          below_risk_level, above_risk_level, below_message, above_message
        )
        SELECT id, 'SENSOR_VALUE', COALESCE(alerts_enabled, warning_enabled, true),
          lower_threshold, upper_threshold,
          below_risk_level, above_risk_level,
          below_threshold_message, above_threshold_message
        FROM sensors
        WHERE lower_threshold IS NOT NULL OR upper_threshold IS NOT NULL
           OR below_risk_level IS NOT NULL OR above_risk_level IS NOT NULL
           OR below_threshold_message IS NOT NULL OR above_threshold_message IS NOT NULL
        ON CONFLICT (sensor_id) DO NOTHING
    """))

    # A configured direction must have an explicit business risk; otherwise
    # the incident evaluator cannot create an incident/outbox notification.
    op.execute(sa.text("""
        UPDATE threshold_alert_configs
        SET below_risk_level = 'LOW', updated_at = now()
        WHERE lower_threshold IS NOT NULL AND below_risk_level IS NULL
    """))
    op.execute(sa.text("""
        UPDATE threshold_alert_configs
        SET above_risk_level = 'HIGH', updated_at = now()
        WHERE upper_threshold IS NOT NULL AND above_risk_level IS NULL
    """))

    # Older incident outbox rows predate the canonical system_id snapshot.
    # Backfill it so delivery history is correctly system-scoped.
    op.execute(sa.text("""
        UPDATE notification_outbox AS outbox
        SET aquaponics_system_id = incident.aquaponics_system_id
        FROM operational_incidents AS incident
        WHERE outbox.incident_id = incident.id
          AND outbox.aquaponics_system_id IS NULL
    """))


def downgrade() -> None:
    # Data repair is intentionally retained. Reverting LOW/HIGH to NULL would
    # recreate silent notification failures and cannot distinguish historical
    # NULLs from deliberate edits safely.
    pass
