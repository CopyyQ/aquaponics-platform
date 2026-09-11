"""Canonicalize Energy Monitor counters and require seven measurements."""

from alembic import op
import sqlalchemy as sa


revision = "0020"
down_revision = "0019"
branch_labels = None
depends_on = None


ENERGY_MODELS = (
    ("INPUT_VOLTAGE_V", "Điện áp đầu vào", "V", "GAUGE", 1),
    ("OUTPUT_VOLTAGE_V", "Điện áp đầu ra", "V", "GAUGE", 2),
    ("INPUT_CURRENT_A", "Dòng điện đầu vào", "A", "GAUGE", 3),
    ("LOAD_CURRENT_A", "Dòng điện tải", "A", "GAUGE", 4),
    ("POWER_W", "Công suất tiêu thụ", "W", "GAUGE", 5),
    ("ENERGY_TOTAL_WH", "Điện năng tiêu thụ tích lũy", "Wh", "COUNTER", 6),
    ("OPERATING_HOURS_TOTAL_H", "Thời gian hoạt động tích lũy", "h", "COUNTER", 7),
)


def upgrade() -> None:
    bind = op.get_bind()
    columns = {item["name"] for item in sa.inspect(bind).get_columns("device_template_sensors")}
    if "is_required" not in columns:
        op.add_column(
            "device_template_sensors",
            sa.Column("is_required", sa.Boolean(), nullable=True),
        )
        bind.execute(sa.text("UPDATE device_template_sensors SET is_required = false"))
        op.alter_column(
            "device_template_sensors",
            "is_required",
            nullable=False,
            server_default=sa.false(),
        )

    # Rename the catalog row in place so existing Sensor and Telemetry foreign keys remain intact.
    legacy_id = bind.scalar(sa.text("SELECT id FROM sensor_models WHERE code = 'ENERGY_WH'"))
    canonical_id = bind.scalar(sa.text("SELECT id FROM sensor_models WHERE code = 'ENERGY_TOTAL_WH'"))
    if legacy_id is not None and canonical_id is None:
        bind.execute(
            sa.text(
                "UPDATE sensor_models SET code = 'ENERGY_TOTAL_WH', "
                "name = 'Điện năng tiêu thụ tích lũy', unit = 'Wh', "
                "value_type = 'NUMBER', measurement_semantics = 'COUNTER', updated_at = now() "
                "WHERE id = :legacy_id"
            ),
            {"legacy_id": legacy_id},
        )
    elif legacy_id is not None and canonical_id is not None:
        # Reconcile an accidental duplicate without deleting runtime readings.
        bind.execute(
            sa.text("UPDATE sensors SET sensor_model_id = :canonical_id WHERE sensor_model_id = :legacy_id"),
            {"canonical_id": canonical_id, "legacy_id": legacy_id},
        )
        bind.execute(
            sa.text(
                "DELETE FROM device_template_sensors legacy USING device_template_sensors canonical "
                "WHERE legacy.sensor_model_id = :legacy_id "
                "AND canonical.sensor_model_id = :canonical_id "
                "AND legacy.device_template_id = canonical.device_template_id"
            ),
            {"canonical_id": canonical_id, "legacy_id": legacy_id},
        )
        bind.execute(
            sa.text("UPDATE device_template_sensors SET sensor_model_id = :canonical_id WHERE sensor_model_id = :legacy_id"),
            {"canonical_id": canonical_id, "legacy_id": legacy_id},
        )
        bind.execute(sa.text("DELETE FROM sensor_models WHERE id = :legacy_id"), {"legacy_id": legacy_id})

    for code, name, unit, semantics, _ in ENERGY_MODELS:
        bind.execute(
            sa.text(
                """
                INSERT INTO sensor_models (
                    code, name, unit, value_type, chart_type, measurement_semantics,
                    is_visible, is_active, is_deleted, created_at, updated_at
                ) VALUES (
                    :code, :name, :unit, 'NUMBER', 'LINE', :semantics,
                    true, true, false, now(), now()
                )
                ON CONFLICT (code) DO UPDATE SET
                    name = EXCLUDED.name, unit = EXCLUDED.unit,
                    value_type = 'NUMBER', measurement_semantics = EXCLUDED.measurement_semantics,
                    is_active = true, is_deleted = false, deleted_at = NULL, updated_at = now()
                """
            ),
            {"code": code, "name": name, "unit": unit, "semantics": semantics},
        )

    bind.execute(
        sa.text(
            """
            UPDATE device_templates SET
                name = 'Thiết bị giám sát năng lượng 12V',
                device_kind = 'ENERGY_MONITOR', nominal_output_voltage_v = 12,
                is_active = true, is_deleted = false, deleted_at = NULL, updated_at = now()
            WHERE code = 'ENERGY_MONITOR_12V'
            """
        )
    )
    canonical_codes = tuple(item[0] for item in ENERGY_MODELS)
    bind.execute(
        sa.text(
            """
            DELETE FROM device_template_sensors dts
            USING device_templates dt, sensor_models sm
            WHERE dts.device_template_id = dt.id AND dts.sensor_model_id = sm.id
              AND dt.code = 'ENERGY_MONITOR_12V' AND sm.code NOT IN :canonical_codes
            """
        ).bindparams(sa.bindparam("canonical_codes", expanding=True)),
        {"canonical_codes": canonical_codes},
    )
    for code, name, _, _, sort_order in ENERGY_MODELS:
        bind.execute(
            sa.text(
                """
                INSERT INTO device_template_sensors (
                    device_template_id, sensor_model_id, display_name,
                    sort_order, is_required, created_at, updated_at
                )
                SELECT dt.id, sm.id, :name, :sort_order, true, now(), now()
                FROM device_templates dt JOIN sensor_models sm ON sm.code = :code
                WHERE dt.code = 'ENERGY_MONITOR_12V'
                ON CONFLICT (device_template_id, sensor_model_id) DO UPDATE SET
                    display_name = EXCLUDED.display_name, sort_order = EXCLUDED.sort_order,
                    is_required = true, updated_at = now()
                """
            ),
            {"code": code, "name": name, "sort_order": sort_order},
        )

    # Repair existing Energy Monitor Devices additively; no Sensor or Telemetry is removed.
    bind.execute(
        sa.text(
            """
            INSERT INTO sensors (
                device_id, sensor_model_id, code, name, status, is_enabled,
                warning_enabled, alert_delay_seconds, is_deleted, created_at, updated_at
            )
            SELECT d.id, sm.id, 'OPERATING-HOURS', 'Thời gian hoạt động tích lũy',
                   'WAITING_CONNECTION', true, true, 0, false, now(), now()
            FROM devices d
            JOIN device_templates dt ON dt.id = d.device_template_id
            JOIN sensor_models sm ON sm.code = 'OPERATING_HOURS_TOTAL_H'
            WHERE dt.device_kind = 'ENERGY_MONITOR' AND d.is_deleted = false
              AND NOT EXISTS (
                  SELECT 1 FROM sensors s
                  WHERE s.device_id = d.id AND s.sensor_model_id = sm.id AND s.is_deleted = false
              )
            """
        )
    )


def downgrade() -> None:
    raise RuntimeError(
        "0020 is intentionally irreversible because it preserves and canonicalizes "
        "runtime Sensor/Telemetry references. Use a forward migration or restore a backup."
    )
