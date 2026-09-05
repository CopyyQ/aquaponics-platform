from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.device_template import DeviceTemplate, DeviceTemplateActuator, DeviceTemplateSensor
from app.models.sensor_model import SensorModel

ENERGY_MONITOR_KIND = "ENERGY_MONITOR"
ENERGY_TEMPLATE_CODE = "ENERGY_MONITOR_12V"


@dataclass(frozen=True)
class EnergySensorSpec:
    model_code: str
    sensor_code: str
    name: str
    unit: str
    measurement_semantics: str
    sort_order: int


ENERGY_SENSOR_SPECS = (
    EnergySensorSpec("OUTPUT_VOLTAGE_V", "OUTPUT-VOLTAGE", "Điện áp đầu ra", "V", "GAUGE", 1),
    EnergySensorSpec("INPUT_VOLTAGE_V", "INPUT-VOLTAGE", "Điện áp đầu vào", "V", "GAUGE", 2),
    EnergySensorSpec("LOAD_CURRENT_A", "LOAD-CURRENT", "Dòng điện tiêu thụ", "A", "GAUGE", 3),
    EnergySensorSpec("INPUT_CURRENT_A", "INPUT-CURRENT", "Dòng điện đầu vào", "A", "GAUGE", 4),
    EnergySensorSpec("POWER_W", "POWER", "Công suất tiêu thụ", "W", "GAUGE", 5),
    EnergySensorSpec("ENERGY_TOTAL_WH", "ENERGY", "Điện năng tiêu thụ", "Wh", "COUNTER", 6),
)
ENERGY_SENSOR_SPEC_BY_MODEL = {item.model_code: item for item in ENERGY_SENSOR_SPECS}


class EnergyTemplateValidationError(ValueError):
    def __init__(self, *, missing: list[str], invalid: list[str]) -> None:
        self.detail = {
            "code": "ENERGY_TEMPLATE_INCOMPLETE",
            "message": "Mẫu thiết bị năng lượng chưa có đầy đủ cảm biến bắt buộc.",
            "missing_sensor_models": missing,
            "invalid_sensor_models": invalid,
        }
        super().__init__(self.detail["message"])


def validate_energy_template(template: DeviceTemplate) -> None:
    if template.device_kind != ENERGY_MONITOR_KIND:
        return
    mappings_by_code: dict[str, list[DeviceTemplateSensor]] = {}
    for mapping in template.sensor_mappings:
        mappings_by_code.setdefault(mapping.sensor_model.code, []).append(mapping)
    missing: list[str] = []
    invalid: list[str] = []
    for spec in ENERGY_SENSOR_SPECS:
        mappings = mappings_by_code.get(spec.model_code, [])
        if not mappings:
            missing.append(spec.model_code)
            continue
        model = mappings[0].sensor_model
        if (
            len(mappings) != 1
            or not mappings[0].is_required
            or model.unit != spec.unit
            or model.value_type != "NUMBER"
            or model.measurement_semantics != spec.measurement_semantics
            or mappings[0].display_name != spec.name
            or mappings[0].sort_order != spec.sort_order
        ):
            invalid.append(spec.model_code)
    if template.nominal_output_voltage_v is not None and template.nominal_output_voltage_v <= 0:
        invalid.append("nominal_output_voltage_v")
    if template.nominal_output_voltage_v is None:
        invalid.append("nominal_output_voltage_v")
    extra = sorted(set(mappings_by_code) - set(ENERGY_SENSOR_SPEC_BY_MODEL))
    invalid.extend(extra)
    if template.actuator_mappings:
        invalid.append("actuators")
    if missing or invalid:
        raise EnergyTemplateValidationError(missing=missing, invalid=invalid)


async def add_missing_energy_sensor_mappings(
    db: AsyncSession, template: DeviceTemplate
) -> list[DeviceTemplateSensor]:
    models = {
        model.code: model
        for model in (
            await db.scalars(
                select(SensorModel).where(
                    SensorModel.code.in_(tuple(ENERGY_SENSOR_SPEC_BY_MODEL)),
                    SensorModel.is_deleted.is_(False),
                )
            )
        ).all()
    }
    missing_catalog = sorted(set(ENERGY_SENSOR_SPEC_BY_MODEL) - set(models))
    if missing_catalog:
        raise EnergyTemplateValidationError(missing=missing_catalog, invalid=[])
    existing = {mapping.sensor_model.code for mapping in template.sensor_mappings}
    created: list[DeviceTemplateSensor] = []
    for spec in ENERGY_SENSOR_SPECS:
        if spec.model_code in existing:
            continue
        mapping = DeviceTemplateSensor(
            device_template_id=template.id,
            sensor_model_id=models[spec.model_code].id,
            display_name=spec.name,
            sort_order=spec.sort_order,
            is_required=True,
        )
        db.add(mapping)
        created.append(mapping)
    await db.flush()
    return created


async def reload_template(db: AsyncSession, template_id: int) -> DeviceTemplate | None:
    return await db.scalar(
        select(DeviceTemplate)
        .options(
            selectinload(DeviceTemplate.sensor_mappings).selectinload(
                DeviceTemplateSensor.sensor_model
            ),
            selectinload(DeviceTemplate.actuator_mappings).selectinload(
                DeviceTemplateActuator.actuator_model
            ),
        )
        .where(DeviceTemplate.id == template_id)
        .execution_options(populate_existing=True)
    )
