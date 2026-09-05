"""Correct the canonical Energy Monitor to six measurements.

The operating-hours catalog row and historical runtime Sensor are preserved.
Existing Energy Monitor operating-hours Sensors are disabled so their Telemetry
remains queryable without participating in the active protocol or health model.
"""

from alembic import op
import sqlalchemy as sa


revision = "0021"
down_revision = "0020"
branch_labels = None
depends_on = None


ENERGY_MODELS = (
    ("OUTPUT_VOLTAGE_V", "OUTPUT-VOLTAGE", "Điện áp đầu ra", "V", "GAUGE", 1),
    ("INPUT_VOLTAGE_V", "INPUT-VOLTAGE", "Điện áp đầu vào", "V", "GAUGE", 2),
    ("LOAD_CURRENT_A", "LOAD-CURRENT", "Dòng điện tiêu thụ", "A", "GAUGE", 3),
    ("INPUT_CURRENT_A", "INPUT-CURRENT", "Dòng điện đầu vào", "A", "GAUGE", 4),
    ("POWER_W", "POWER", "Công suất tiêu thụ", "W", "GAUGE", 5),
    ("ENERGY_TOTAL_WH", "ENERGY", "Điện năng tiêu thụ", "Wh", "COUNTER", 6),
)


def upgrade() -> None:
    bind = op.get_bind()
    canonical_codes = tuple(item[0] for item in ENERGY_MODELS)

    bind.execute(
        sa.text(
            """
            UPDATE device_templates SET
                name = 'Thiết bị giám sát năng lượng 12V',
                description = 'Thiết bị đo sáu đại lượng năng lượng bắt buộc.',
                notes = 'ENERGY_TOTAL_WH là cumulative counter có xử lý reset theo đoạn.',
                device_kind = 'ENERGY_MONITOR', nominal_output_voltage_v = 12,
                updated_at = now()
            WHERE code = 'ENERGY_MONITOR_12V'
            """
        )
    )

    for model_code, sensor_code, name, unit, semantics, sort_order in ENERGY_MODELS:
        bind.execute(
            sa.text(
                """
                UPDATE sensor_models SET
                    name = :name, unit = :unit, value_type = 'NUMBER',
                    measurement_semantics = :semantics, updated_at = now()
                WHERE code = :model_code
                """
            ),
            {
                "model_code": model_code,
                "name": name,
                "unit": unit,
                "semantics": semantics,
            },
        )
        bind.execute(
            sa.text(
                """
                INSERT INTO device_template_sensors (
                    device_template_id, sensor_model_id, display_name,
                    sort_order, is_required, created_at, updated_at
                )
                SELECT dt.id, sm.id, :name, :sort_order, true, now(), now()
                FROM device_templates dt
                JOIN sensor_models sm ON sm.code = :model_code
                WHERE dt.code = 'ENERGY_MONITOR_12V'
                ON CONFLICT (device_template_id, sensor_model_id) DO UPDATE SET
                    display_name = EXCLUDED.display_name,
                    sort_order = EXCLUDED.sort_order,
                    is_required = true,
                    updated_at = now()
                """
            ),
            {"model_code": model_code, "name": name, "sort_order": sort_order},
        )

        conflicting_sensor = bind.scalar(
            sa.text(
                """
                SELECT s.id
                FROM sensors s
                JOIN sensor_models sm ON sm.id = s.sensor_model_id
                JOIN devices d ON d.id = s.device_id
                JOIN device_templates dt ON dt.id = d.device_template_id
                WHERE dt.device_kind = 'ENERGY_MONITOR'
                  AND sm.code = :model_code
                  AND s.code <> :sensor_code
                  AND EXISTS (
                      SELECT 1 FROM sensors conflict
                      WHERE conflict.device_id = s.device_id
                        AND conflict.code = :sensor_code
                        AND conflict.id <> s.id
                  )
                LIMIT 1
                """
            ),
            {"model_code": model_code, "sensor_code": sensor_code},
        )
        if conflicting_sensor is not None:
            raise RuntimeError(
                "Cannot canonicalize Energy Monitor Sensor code because a Device "
                f"already uses {sensor_code!r}; conflicting Sensor id={conflicting_sensor}."
            )
        bind.execute(
            sa.text(
                """
                UPDATE sensors s SET
                    code = :sensor_code, name = :name, updated_at = now()
                FROM sensor_models sm, devices d, device_templates dt
                WHERE s.sensor_model_id = sm.id
                  AND s.device_id = d.id
                  AND d.device_template_id = dt.id
                  AND dt.device_kind = 'ENERGY_MONITOR'
                  AND sm.code = :model_code
                  AND d.is_deleted = false
                """
            ),
            {
                "model_code": model_code,
                "sensor_code": sensor_code,
                "name": name,
            },
        )

    # Template mappings are catalog metadata; removing the legacy mapping does
    # not touch Sensor instances or Telemetry readings.
    bind.execute(
        sa.text(
            """
            DELETE FROM device_template_sensors dts
            USING device_templates dt, sensor_models sm
            WHERE dts.device_template_id = dt.id
              AND dts.sensor_model_id = sm.id
              AND dt.code = 'ENERGY_MONITOR_12V'
              AND sm.code NOT IN :canonical_codes
            """
        ).bindparams(sa.bindparam("canonical_codes", expanding=True)),
        {"canonical_codes": canonical_codes},
    )

    bind.execute(
        sa.text(
            """
            UPDATE sensor_models SET
                is_active = false, is_visible = false, updated_at = now()
            WHERE code = 'OPERATING_HOURS_TOTAL_H'
            """
        )
    )

    # Preserve the legacy Sensor row and every historical reading while
    # excluding it from active ingestion, config export, dashboards and SCADA.
    bind.execute(
        sa.text(
            """
            UPDATE sensors s SET
                is_enabled = false,
                disabled_at = COALESCE(s.disabled_at, now()),
                disabled_reason = COALESCE(
                    s.disabled_reason,
                    'Legacy operating-hours measurement removed from ENERGY_MONITOR_12V canonical contract.'
                ),
                warning_enabled = false,
                updated_at = now()
            FROM sensor_models sm, devices d, device_templates dt
            WHERE s.sensor_model_id = sm.id
              AND s.device_id = d.id
              AND d.device_template_id = dt.id
              AND dt.device_kind = 'ENERGY_MONITOR'
              AND sm.code = 'OPERATING_HOURS_TOTAL_H'
              AND d.is_deleted = false
            """
        )
    )


def downgrade() -> None:
    raise RuntimeError(
        "0021 is intentionally irreversible because re-enabling a legacy Sensor "
        "would be an operational decision. Restore a backup or use a forward migration."
    )
