"""Reconcile runtime schema and add first power-monitoring metadata."""

from alembic import op
import sqlalchemy as sa

revision = "0017"
down_revision = "0016"
branch_labels = None
depends_on = None

POWER_SENSOR_MODELS = (
    ("INPUT_VOLTAGE_V", "Điện áp đầu vào", "V", "GAUGE"),
    ("OUTPUT_VOLTAGE_V", "Điện áp đầu ra đo thực tế", "V", "GAUGE"),
    ("INPUT_CURRENT_A", "Dòng điện đầu vào", "A", "GAUGE"),
    ("LOAD_CURRENT_A", "Dòng điện tải", "A", "GAUGE"),
    ("POWER_W", "Công suất", "W", "GAUGE"),
    ("ENERGY_WH", "Điện năng tích lũy", "Wh", "COUNTER"),
)


def _index_names(inspector: sa.Inspector, table_name: str) -> set[str]:
    return {item["name"] for item in inspector.get_indexes(table_name)}


def _unique_names(inspector: sa.Inspector, table_name: str) -> set[str]:
    return {
        item["name"]
        for item in inspector.get_unique_constraints(table_name)
        if item.get("name")
    }


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    duplicate = bind.execute(
        sa.text(
            """
            SELECT device_id, code
            FROM actuators
            GROUP BY device_id, code
            HAVING COUNT(*) > 1
            LIMIT 1
            """
        )
    ).first()
    if duplicate is not None:
        raise RuntimeError(
            "Cannot enforce device-scoped actuator identity: duplicate "
            f"device_id={duplicate.device_id}, code={duplicate.code}"
        )

    unique_names = _unique_names(inspector, "actuators")
    if "uq_actuators_code" in unique_names:
        op.drop_constraint("uq_actuators_code", "actuators", type_="unique")
    inspector = sa.inspect(bind)
    if "uq_actuator_device_code" not in _unique_names(inspector, "actuators"):
        op.create_unique_constraint(
            "uq_actuator_device_code",
            "actuators",
            ["device_id", "code"],
        )

    telemetry_indexes = _index_names(sa.inspect(bind), "telemetry_readings")
    for redundant_index in (
        "ix_telemetry_sensor_recorded_at",
        "ix_telemetry_readings_sensor_recorded_at",
    ):
        if redundant_index in telemetry_indexes:
            op.drop_index(redundant_index, table_name="telemetry_readings")

    required_indexes = {
        "actuator_models": (
            ("ix_actuator_models_is_deleted", ["is_deleted"]),
        ),
        "actuators": (
            ("ix_actuators_is_deleted", ["is_deleted"]),
        ),
        "device_template_actuators": (
            ("ix_device_template_actuators_actuator_model_id", ["actuator_model_id"]),
        ),
    }
    for table_name, indexes in required_indexes.items():
        existing_indexes = _index_names(sa.inspect(bind), table_name)
        for index_name, columns in indexes:
            if index_name not in existing_indexes:
                op.create_index(index_name, table_name, columns)

    sensor_model_columns = {
        column["name"] for column in sa.inspect(bind).get_columns("sensor_models")
    }
    if "measurement_semantics" not in sensor_model_columns:
        op.add_column(
            "sensor_models",
            sa.Column(
                "measurement_semantics",
                sa.String(length=20),
                nullable=False,
                server_default="GAUGE",
            ),
        )
        op.create_check_constraint(
            "sensor_model_measurement_semantics",
            "sensor_models",
            "measurement_semantics IN ('GAUGE', 'COUNTER')",
        )

    template_columns = {
        column["name"] for column in sa.inspect(bind).get_columns("device_templates")
    }
    if "nominal_output_voltage_v" not in template_columns:
        op.add_column(
            "device_templates",
            sa.Column("nominal_output_voltage_v", sa.Float(), nullable=True),
        )
        op.create_check_constraint(
            "device_template_nominal_output_voltage_positive",
            "device_templates",
            "nominal_output_voltage_v IS NULL OR nominal_output_voltage_v > 0",
        )

    for code, name, unit, semantics in POWER_SENSOR_MODELS:
        bind.execute(
            sa.text(
                """
                INSERT INTO sensor_models (
                    code, name, unit, value_type, chart_type,
                    measurement_semantics, is_visible, is_active,
                    is_deleted, created_at, updated_at
                )
                VALUES (
                    :code, :name, :unit, 'NUMBER', 'LINE',
                    :semantics, true, true, false, now(), now()
                )
                ON CONFLICT (code) DO UPDATE
                SET measurement_semantics = EXCLUDED.measurement_semantics
                """
            ),
            {"code": code, "name": name, "unit": unit, "semantics": semantics},
        )

    # Historical revisions introduced database defaults inconsistently. The application
    # always supplies these values, so remove unconfirmed raw-SQL behavior and make the
    # upgraded schema equivalent to the versioned fresh baseline.
    defaults_to_remove = {
        "actuator_commands": ("status",),
        "actuator_models": (
            "data_type",
            "default_state",
            "is_active",
            "sort_order",
            "is_deleted",
        ),
        "actuators": ("is_enabled", "is_deleted"),
        "device_template_actuators": ("sort_order", "is_required"),
        "device_template_sensors": ("sort_order",),
        "device_templates": ("is_active", "is_deleted"),
        "projects": ("status", "is_deleted"),
        "sensor_models": (
            "value_type",
            "chart_type",
            "is_active",
            "measurement_semantics",
        ),
        "users": ("token_version",),
    }
    for table_name, column_names in defaults_to_remove.items():
        for column_name in column_names:
            op.alter_column(table_name, column_name, server_default=None)


def downgrade() -> None:
    raise RuntimeError(
        "0017 is intentionally irreversible because power catalog rows may be referenced "
        "and reconciliation removes redundant indexes. Restore from a verified backup instead."
    )
