"""Add explicit Energy Monitor template classification and catalog mapping."""

from alembic import op
import sqlalchemy as sa

revision = "0018"
down_revision = "0017"
branch_labels = None
depends_on = None

ENERGY_MODELS = (
    ("INPUT_VOLTAGE_V", "Điện áp đầu vào", "V", "GAUGE", 1),
    ("OUTPUT_VOLTAGE_V", "Điện áp đầu ra đo thực tế", "V", "GAUGE", 2),
    ("INPUT_CURRENT_A", "Dòng điện đầu vào", "A", "GAUGE", 3),
    ("LOAD_CURRENT_A", "Dòng điện tải", "A", "GAUGE", 4),
    ("POWER_W", "Công suất tiêu thụ", "W", "GAUGE", 5),
    ("ENERGY_WH", "Điện năng tích lũy", "Wh", "COUNTER", 6),
)


def _check_names(bind: sa.Connection, table_name: str) -> set[str]:
    return {
        item["name"]
        for item in sa.inspect(bind).get_check_constraints(table_name)
        if item.get("name")
    }


def upgrade() -> None:
    bind = op.get_bind()
    template_columns = {
        column["name"] for column in sa.inspect(bind).get_columns("device_templates")
    }
    if "device_kind" not in template_columns:
        op.add_column(
            "device_templates",
            sa.Column("device_kind", sa.String(length=40), nullable=True),
        )
        bind.execute(sa.text("UPDATE device_templates SET device_kind = 'GENERIC'"))
        op.alter_column(
            "device_templates",
            "device_kind",
            nullable=False,
            server_default="GENERIC",
        )
        op.create_check_constraint(
            "device_kind_allowed",
            "device_templates",
            "device_kind IN ('GENERIC', 'ENERGY_MONITOR')",
        )

    template_checks = _check_names(bind, "device_templates")
    legacy_voltage_check = (
        "ck_device_templates_device_template_nominal_output_volt_8dfc"
    )
    if legacy_voltage_check in template_checks:
        op.drop_constraint(
            op.f(legacy_voltage_check), "device_templates", type_="check"
        )
    if "ck_device_templates_nominal_voltage_positive" not in _check_names(
        bind, "device_templates"
    ):
        op.create_check_constraint(
            "nominal_voltage_positive",
            "device_templates",
            "nominal_output_voltage_v IS NULL OR nominal_output_voltage_v > 0",
        )

    sensor_checks = _check_names(bind, "sensor_models")
    legacy_semantics_check = (
        "ck_sensor_models_sensor_model_measurement_semantics"
    )
    if legacy_semantics_check in sensor_checks:
        op.drop_constraint(
            op.f(legacy_semantics_check), "sensor_models", type_="check"
        )
    if "ck_sensor_models_measurement_semantics_allowed" not in _check_names(
        bind, "sensor_models"
    ):
        op.create_check_constraint(
            "measurement_semantics_allowed",
            "sensor_models",
            "measurement_semantics IN ('GAUGE', 'COUNTER')",
        )
    bind.execute(
        sa.text(
            "UPDATE sensor_models SET measurement_semantics = 'GAUGE' "
            "WHERE measurement_semantics IS NULL"
        )
    )
    op.alter_column(
        "sensor_models",
        "measurement_semantics",
        nullable=False,
        server_default="GAUGE",
    )

    for code, name, unit, semantics, _ in ENERGY_MODELS:
        bind.execute(
            sa.text(
                """
                INSERT INTO sensor_models (
                    code, name, unit, value_type, chart_type,
                    measurement_semantics, is_visible, is_active,
                    is_deleted, created_at, updated_at
                ) VALUES (
                    :code, :name, :unit, 'NUMBER', 'LINE', :semantics,
                    true, true, false, now(), now()
                )
                ON CONFLICT (code) DO UPDATE SET
                    name = EXCLUDED.name,
                    unit = EXCLUDED.unit,
                    value_type = 'NUMBER',
                    measurement_semantics = EXCLUDED.measurement_semantics,
                    is_active = true,
                    is_deleted = false,
                    deleted_at = NULL,
                    updated_at = now()
                """
            ),
            {"code": code, "name": name, "unit": unit, "semantics": semantics},
        )

    bind.execute(
        sa.text(
            """
            INSERT INTO device_templates (
                code, name, description, notes, device_kind,
                nominal_output_voltage_v, is_active, is_deleted,
                created_at, updated_at
            ) VALUES (
                'ENERGY_MONITOR_12V',
                'Thiết bị giám sát năng lượng 12V',
                'Thiết bị đo sáu đại lượng điện, công suất và điện năng tích lũy.',
                'POWER_W được đo trực tiếp; ENERGY_WH là raw cumulative counter.',
                'ENERGY_MONITOR', 12, true, false, now(), now()
            )
            ON CONFLICT (code) DO UPDATE SET
                name = EXCLUDED.name,
                device_kind = 'ENERGY_MONITOR',
                nominal_output_voltage_v = 12,
                is_active = true,
                is_deleted = false,
                deleted_at = NULL,
                updated_at = now()
            """
        )
    )

    for code, name, _, _, sort_order in ENERGY_MODELS:
        bind.execute(
            sa.text(
                """
                INSERT INTO device_template_sensors (
                    device_template_id, sensor_model_id, display_name,
                    sort_order, created_at, updated_at
                )
                SELECT dt.id, sm.id, :display_name, :sort_order, now(), now()
                FROM device_templates dt
                JOIN sensor_models sm ON sm.code = :model_code
                WHERE dt.code = 'ENERGY_MONITOR_12V'
                ON CONFLICT (device_template_id, sensor_model_id) DO UPDATE SET
                    display_name = EXCLUDED.display_name,
                    sort_order = EXCLUDED.sort_order,
                    updated_at = now()
                """
            ),
            {"model_code": code, "display_name": name, "sort_order": sort_order},
        )


def downgrade() -> None:
    raise RuntimeError(
        "0018 is intentionally irreversible because the seeded catalog/template may "
        "already be referenced by runtime Devices and Sensors. Restore from a verified "
        "backup or use a forward migration."
    )
