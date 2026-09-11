"""Finish retained actuator feedback history migration and retire pseudo-Sensors.

Revision ID: 0061
Revises: 0060
"""

from alembic import op
import sqlalchemy as sa


revision = "0061"
down_revision = "0060"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    bind.execute(sa.text("""
        WITH voltage AS (
            SELECT b.actuator_id, tr.id, tr.value, tr.recorded_at, tr.received_at,
                   floor(extract(epoch FROM tr.recorded_at) / 5)::bigint AS bucket,
                   row_number() OVER (
                     PARTITION BY b.actuator_id, floor(extract(epoch FROM tr.recorded_at) / 5)
                     ORDER BY tr.recorded_at, tr.id
                   ) AS sequence
            FROM legacy_actuator_feedback_bindings b
            JOIN telemetry_readings tr ON tr.sensor_id = b.sensor_id
            WHERE b.feedback_role = 'SUPPLY_VOLTAGE'
        ), current AS (
            SELECT b.actuator_id, tr.id, tr.value, tr.recorded_at, tr.received_at,
                   floor(extract(epoch FROM tr.recorded_at) / 5)::bigint AS bucket,
                   row_number() OVER (
                     PARTITION BY b.actuator_id, floor(extract(epoch FROM tr.recorded_at) / 5)
                     ORDER BY tr.recorded_at, tr.id
                   ) AS sequence
            FROM legacy_actuator_feedback_bindings b
            JOIN telemetry_readings tr ON tr.sensor_id = b.sensor_id
            WHERE b.feedback_role = 'RUNNING_CURRENT'
        ), rows AS (
            SELECT COALESCE(v.actuator_id, c.actuator_id) AS actuator_id,
                   v.value AS voltage_v, c.value AS current_a,
                   GREATEST(v.recorded_at, c.recorded_at) AS recorded_at,
                   GREATEST(v.received_at, c.received_at) AS received_at,
                   CASE WHEN v.id IS NOT NULL AND c.id IS NOT NULL THEN 'pair:' || v.id::text || ':' || c.id::text
                        WHEN v.id IS NOT NULL THEN 'voltage:' || v.id::text
                        ELSE 'current:' || c.id::text END AS legacy_source_key
            FROM voltage v
            FULL OUTER JOIN current c
              ON c.actuator_id = v.actuator_id AND c.bucket = v.bucket AND c.sequence = v.sequence
        )
        INSERT INTO actuator_readings (
            actuator_id, voltage_v, current_a, recorded_at, received_at, quality, legacy_source_key
        )
        SELECT actuator_id, voltage_v, current_a, recorded_at, received_at, 'UNVALIDATED', legacy_source_key
        FROM rows
        ON CONFLICT (legacy_source_key) DO NOTHING
    """))

    missing = bind.scalar(sa.text("""
        WITH copied_ids AS (
            SELECT actuator_id, split_part(legacy_source_key, ':', 2)::bigint AS source_id
            FROM actuator_readings
            WHERE legacy_source_key LIKE 'voltage:%' OR legacy_source_key LIKE 'current:%'
            UNION ALL
            SELECT actuator_id, split_part(legacy_source_key, ':', 2)::bigint
            FROM actuator_readings WHERE legacy_source_key LIKE 'pair:%'
            UNION ALL
            SELECT actuator_id, split_part(legacy_source_key, ':', 3)::bigint
            FROM actuator_readings WHERE legacy_source_key LIKE 'pair:%'
        )
        SELECT count(*)
        FROM legacy_actuator_feedback_bindings b
        JOIN telemetry_readings tr ON tr.sensor_id = b.sensor_id
        LEFT JOIN copied_ids c ON c.actuator_id = b.actuator_id AND c.source_id = tr.id
        WHERE c.source_id IS NULL
    """))
    if missing:
        raise RuntimeError(f"Refusing to retire actuator feedback Sensors: {missing} readings are not preserved")

    bind.execute(sa.text("""
        UPDATE sensors s
        SET is_enabled = false,
            status = 'DISABLED',
            disabled_at = COALESCE(disabled_at, now()),
            disabled_reason = COALESCE(disabled_reason, 'Retired after verified ActuatorReading migration'),
            is_deleted = true,
            deleted_at = COALESCE(deleted_at, now())
        FROM legacy_actuator_feedback_bindings b
        WHERE b.sensor_id = s.id
          AND s.device_id = (SELECT a.device_id FROM actuators a WHERE a.id = b.actuator_id)
    """))


def downgrade() -> None:
    raise RuntimeError("0061 retires migrated compatibility Sensors; restore a verified backup to roll back.")
