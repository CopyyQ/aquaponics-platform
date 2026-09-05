"""Create and stamp a verified-empty disposable/fresh database at the current baseline."""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import inspect, text

from app import models  # noqa: F401 - registers every model with Base.metadata
from app.core.config import settings
from app.db.base import Base
from app.db.session import engine

ALLOWED_DATABASE_PREFIXES = ("aquaponics_codex_", "aquaponics_test_", "aquaponics_fresh_")
BASELINE_REVISION = "0021"
POWER_SENSOR_MODELS = (
    ("OUTPUT_VOLTAGE_V", "Điện áp đầu ra", "V", "GAUGE"),
    ("INPUT_VOLTAGE_V", "Điện áp đầu vào", "V", "GAUGE"),
    ("LOAD_CURRENT_A", "Dòng điện tiêu thụ", "A", "GAUGE"),
    ("INPUT_CURRENT_A", "Dòng điện đầu vào", "A", "GAUGE"),
    ("POWER_W", "Công suất tiêu thụ", "W", "GAUGE"),
    ("ENERGY_TOTAL_WH", "Điện năng tiêu thụ", "Wh", "COUNTER"),
)
ACTUATOR_MODELS = (
    ("FISH_TANK_PUMP", "Bơm hút bể cá", "Điều khiển bơm hút hoặc tuần hoàn nước tại bể cá.", 1),
    ("IRRIGATION_PUMP", "Bơm tưới", "Điều khiển bơm cấp nước cho hệ thống tưới.", 2),
    ("MIST_SYSTEM", "Phun sương", "Điều khiển hệ thống phun sương tạo ẩm môi trường.", 3),
    ("GROW_LIGHT", "Đèn chiếu sáng", "Điều khiển hệ thống đèn chiếu sáng cho khu vực trồng.", 4),
    ("ALARM_SIREN", "Còi cảnh báo", "Điều khiển còi cảnh báo khi hệ thống phát hiện sự cố.", 5),
)


async def bootstrap() -> None:
    async with engine.begin() as connection:
        database_name = await connection.scalar(text("SELECT current_database()"))
        if not isinstance(database_name, str) or not database_name.startswith(
            ALLOWED_DATABASE_PREFIXES
        ):
            raise RuntimeError(
                "Refusing fresh bootstrap outside an explicitly disposable database; "
                f"got {database_name!r}"
            )
        existing_tables = await connection.run_sync(
            lambda sync_connection: inspect(sync_connection).get_table_names()
        )
        if existing_tables:
            raise RuntimeError(
                "Refusing fresh bootstrap because database is not empty: "
                + ", ".join(sorted(existing_tables))
            )
        await connection.run_sync(Base.metadata.create_all)
        for code, name, unit, semantics in POWER_SENSOR_MODELS:
            await connection.execute(
                text(
                    """
                    INSERT INTO sensor_models (
                        code, name, unit, value_type, chart_type,
                        measurement_semantics, is_visible, is_active,
                        is_deleted, created_at, updated_at
                    ) VALUES (
                        :code, :name, :unit, 'NUMBER', 'LINE',
                        :semantics, true, true, false, now(), now()
                    )
                    """
                ),
                {"code": code, "name": name, "unit": unit, "semantics": semantics},
            )
        await connection.execute(
            text(
                """
                INSERT INTO device_templates (
                    code, name, description, notes, device_kind,
                    nominal_output_voltage_v, is_active, is_deleted,
                    created_at, updated_at
                ) VALUES (
                    'ENERGY_MONITOR_12V',
                    'Thiết bị giám sát năng lượng 12V',
                    'Thiết bị đo sáu đại lượng năng lượng bắt buộc.',
                    'ENERGY_TOTAL_WH là cumulative counter có xử lý reset theo đoạn.',
                    'ENERGY_MONITOR', 12, true, false, now(), now()
                )
                """
            )
        )
        for sort_order, (code, name, _, _) in enumerate(POWER_SENSOR_MODELS, start=1):
            await connection.execute(
                text(
                    """
                    INSERT INTO device_template_sensors (
                        device_template_id, sensor_model_id, display_name,
                        sort_order, is_required, created_at, updated_at
                    )
                    SELECT dt.id, sm.id, :name, :sort_order, true, now(), now()
                    FROM device_templates dt, sensor_models sm
                    WHERE dt.code = 'ENERGY_MONITOR_12V' AND sm.code = :code
                    """
                ),
                {"code": code, "name": name, "sort_order": sort_order},
            )
        for code, name, description, sort_order in ACTUATOR_MODELS:
            await connection.execute(
                text(
                    """
                    INSERT INTO actuator_models (
                        code, name, description, data_type, default_state,
                        is_active, sort_order, is_deleted, created_at, updated_at
                    ) VALUES (
                        :code, :name, :description, 'BOOLEAN', false,
                        true, :sort_order, false, now(), now()
                    )
                    """
                ),
                {
                    "code": code,
                    "name": name,
                    "description": description,
                    "sort_order": sort_order,
                },
            )
        await connection.execute(
            text("CREATE TABLE alembic_version (version_num VARCHAR(32) PRIMARY KEY)")
        )
        await connection.execute(
            text("INSERT INTO alembic_version (version_num) VALUES (:revision)"),
            {"revision": BASELINE_REVISION},
        )
    await engine.dispose()
    print(f"Fresh baseline created and stamped at {BASELINE_REVISION}: {settings.database_url}")


if __name__ == "__main__":
    asyncio.run(bootstrap())
