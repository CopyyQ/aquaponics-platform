"""Retire parallel simple Sensor threshold rules.

Revision ID: 0054
Revises: 0053
"""

import sqlalchemy as sa

from alembic import op

revision = "0054"
down_revision = "0053"
branch_labels = None
depends_on = None

def upgrade() -> None:
    bind = op.get_bind()

    # Preserve rule history while disabling only the simple Sensor semantics
    # now owned by ThresholdAlertConfig. Advanced/window/trend rules remain.
    bind.execute(sa.text("""
        UPDATE alert_rule_profiles AS profile
        SET is_enabled = false, updated_at = now()
        FROM alert_rules AS rule
        WHERE profile.rule_id = rule.id
          AND rule.target_type = 'SENSOR'
          AND rule.evaluator_type IN (
              'THRESHOLD', 'THRESHOLD_BANDS', 'RANGE_BANDS', 'THRESHOLD_DURATION'
          )
    """))
    bind.execute(sa.text("""
        UPDATE alert_rules
        SET is_enabled = false, updated_at = now()
        WHERE target_type = 'SENSOR'
          AND evaluator_type IN (
              'THRESHOLD', 'THRESHOLD_BANDS', 'RANGE_BANDS', 'THRESHOLD_DURATION'
          )
    """))

    # Stop unsent reminders/events first, then close the retained legacy
    # incidents. No row is deleted and no synthetic resolution is enqueued.
    bind.execute(sa.text("""
        UPDATE notification_outbox AS outbox
        SET status = 'SKIPPED',
            processed_at = now(),
            skip_reason = 'LEGACY_SIMPLE_SENSOR_RULE_RETIRED'
        FROM operational_incidents AS incident
        JOIN alert_rules AS rule ON rule.id = incident.rule_id
        JOIN threshold_alert_configs AS config ON config.sensor_id = incident.sensor_id
        WHERE outbox.incident_id = incident.id
          AND outbox.status IN ('PENDING', 'RETRYING')
          AND incident.status IN ('PENDING', 'OPEN', 'ACKNOWLEDGED')
          AND rule.target_type = 'SENSOR'
          AND rule.evaluator_type IN (
              'THRESHOLD', 'THRESHOLD_BANDS', 'RANGE_BANDS', 'THRESHOLD_DURATION'
          )
    """))
    bind.execute(sa.text("""
        UPDATE operational_incidents AS incident
        SET status = 'RESOLVED',
            normalized_at = COALESCE(incident.normalized_at, now()),
            resolved_at = COALESCE(incident.resolved_at, now()),
            resolution_note = COALESCE(incident.resolution_note || E'\n', '')
                || 'Normalized by 0054: canonical ThresholdAlertConfig authority.',
            updated_at = now()
        FROM alert_rules AS rule,
             threshold_alert_configs AS config
        WHERE rule.id = incident.rule_id
          AND config.sensor_id = incident.sensor_id
          AND incident.status IN ('PENDING', 'OPEN', 'ACKNOWLEDGED')
          AND rule.target_type = 'SENSOR'
          AND rule.evaluator_type IN (
              'THRESHOLD', 'THRESHOLD_BANDS', 'RANGE_BANDS', 'THRESHOLD_DURATION'
          )
    """))


def downgrade() -> None:
    raise RuntimeError("0054 normalizes retained incidents and cannot be reversed safely; restore a verified backup.")
