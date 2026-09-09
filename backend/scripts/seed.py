import asyncio
import importlib.util
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.core.enums import UserRole, UserStatus
from app.core.security import hash_password
from app.models.sensor import SensorModel
from app.models.actuator_model import ActuatorModel
from app.models.operational_alert import AlertRule, AlertRuleProfile, AlertRuleSensorModelProfile
from app.models.user import User
from app.models.permission import Permission, Role, RolePermission

SENSOR_MODELS: tuple[dict[str, str | float | None], ...] = (
    {
        "code": "PH",
        "name": "Cảm biến pH",
        "unit": "pH",
        "description": "Mẫu cấu hình Cảm biến pH",
        "value_type": "NUMBER",
        "chart_type": "LINE",
        "default_lower_threshold": 6.0,
        "default_upper_threshold": 7.5,
    },
    {
        "code": "TEMP",
        "name": "Cảm biến nhiệt độ nước",
        "unit": "°C",
        "description": "Mẫu cấu hình Cảm biến nhiệt độ nước",
        "value_type": "NUMBER",
        "chart_type": "LINE",
        "default_lower_threshold": 18.0,
        "default_upper_threshold": 35.0,
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
        "default_lower_threshold": 60.0,
        "default_upper_threshold": None,
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
        "code": "TDS",
        "name": "Cảm biến TDS",
        "unit": "ppm",
        "description": "Đo tổng chất rắn hòa tan trong nước.",
        "value_type": "NUMBER",
        "chart_type": "LINE",
        "default_lower_threshold": 100.0,
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
    {"code": "OUTPUT_VOLTAGE_V", "name": "Điện áp đầu ra", "unit": "V", "description": "Điện áp đo trực tiếp tại Device.", "value_type": "NUMBER", "chart_type": "LINE", "measurement_semantics": "GAUGE", "default_lower_threshold": None, "default_upper_threshold": None},
    {"code": "INPUT_VOLTAGE_V", "name": "Điện áp đầu vào", "unit": "V", "description": "Điện áp đo trực tiếp tại Device.", "value_type": "NUMBER", "chart_type": "LINE", "measurement_semantics": "GAUGE", "default_lower_threshold": None, "default_upper_threshold": None},
    {"code": "LOAD_CURRENT_A", "name": "Dòng điện tải", "unit": "A", "description": "Dòng điện đo trực tiếp tại Device.", "value_type": "NUMBER", "chart_type": "LINE", "measurement_semantics": "GAUGE", "default_lower_threshold": None, "default_upper_threshold": None},
    {"code": "INPUT_CURRENT_A", "name": "Dòng điện đầu vào", "unit": "A", "description": "Dòng điện đo trực tiếp tại Device.", "value_type": "NUMBER", "chart_type": "LINE", "measurement_semantics": "GAUGE", "default_lower_threshold": None, "default_upper_threshold": None},
    {"code": "POWER_W", "name": "Công suất", "unit": "W", "description": "Công suất được phần cứng đo trực tiếp.", "value_type": "NUMBER", "chart_type": "LINE", "measurement_semantics": "GAUGE", "default_lower_threshold": None, "default_upper_threshold": None},
    {"code": "ENERGY_TOTAL_WH", "name": "Điện năng tích lũy", "unit": "Wh", "description": "Bộ đếm điện năng tích lũy có xử lý reset theo đoạn.", "value_type": "NUMBER", "chart_type": "LINE", "measurement_semantics": "COUNTER", "default_lower_threshold": None, "default_upper_threshold": None},
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
    ("AIR_PUMP", "Máy sủi oxy", "Cấp khí cho bể cá hoặc bể lọc vi sinh.", 6),
)

ACTUATOR_ELECTRICAL_DEFAULTS = {
    code: {
        "nominal_voltage_v": 12.0,
        "voltage_tolerance_v": 1.5,
        "zero_voltage_max_v": 1.0,
        "minimum_running_current_a": 0.10,
        "maximum_running_current_a": 10.0,
    }
    for code in ("FISH_TANK_PUMP", "IRRIGATION_PUMP", "MIST_SYSTEM", "GROW_LIGHT", "AIR_PUMP")
}

CANONICAL_ALERT_SENSOR_PROFILES = (
    ("FISH_TANK_DO_LOW", "DO"),
    ("WATER_PH_OUT_OF_RANGE", "PH"),
    ("TDS_LOW", "TDS"),
    ("AIR_TEMPERATURE_HIGH", "AIR_TEMPERATURE"),
)


def _canonical_permissions() -> tuple[tuple[str, str, str], ...]:
    """Read the 0050 RBAC catalog from the migration that introduced it."""
    path = Path(__file__).resolve().parents[1] / "alembic/versions/0047_permission_rbac.py"
    spec = importlib.util.spec_from_file_location("permission_rbac_0047", path)
    if spec is None or spec.loader is None: raise RuntimeError("Cannot load canonical permission catalog")
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module.PERMISSIONS


async def seed_rbac(db: AsyncSession) -> None:
    roles: dict[str, Role] = {row.code: row for row in (await db.scalars(select(Role))).all()}
    for code, name in (("ADMIN", "Administrator"), ("OWNER", "System Owner"), ("TECHNICIAN", "Technician"), ("VIEWER", "Viewer")):
        if code not in roles:
            roles[code] = Role(code=code, name=name, is_system=True, enabled=True); db.add(roles[code])
    permissions: dict[str, Permission] = {row.code: row for row in (await db.scalars(select(Permission))).all()}
    for code, resource, action in _canonical_permissions():
        if code not in permissions:
            permissions[code] = Permission(code=code, resource=resource, action=action); db.add(permissions[code])
    await db.flush()
    existing = {(row.role_id, row.permission_id) for row in (await db.scalars(select(RolePermission))).all()}
    for role_code, role in roles.items():
        for permission in permissions.values():
            allowed = role_code == "ADMIN" or (role_code == "VIEWER" and permission.resource != "users" and permission.action in {"read", "telemetry.read", "thresholds.read", "commands.read", "readings.read", "history.read", "export"}) or (role_code in {"OWNER", "TECHNICIAN"} and permission.resource != "users" and permission.action not in {"read_all", "manage_all"})
            if allowed and (role.id, permission.id) not in existing: db.add(RolePermission(role_id=role.id, permission_id=permission.id))
    await db.flush()


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
            **ACTUATOR_ELECTRICAL_DEFAULTS.get(code, {}),
        )
        for code, name, description, sort_order in ACTUATOR_MODELS
        if code not in existing_codes
    ]
    existing_models = list((await db.scalars(select(ActuatorModel).where(ActuatorModel.code.in_(codes)))).all())
    for model in existing_models:
        for field, value in ACTUATOR_ELECTRICAL_DEFAULTS.get(model.code, {}).items():
            if getattr(model, field) is None:
                setattr(model, field, value)
    db.add_all(missing)
    await db.flush()
    return len(missing)


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
        await seed_rbac(db)
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
        owner = await db.scalar(select(User).where(User.username == settings.default_owner_username))
        if owner is None:
            owner = User(
                username=settings.default_owner_username,
                password_hash=hash_password(settings.default_admin_password),
                full_name="Chủ sở hữu hệ thống",
                email="owner@aquaponics.vn",
                phone_number="0000000001",
                address="",
                system_role=UserRole.OWNER,
                status=UserStatus.ACTIVE,
                must_change_password=True,
            )
            db.add(owner)
        else:
            owner.system_role = UserRole.OWNER
            owner.status = UserStatus.ACTIVE
            owner.is_deleted = False
            owner.deleted_at = None
            owner.must_change_password = True
        await seed_sensor_models(db)
        await db.flush()
        await seed_actuator_models(db)
        roles = {role.code: role.id for role in (await db.scalars(select(Role))).all()}
        if roles:
            admin.role_id = roles.get(UserRole.ADMIN.value)
            owner.role_id = roles.get(UserRole.OWNER.value)
        await db.commit()


if __name__ == "__main__":
    asyncio.run(seed())
