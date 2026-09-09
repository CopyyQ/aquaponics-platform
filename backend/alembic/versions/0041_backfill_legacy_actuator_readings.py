"""Backfill direct Actuator readings from legacy feedback telemetry.

Revision ID: 0041
Revises: 0040

The migration pairs samples in deterministic five-second buckets. Each legacy
source reading is represented exactly once: paired values produce one row with
both values; remaining voltage/current readings produce one-sided rows.
`legacy_source_key` makes re-entry idempotent and exposes provenance for the
reconciliation report. It never deletes or updates legacy telemetry.
"""

from alembic import op
import sqlalchemy as sa

revision = "0041"
down_revision = "0040"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    # Pair within five-second buckets and rank by timestamp/ID. This is a
    # deterministic one-to-one strategy that scales over retained telemetry;
    # a source row has exactly one bucket/rank and can never be copied twice.
    bind.execute(sa.text("""
        WITH voltage AS (
            SELECT b.actuator_id, tr.id, tr.value, tr.recorded_at, tr.received_at,
                   floor(extract(epoch FROM tr.recorded_at) / 5)::bigint AS bucket,
                   row_number() OVER (
                     PARTITION BY b.actuator_id, floor(extract(epoch FROM tr.recorded_at) / 5)
                     ORDER BY tr.recorded_at, tr.id
                   ) AS sequence
            FROM actuator_feedback_bindings b
            JOIN telemetry_readings tr ON tr.sensor_id = b.sensor_id
            WHERE b.feedback_role = 'SUPPLY_VOLTAGE'
        ), current AS (
            SELECT b.actuator_id, tr.id, tr.value, tr.recorded_at, tr.received_at,
                   floor(extract(epoch FROM tr.recorded_at) / 5)::bigint AS bucket,
                   row_number() OVER (
                     PARTITION BY b.actuator_id, floor(extract(epoch FROM tr.recorded_at) / 5)
                     ORDER BY tr.recorded_at, tr.id
                   ) AS sequence
            FROM actuator_feedback_bindings b
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
    # A single snapshot must be internally coherent. The latest electrical
    # row determines values; its stored received time is the trusted freshness.
    bind.execute(sa.text("""
        WITH latest AS (
            SELECT DISTINCT ON (actuator_id)
                actuator_id, voltage_v, current_a, recorded_at, received_at
            FROM actuator_readings
            ORDER BY actuator_id, recorded_at DESC, id DESC
        )
        UPDATE actuators a
        SET voltage_v = latest.voltage_v,
            current_a = latest.current_a,
            electrical_recorded_at = latest.recorded_at,
            electrical_received_at = latest.received_at
        FROM latest
        WHERE latest.actuator_id = a.id
    """))


def downgrade() -> None:
    raise RuntimeError("0041 preserves historical migration provenance. Restore the verified backup if required.")
