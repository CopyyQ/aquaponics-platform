from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import uuid4

import httpx
import pytest
from sqlalchemy import delete, select

from app.core.enums import ProjectStatus, UserRole
from app.core.security import create_access_token
from app.db.session import AsyncSessionLocal
from app.main import app
from app.models.audit_log import AuditLog
from app.models.device import Device
from app.models.device_template import DeviceTemplate, DeviceTemplateSensor
from app.models.project import Project
from app.models.sensor import Sensor, SensorModel
from app.models.telemetry import TelemetryReading
from app.models.user import User
from app.services.energy_monitor_service import (
    ENERGY_SENSOR_SPECS,
    EnergyTemplateValidationError,
    validate_energy_template,
)
from app.services.energy_monitor_read_service import counter_segment_delta


def _template(*, missing: str | None = None, kind: str = "ENERGY_MONITOR"):
    mappings = []
    for spec in ENERGY_SENSOR_SPECS:
        if spec.model_code == missing:
            continue
        mappings.append(
            SimpleNamespace(
                is_required=True,
                display_name=spec.name,
                sort_order=spec.sort_order,
                sensor_model=SimpleNamespace(
                    code=spec.model_code,
                    unit=spec.unit,
                    value_type="NUMBER",
                    measurement_semantics=spec.measurement_semantics,
                )
            )
        )
    return SimpleNamespace(
        device_kind=kind,
        sensor_mappings=mappings,
        actuator_mappings=[],
        nominal_output_voltage_v=12,
    )


def test_energy_template_accepts_exact_required_catalog() -> None:
    validate_energy_template(_template())
    assert [item.sensor_code for item in ENERGY_SENSOR_SPECS] == [
        "OUTPUT-VOLTAGE",
        "INPUT-VOLTAGE",
        "LOAD-CURRENT",
        "INPUT-CURRENT",
        "POWER",
        "ENERGY",
    ]
    assert [item.name for item in ENERGY_SENSOR_SPECS] == [
        "Điện áp đầu ra",
        "Điện áp đầu vào",
        "Dòng điện tiêu thụ",
        "Dòng điện đầu vào",
        "Công suất tiêu thụ",
        "Điện năng tiêu thụ",
    ]
    assert len(ENERGY_SENSOR_SPECS) == 6
    assert sum(item.measurement_semantics == "GAUGE" for item in ENERGY_SENSOR_SPECS) == 5
    assert sum(item.measurement_semantics == "COUNTER" for item in ENERGY_SENSOR_SPECS) == 1
    assert all(item.model_code != "OPERATING_HOURS_TOTAL_H" for item in ENERGY_SENSOR_SPECS)


def test_energy_template_reports_missing_model() -> None:
    with pytest.raises(EnergyTemplateValidationError) as captured:
        validate_energy_template(_template(missing="ENERGY_TOTAL_WH"))
    assert captured.value.detail["code"] == "ENERGY_TEMPLATE_INCOMPLETE"
    assert captured.value.detail["missing_sensor_models"] == ["ENERGY_TOTAL_WH"]


def test_generic_template_is_not_constrained_by_energy_catalog() -> None:
    validate_energy_template(_template(missing="POWER_W", kind="GENERIC"))


def test_counter_delta_sums_segments_after_reset() -> None:
    assert counter_segment_delta([12_500.0, 12_540.0, 10.0, 18.0]) == 58.0


def test_counter_delta_requires_a_baseline_and_never_returns_negative() -> None:
    assert counter_segment_delta([12_500.0]) is None
    assert counter_segment_delta([100.0, 3.0]) == 3.0


async def test_energy_runtime_materializes_and_exports_only_six_measurements() -> None:
    suffix = uuid4().hex[:8].upper()
    project_id: int | None = None
    device_id: int | None = None
    legacy_sensor_id: int | None = None
    legacy_reading_id: int | None = None
    async with AsyncSessionLocal() as db:
        admin = await db.scalar(
            select(User).where(User.system_role == UserRole.ADMIN, User.is_deleted.is_(False))
        )
        owner = await db.scalar(
            select(User).where(User.system_role == UserRole.OWNER, User.is_deleted.is_(False))
        )
        template = await db.scalar(
            select(DeviceTemplate).where(DeviceTemplate.code == "ENERGY_MONITOR_12V")
        )
        assert admin is not None
        assert owner is not None
        assert template is not None
        mappings = list(
            (
                await db.execute(
                    select(DeviceTemplateSensor, SensorModel)
                    .join(SensorModel, SensorModel.id == DeviceTemplateSensor.sensor_model_id)
                    .where(DeviceTemplateSensor.device_template_id == template.id)
                    .order_by(DeviceTemplateSensor.sort_order)
                )
            ).all()
        )
        assert [model.code for _, model in mappings] == [item.model_code for item in ENERGY_SENSOR_SPECS]
        assert all(mapping.is_required for mapping, _ in mappings)
        project = Project(
            owner_user_id=owner.id,
            code=f"ENERGY-SIX-{suffix}",
            name=f"Energy six regression {suffix}",
            status=ProjectStatus.ACTIVE,
        )
        db.add(project)
        await db.commit()
        project_id = project.id
        template_id = template.id
        token = create_access_token(
            str(admin.id),
            {"role": admin.system_role.value, "token_version": admin.token_version},
        )
        headers = {"Authorization": f"Bearer {token}"}

    try:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            created = await client.post(
                f"/api/v1/projects/{project_id}/devices/from-template",
                json={
                    "device_template_id": template_id,
                    "code": f"ENERGY-SIX-{suffix}",
                    "name": "Thiết bị giám sát năng lượng 12V",
                },
                headers=headers,
            )
            assert created.status_code == 201, created.text
            device_id = created.json()["id"]

        async with AsyncSessionLocal() as db:
            active_rows = list(
                (
                    await db.execute(
                        select(Sensor, SensorModel)
                        .join(SensorModel, SensorModel.id == Sensor.sensor_model_id)
                        .where(Sensor.device_id == device_id, Sensor.is_enabled.is_(True))
                        .order_by(Sensor.id)
                    )
                ).all()
            )
            active_by_model = {model.code: sensor for sensor, model in active_rows}
            assert list(active_by_model) == [item.model_code for item in ENERGY_SENSOR_SPECS]
            for spec in ENERGY_SENSOR_SPECS:
                sensor = active_by_model[spec.model_code]
                assert (sensor.code, sensor.name) == (spec.sensor_code, spec.name)

            legacy_model = await db.scalar(
                select(SensorModel).where(SensorModel.code == "OPERATING_HOURS_TOTAL_H")
            )
            assert legacy_model is not None
            assert legacy_model.is_active is False
            legacy = Sensor(
                device_id=device_id,
                sensor_model_id=legacy_model.id,
                code="OPERATING-HOURS",
                name="Legacy operating hours",
                is_enabled=False,
                disabled_at=datetime.now(UTC),
                disabled_reason="Regression fixture for preserved historical telemetry",
            )
            db.add(legacy)
            await db.flush()
            reading = TelemetryReading(
                sensor_id=legacy.id,
                value=123.0,
                recorded_at=datetime.now(UTC),
                received_at=datetime.now(UTC),
            )
            db.add(reading)
            await db.commit()
            legacy_sensor_id = legacy.id
            legacy_reading_id = reading.id

        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            config_response = await client.get(
                f"/api/v1/projects/{project_id}/devices/{device_id}/mqtt-connection-config",
                headers=headers,
            )
            assert config_response.status_code == 200
            config = config_response.json()
            assert [item["sensor_model_code"] for item in config["sensors"]] == [
                item.model_code for item in ENERGY_SENSOR_SPECS
            ]
            assert [item["sensor_code"] for item in config["sensors"]] == [
                item.sensor_code for item in ENERGY_SENSOR_SPECS
            ]
            assert config["energy_monitoring"]["energy_sensor_code"] == "ENERGY"
            assert "operating" not in str(config).lower()

            overview_response = await client.get(
                f"/api/v1/projects/{project_id}/devices/{device_id}/energy-overview",
                headers=headers,
            )
            assert overview_response.status_code == 200
            overview = overview_response.json()
            assert list(overview["measurements"]) == [
                "output_voltage",
                "input_voltage",
                "load_current",
                "input_current",
                "power",
                "energy_total",
            ]
            assert overview["data_health"]["expected_measurements"] == 6

            scada_response = await client.get(
                f"/api/v1/projects/{project_id}/scada/runtime", headers=headers
            )
            assert scada_response.status_code == 200
            scada = scada_response.json()
            energy_runtime = next(
                item for item in scada["energy_monitor_runtime"] if item["device_id"] == device_id
            )
            assert energy_runtime["expected_measurements"] == 6
            assert "operating" not in str(energy_runtime).lower()
            assert legacy_sensor_id not in {item["id"] for item in scada["inventory"]["sensors"]}

        async with AsyncSessionLocal() as db:
            preserved = await db.get(TelemetryReading, legacy_reading_id)
            assert preserved is not None
            assert preserved.value == 123.0
    finally:
        async with AsyncSessionLocal() as db:
            if legacy_reading_id is not None:
                await db.execute(delete(TelemetryReading).where(TelemetryReading.id == legacy_reading_id))
            if device_id is not None:
                await db.execute(
                    delete(AuditLog).where(
                        AuditLog.entity_type == "DEVICE", AuditLog.entity_id == device_id
                    )
                )
                await db.execute(delete(Sensor).where(Sensor.device_id == device_id))
                await db.execute(delete(Device).where(Device.id == device_id))
            if project_id is not None:
                await db.execute(delete(Project).where(Project.id == project_id))
            await db.commit()
