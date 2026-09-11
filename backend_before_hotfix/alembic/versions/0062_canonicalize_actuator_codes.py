"""Canonicalize device-local actuator codes.

Revision ID: 0062
Revises: 0061
"""

from alembic import op
import sqlalchemy as sa


revision = "0062"
down_revision = "0061"
branch_labels = None
depends_on = None


_CANDIDATES = """
    SELECT
        actuator.id,
        actuator.device_id,
        substring(
            actuator.code
            FROM char_length(system.code || '-' || device.code || '-') + 1
        ) AS local_code
    FROM actuators AS actuator
    JOIN devices AS device ON device.id = actuator.device_id
    JOIN aquaponics_systems AS system
      ON system.id = device.aquaponics_system_id
    WHERE actuator.code LIKE system.code || '-' || device.code || '-%'
"""


def upgrade() -> None:
    bind = op.get_bind()
    collision = bind.execute(
        sa.text(
            f"""
            WITH candidates AS ({_CANDIDATES})
            SELECT candidate.device_id, candidate.local_code
            FROM candidates AS candidate
            LEFT JOIN actuators AS existing
              ON existing.device_id = candidate.device_id
             AND existing.code = candidate.local_code
             AND existing.id <> candidate.id
            GROUP BY candidate.device_id, candidate.local_code
            HAVING count(*) > 1 OR count(existing.id) > 0
            LIMIT 1
            """
        )
    ).first()
    if collision is not None:
        raise RuntimeError(
            "Cannot canonicalize actuator codes: collision for "
            f"device_id={collision.device_id}, code={collision.local_code}"
        )

    bind.execute(
        sa.text(
            f"""
            WITH candidates AS ({_CANDIDATES})
            UPDATE actuators AS actuator
            SET code = candidate.local_code
            FROM candidates AS candidate
            WHERE actuator.id = candidate.id
            """
        )
    )


def downgrade() -> None:
    # The former qualified value is not recoverable without reintroducing the
    # invalid identity format. Runtime identity and foreign keys stay intact.
    pass
