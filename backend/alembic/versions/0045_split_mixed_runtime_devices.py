"""Split retained mixed runtime devices into canonical sensor/actuator devices.

Revision ID: 0045
Revises: 0044
"""

from alembic import op
import sqlalchemy as sa

revision = "0045"
down_revision = "0044"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    rows = bind.execute(sa.text("""
        SELECT d.id, d.project_id, d.code, d.name, d.description, d.status,
               d.is_enabled, d.location, d.device_template_id
        FROM devices d
        WHERE EXISTS (SELECT 1 FROM sensors s WHERE s.device_id = d.id AND s.is_deleted = false)
          AND EXISTS (SELECT 1 FROM actuators a WHERE a.device_id = d.id AND a.is_deleted = false)
        ORDER BY d.id
    """)).mappings().all()
    for row in rows:
        new_code = f"{row['code']}-ACTUATORS"
        existing = bind.execute(sa.text("SELECT id FROM devices WHERE code = :code"), {"code": new_code}).scalar()
        if existing is None:
            existing = bind.execute(sa.text("""
                INSERT INTO devices
                    (code, name, description, status, is_enabled, is_deleted,
                     project_id, location, device_template_id, device_type,
                     is_legacy_mixed, is_legacy_energy_monitor)
                VALUES
                    (:code, :name, :description, :status, :is_enabled, false,
                     :project_id, :location, :device_template_id, 'ACTUATOR_DEVICE',
                     false, false)
                RETURNING id
            """), {**row, "code": new_code, "name": f"{row['name']} (Actuators)"}).scalar_one()
        bind.execute(sa.text("UPDATE actuators SET device_id = :new_id WHERE device_id = :old_id"), {"new_id": existing, "old_id": row["id"]})
        bind.execute(sa.text("UPDATE devices SET device_type = 'SENSOR_DEVICE', is_legacy_mixed = false WHERE id = :id"), {"id": row["id"]})


def downgrade() -> None:
    raise RuntimeError("0045 is a retained-data forward migration; restore a verified backup for rollback.")
