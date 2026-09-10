"""Use one canonical code for DeviceTemplate Sensor mappings.

Revision ID: 0056
Revises: 0055
"""

import sqlalchemy as sa
from alembic import op

revision = "0056"
down_revision = "0055"
branch_labels = None
depends_on = None


def _columns(bind: sa.Connection) -> set[str]:
    return {column["name"] for column in sa.inspect(bind).get_columns("device_template_sensors")}


def _has_constraint(bind: sa.Connection, name: str) -> bool:
    return any(
        constraint["name"] == name
        for constraint in sa.inspect(bind).get_unique_constraints("device_template_sensors")
    )


def _ensure_unique_codes(bind: sa.Connection) -> None:
    duplicate = bind.execute(sa.text("""
        SELECT device_template_id, code
        FROM device_template_sensors
        GROUP BY device_template_id, code
        HAVING count(*) > 1
        LIMIT 1
    """)).first()
    if duplicate is not None:
        raise RuntimeError(
            "Cannot create uq_device_template_sensor_code while duplicate mapping codes exist "
            f"for template={duplicate.device_template_id}, code={duplicate.code}."
        )


def upgrade() -> None:
    bind = op.get_bind()
    columns = _columns(bind)
    has_slot = "slot_code" in columns
    has_code = "code" in columns

    if has_slot and not has_code:
        op.alter_column("device_template_sensors", "slot_code", new_column_name="code")
    elif not has_slot and not has_code:
        op.add_column("device_template_sensors", sa.Column("code", sa.String(80), nullable=True))
        bind.execute(sa.text("""
            UPDATE device_template_sensors AS mapping
            SET code = model.code
            FROM sensor_models AS model
            WHERE model.id = mapping.sensor_model_id
              AND mapping.code IS NULL
        """))
    elif has_slot:
        conflict = bind.execute(sa.text("""
            SELECT id
            FROM device_template_sensors
            WHERE code IS NOT NULL
              AND slot_code IS NOT NULL
              AND code <> slot_code
            LIMIT 1
        """)).first()
        if conflict is not None:
            raise RuntimeError(
                "Cannot remove slot_code because it conflicts with code on "
                f"device_template_sensors.id={conflict.id}."
            )
        bind.execute(sa.text("""
            UPDATE device_template_sensors
            SET code = COALESCE(code, slot_code)
            WHERE code IS NULL
        """))
        op.drop_column("device_template_sensors", "slot_code")

    missing = bind.execute(
        sa.text("SELECT id FROM device_template_sensors WHERE code IS NULL LIMIT 1")
    ).first()
    if missing is not None:
        raise RuntimeError(
            "Cannot make device_template_sensors.code required; "
            f"mapping id={missing.id} has no recoverable code."
        )
    op.alter_column("device_template_sensors", "code", existing_type=sa.String(80), nullable=False)

    if _has_constraint(bind, "uq_device_template_sensor_slot"):
        op.drop_constraint("uq_device_template_sensor_slot", "device_template_sensors", type_="unique")
    if not _has_constraint(bind, "uq_device_template_sensor_code"):
        _ensure_unique_codes(bind)
        op.create_unique_constraint(
            "uq_device_template_sensor_code",
            "device_template_sensors",
            ["device_template_id", "code"],
        )


def downgrade() -> None:
    bind = op.get_bind()
    if _has_constraint(bind, "uq_device_template_sensor_code"):
        op.drop_constraint("uq_device_template_sensor_code", "device_template_sensors", type_="unique")
    if "code" in _columns(bind):
        op.alter_column("device_template_sensors", "code", new_column_name="slot_code")
    if not _has_constraint(bind, "uq_device_template_sensor_slot"):
        op.create_unique_constraint(
            "uq_device_template_sensor_slot",
            "device_template_sensors",
            ["device_template_id", "slot_code"],
        )
