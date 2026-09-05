import asyncio

from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.core.enums import UserRole, UserStatus
from app.core.security import hash_password
from app.models.sensor import SensorModel
from app.models.device_template import DeviceTemplate, DeviceTemplateActuator, DeviceTemplateSensor
from app.models.actuator_model import ActuatorModel, ActuatorModelFeedbackDefinition
from app.models.operational_alert import AlertRule, AlertRuleProfile, AlertRuleSensorModelProfile
from app.models.user import User
from app.services.energy_monitor_service import (
    ENERGY_MONITOR_KIND,
    ENERGY_SENSOR_SPEC_BY_MODEL,
    ENERGY_SENSOR_SPECS,
    ENERGY_TEMPLATE_CODE,
    add_missing_energy_sensor_mappings,
    validate_energy_template,
)

SENSOR_MODELS: tuple[dict[str, str | float | None], ...] = (
    {
        "code": "PH",
        "name": "Cảm biến pH",
        "unit": "pH",
        "description": "Mẫu cấu hình Cảm biến pH",
        "value_type": "NUMBER",
        "chart_type": "LINE",
        "default_lower_threshold": 6.5,
        "default_upper_threshold": 8.5,
    },
    {
        "code": "TEMP",
        "name": "Cảm biến nhiệt độ nước",
        "unit": "°C",
        "description": "Mẫu cấu hình Cảm biến nhiệt độ nước",
        "value_type": "NUMBER",
        "chart_type": "LINE",
        "default_lower_threshold": 20.0,
        "default_upper_threshold": 32.0,
    },
    {
        "code": "DO",
        "name": "Cảm biến oxy hòa tan",
        "unit": "mg/L",
        "description": "Mẫu cấu hình Cảm biến oxy hòa tan",
        "value_type": "NUMBER",
        "chart_type": "LINE",
        "default_lower_threshold": 5.0,
        "default_upper_threshold": 12.0,
    },
    {
        "code": "EC",
        "name": "Cảm biến độ dẫn điện",
        "unit": "mS/cm",
        "description": "Mẫu cấu hình Cảm biến độ dẫn điện",
        "value_type": "NUMBER",
        "chart_type": "LINE",
        "default_lower_threshold": 0.8,
        "default_upper_threshold": 2.5,
    },
    {
        "code": "WATER_LEVEL",
        "name": "Cảm biến mực nước",
        "unit": "%",
        "description": "Mẫu cấu hình Cảm biến mực nước",
        "value_type": "NUMBER",
        "chart_type": "LINE",
        "default_lower_threshold": 20.0,
        "default_upper_threshold": 100.0,
    },
    {
        "code": "AIR_HUMIDITY",
        "name": "Cảm biến độ ẩm môi trường",
        "unit": "%RH",
        "description": "Đo độ ẩm tương đối của không khí tại khu vực lắp đặt.",
        "value_type": "NUMBER",
        "chart_type": "LINE",
        "default_lower_threshold": None,
        "default_upper_threshold": None,
    },
    {
        "code": "AIR_TEMPERATURE",
        "name": "Cảm biến nhiệt độ môi trường",
        "unit": "°C",
        "description": "Đo nhiệt độ không khí tại khu vực lắp đặt.",
        "value_type": "NUMBER",
        "chart_type": "LINE",
        "default_lower_threshold": None,
        "default_upper_threshold": None,
    },
    {
        "code": "AIR_PRESSURE",
        "name": "Cảm biến áp suất không khí",
        "unit": "hPa",
        "description": "Đo áp suất khí quyển tại khu vực lắp đặt.",
        "value_type": "NUMBER",
        "chart_type": "LINE",
        "default_lower_threshold": None,
        "default_upper_threshold": None,
    },
    {
        "code": "ILLUMINANCE",
        "name": "Cảm biến ánh sáng",
        "unit": "lux",
        "description": "Đo độ rọi ánh sáng tại khu vực lắp đặt.",
        "value_type": "NUMBER",
        "chart_type": "LINE",
        "default_lower_threshold": None,
        "default_upper_threshold": None,
    },
    *tuple(
        {
            "code": spec.model_code,
            "name": spec.name,
            "unit": spec.unit,
            "description": f"Đại lượng bắt buộc cho thiết bị giám sát năng lượng: {spec.name}.",
            "value_type": "NUMBER",
            "chart_type": "LINE",
            "measurement_semantics": spec.measurement_semantics,
            "default_lower_threshold": None,
            "default_upper_threshold": None,
        }
        for spec in ENERGY_SENSOR_SPECS
    ),
)

ENVIRONMENTAL_SENSOR_MODEL_CODES = frozenset(
    {
        "AIR_HUMIDITY",
        "AIR_TEMPERATURE",
        "AIR_PRESSURE",
        "ILLUMINANCE",
    }
)

ACTUATOR_MODELS = (
    ("FISH_TANK_PUMP", "Bơm hút bể cá", "Điều khiển bơm hút hoặc tuần hoàn nước tại bể cá.", 1),
    ("IRRIGATION_PUMP", "Bơm tưới", "Điều khiển bơm cấp nước cho hệ thống tưới.", 2),
    ("MIST_SYSTEM", "Phun sương", "Điều khiển hệ thống phun sương tạo ẩm môi trường.", 3),
    ("GROW_LIGHT", "Đèn chiếu sáng", "Điều khiển hệ thống đèn chiếu sáng cho khu vực trồng.", 4),
    ("ALARM_SIREN", "Còi cảnh báo", "Điều khiển còi cảnh báo khi hệ thống phát hiện sự cố.", 5),
)

CANONICAL_ALERT_SENSOR_PROFILES = (
    ("FISH_TANK_DO_LOW", "DO"),
    ("WATER_PH_OUT_OF_RANGE", "PH"),
    ("TDS_LOW", "TDS"),
    ("AIR_TEMPERATURE_HIGH", "AIR_TEMPERATURE"),
)


async def seed_sensor_models(db: AsyncSession) -> int:
    codes = tuple(str(item["code"]) for item in SENSOR_MODELS)
    existing_models = {
        model.code: model
        for model in (
            await db.scalars(select(SensorModel).where(SensorModel.code.in_(codes)))
        ).all()
    }
    missing_models = [
        SensorModel(
            **item,
            is_active=True,
            is_visible=True,
        )
        for item in SENSOR_MODELS
        if item["code"] not in existing_models
    ]
    for item in SENSOR_MODELS:
        model = existing_models.get(str(item["code"]))
        if model is None:
            continue
        model.name = str(item["name"])
        model.unit = str(item["unit"])
        model.value_type = str(item["value_type"])
        model.chart_type = str(item["chart_type"])
        if "measurement_semantics" in item:
            model.measurement_semantics = str(item["measurement_semantics"])
        model.is_active = True
        model.is_deleted = False
        model.deleted_at = None
    db.add_all(missing_models)
    await db.flush()
    return len(missing_models)


async def seed_energy_monitor_template(db: AsyncSession) -> DeviceTemplate:
    template = await db.scalar(
        select(DeviceTemplate)
        .options(
            selectinload(DeviceTemplate.sensor_mappings).selectinload(
                DeviceTemplateSensor.sensor_model
            ),
            selectinload(DeviceTemplate.actuator_mappings).selectinload(
                DeviceTemplateActuator.actuator_model
            ),
        )
        .where(DeviceTemplate.code == ENERGY_TEMPLATE_CODE)
    )
    if template is None:
        template = DeviceTemplate(
            code=ENERGY_TEMPLATE_CODE,
            name="Thiết bị giám sát năng lượng 12V",
            description="Thiết bị đo sáu đại lượng năng lượng bắt buộc.",
            notes="ENERGY_TOTAL_WH là cumulative counter có xử lý reset theo đoạn.",
            device_kind=ENERGY_MONITOR_KIND,
            nominal_output_voltage_v=12,
            is_active=False,
        )
        db.add(template)
        await db.flush()
        template.sensor_mappings = []
    else:
        template.name = "Thiết bị giám sát năng lượng 12V"
        template.device_kind = ENERGY_MONITOR_KIND
        template.nominal_output_voltage_v = 12
        template.is_deleted = False
        template.deleted_at = None
    template.description = "Thiết bị đo sáu đại lượng năng lượng bắt buộc."
    template.notes = "ENERGY_TOTAL_WH là cumulative counter có xử lý reset theo đoạn."
    canonical_codes = {spec.model_code for spec in ENERGY_SENSOR_SPECS}
    for mapping in list(template.sensor_mappings):
        if mapping.sensor_model.code not in canonical_codes:
            await db.delete(mapping)
            continue
        spec = ENERGY_SENSOR_SPEC_BY_MODEL[mapping.sensor_model.code]
        mapping.display_name = spec.name
        mapping.sort_order = spec.sort_order
        mapping.is_required = True
    await db.flush()
    await add_missing_energy_sensor_mappings(db, template)
    refreshed = await db.scalar(
        select(DeviceTemplate)
        .options(
            selectinload(DeviceTemplate.sensor_mappings).selectinload(
                DeviceTemplateSensor.sensor_model
            ),
            selectinload(DeviceTemplate.actuator_mappings).selectinload(
                DeviceTemplateActuator.actuator_model
            ),
        )
        .where(DeviceTemplate.id == template.id)
        .execution_options(populate_existing=True)
    )
    if refreshed is None:
        raise RuntimeError("Không thể tải lại mẫu Energy Monitor sau seed")
    validate_energy_template(refreshed)
    refreshed.is_active = True
    return refreshed


async def seed_actuator_models(db: AsyncSession) -> int:
    codes = tuple(item[0] for item in ACTUATOR_MODELS)
    existing_codes = set(
        (await db.scalars(select(ActuatorModel.code).where(ActuatorModel.code.in_(codes)))).all()
    )
    missing = [
        ActuatorModel(
            code=code,
            name=name,
            description=description,
            data_type="BOOLEAN",
            default_state=False,
            is_active=True,
            sort_order=sort_order,
        )
        for code, name, description, sort_order in ACTUATOR_MODELS
        if code not in existing_codes
    ]
    db.add_all(missing)
    await db.flush()
    return len(missing)


async def seed_actuator_model_feedbacks(db: AsyncSession) -> int:
    sensor_models = {
        item.code: item
        for item in (await db.scalars(select(SensorModel).where(
            SensorModel.code.in_(("OUTPUT_VOLTAGE_V", "LOAD_CURRENT_A")),
            SensorModel.is_active.is_(True),
            SensorModel.is_deleted.is_(False),
        ))).all()
    }
    if set(sensor_models) != {"OUTPUT_VOLTAGE_V", "LOAD_CURRENT_A"}:
        return 0
    models = list((await db.scalars(select(ActuatorModel).where(
        ActuatorModel.is_active.is_(True),
        ActuatorModel.is_deleted.is_(False),
        ActuatorModel.data_type == "BOOLEAN",
    ))).all())
    existing = {
        (model_id, role)
        for model_id, role in (await db.execute(select(
            ActuatorModelFeedbackDefinition.actuator_model_id,
            ActuatorModelFeedbackDefinition.feedback_role,
        ))).all()
    }
    created = 0
    for model in models:
        for role, sensor_model_code, value_key, unit, order in (
            ("SUPPLY_VOLTAGE", "OUTPUT_VOLTAGE_V", "voltage_v", "V", 0),
            ("RUNNING_CURRENT", "LOAD_CURRENT_A", "current_a", "A", 1),
        ):
            if (model.id, role) in existing:
                continue
            db.add(ActuatorModelFeedbackDefinition(
                actuator_model_id=model.id,
                feedback_role=role,
                sensor_model_id=sensor_models[sensor_model_code].id,
                value_key=value_key,
                unit=unit,
                data_type="FLOAT",
                is_required=True,
                is_enabled=True,
                display_order=order,
            ))
            created += 1
    await db.flush()
    return created


async def seed_canonical_alert_profiles(db: AsyncSession) -> int:
    created = 0
    for rule_code, model_code in CANONICAL_ALERT_SENSOR_PROFILES:
        rule = await db.scalar(select(AlertRule).where(AlertRule.code == rule_code))
        model = await db.scalar(select(SensorModel).where(SensorModel.code == model_code))
        if rule is None or model is None:
            continue
        profile_code = f"{rule_code}_CANONICAL"
        profile = await db.scalar(select(AlertRuleProfile).where(AlertRuleProfile.code == profile_code))
        if profile is None:
            profile = AlertRuleProfile(
                rule_id=rule.id,
                code=profile_code,
                name=f"Áp dụng cho SensorModel {model_code}",
                config={},
                is_enabled=True,
            )
            db.add(profile)
            await db.flush()
            created += 1
        else:
            profile.rule_id = rule.id
            profile.is_enabled = True
        link = await db.get(AlertRuleSensorModelProfile, (profile.id, model.id))
        if link is None:
            db.add(AlertRuleSensorModelProfile(profile_id=profile.id, sensor_model_id=model.id))
    await db.flush()
    return created


async def seed() -> None:
    async with AsyncSessionLocal() as db:
        admin = await db.scalar(select(User).where(User.username == settings.default_admin_username))
        if admin is None:
            admin = User(
                username=settings.default_admin_username,
                password_hash=hash_password(settings.default_admin_password),
                full_name="Quản trị viên hệ thống",
                email="admin@aquaponics.vn",
                phone_number="0000000000",
                address="",
                system_role=UserRole.ADMIN,
                status=UserStatus.ACTIVE,
                must_change_password=False,
            )
            db.add(admin)
        else:
            admin.system_role = UserRole.ADMIN
            admin.status = UserStatus.ACTIVE
            admin.is_deleted = False
            admin.deleted_at = None
            admin.must_change_password = False
            admin.email = "admin@aquaponics.vn"
            if settings.reset_default_admin_password:
                admin.password_hash = hash_password(settings.default_admin_password)
        await seed_sensor_models(db)
        await db.flush()
        await seed_energy_monitor_template(db)
        await seed_actuator_models(db)
        await seed_actuator_model_feedbacks(db)
        await seed_canonical_alert_profiles(db)
        await db.commit()


if __name__ == "__main__":
    asyncio.run(seed())
