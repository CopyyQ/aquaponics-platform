import asyncio
import logging
from datetime import UTC, datetime
from typing import Protocol
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.enums import AlertType
from app.models.actuator import Actuator, ActuatorCommand
from app.models.actuator_model import ActuatorModelFeedbackDefinition
from app.models.alert import SensorAlert
from app.models.device import Device
from app.models.operational_alert import ActuatorFeedbackBinding
from app.models.project import Project
from app.models.project_settings import ProjectNotificationRecipient, ProjectNotificationSettings
from app.models.sensor import Sensor, SensorModel
from app.models.telemetry import TelemetryReading
from app.models.user import User
from app.services.measurement_quality import classify_measurement_quality
from app.services.telegram_notifier import TelegramDeliveryResult, TelegramNotifier

logger = logging.getLogger(__name__)


# Semantic fallbacks only. Persisted names always win and no physical device is
# inferred from these labels.
SENSOR_MODEL_DISPLAY = {
    "PH": ("pH", "pH"), "TEMP": ("Nhiệt độ nước", "°C"),
    "DO": ("Oxy hòa tan", "mg/L"), "EC": ("Độ dẫn điện", "mS/cm"),
    "WATER_LEVEL": ("Mực nước", "%"), "AIR_TEMPERATURE": ("Nhiệt độ môi trường", "°C"),
    "AIR_HUMIDITY": ("Độ ẩm môi trường", "%RH"), "AIR_PRESSURE": ("Áp suất không khí", "hPa"),
    "ILLUMINANCE": ("Ánh sáng", "lux"), "TDS_01": ("Tổng chất rắn hòa tan", "ppm"),
    "TDS": ("Tổng chất rắn hòa tan", "ppm"), "INPUT_VOLTAGE_V": ("Điện áp đầu vào", "V"),
    "OUTPUT_VOLTAGE_V": ("Điện áp đầu ra", "V"), "INPUT_CURRENT_A": ("Dòng điện đầu vào", "A"),
    "LOAD_CURRENT_A": ("Dòng điện tải", "A"), "POWER_W": ("Công suất", "W"),
    "ENERGY_TOTAL_WH": ("Điện năng", "Wh"),
}
ACTUATOR_MODEL_DISPLAY = {
    "FISH_TANK_PUMP": "Bơm hút bể cá", "IRRIGATION_PUMP": "Bơm tưới",
    "MIST_SYSTEM": "Phun sương", "GROW_LIGHT": "Đèn chiếu sáng",
    "ALARM_SIREN": "Còi cảnh báo", "AERATOR_PUMP": "Máy sủi oxy",
}
SEVERITY_LABELS = {"WARNING": "Cảnh báo", "CRITICAL": "Nghiêm trọng"}
RISK_LABELS = {
    "EXTREME": "Cực cao", "VERY_HIGH": "Rất cao", "HIGH": "Cao",
    "MEDIUM": "Trung bình", "LOW_MEDIUM": "Thấp–trung bình", "LOW": "Thấp",
}
SEVERITY_ORDER = {"WARNING": 0, "CRITICAL": 1}
QUALITY_LABELS = {"VALID": "Hợp lệ", "STALE": "Dữ liệu cũ", "NO_DATA": "Không có dữ liệu", "INVALID": "Không hợp lệ", "OUT_OF_RANGE": "Ngoài phạm vi"}


BUSINESS_ALERT_RULE_SOURCE = "Bảng cảnh báo mức độ (1).xlsx"

# V1 business catalogue transcribed from the Excel specification.
# This catalogue enriches notification text only; it does NOT evaluate the
# condition again. Runtime evaluators/incident services remain responsible for
# deciding when a rule is OPENED/ESCALATED/RECOVERED/RESOLVED.
BUSINESS_ALERT_RULES: dict[str, dict[str, object]] = {
    "FISH_TANK_DO_LOW": {
        "excel_index": 1,
        "name": "DO nước bể cá",
        "risk_level": "EXTREME",
        "threshold_text": "< 5 mg/L; nguy cơ tăng rất mạnh khi < 4 mg/L",
        "message": None,
        "consequence": "Cá stress, giảm ăn; thấp kéo dài có thể chết",
        "source_note": "Hiện tại hệ thống chưa có cảm biến DO",
        "target_type": "SENSOR",
        "sensor_model_codes": ("DO",),
        "actuator_model_codes": (),
        "feedback_role": None,
        "mapping_status": "READY_BY_MODEL",
    },
    "FISH_TANK_AERATOR_NO_CURRENT": {
        "excel_index": 2,
        "name": "Máy sủi oxy bể cá mất hoạt động",
        "risk_level": "EXTREME",
        "threshold_text": "Mất điện / dòng = 0",
        "message": "Máy sục oxy đang có vấn đề, cần kiểm tra!",
        "consequence": "DO có thể tụt nhanh, đặc biệt ban đêm",
        "source_note": None,
        "target_type": "ACTUATOR",
        "sensor_model_codes": (),
        "actuator_model_codes": ("AERATOR_PUMP",),
        "feedback_role": "RUNNING_CURRENT",
        "mapping_status": "NEED_PHYSICAL_ROLE",
    },
    "FISH_TO_RFF_PUMP_NO_CURRENT": {
        "excel_index": 3,
        "name": "Bơm hút từ bể cá lên bể RFF mất hoạt động",
        "risk_level": "EXTREME",
        "threshold_text": "Command ON nhưng không có dòng",
        "message": "Bơm hút bể cá đang có vấn đề, cần kiểm tra!",
        "consequence": "Chất thải không được đưa vào lọc; có thể ảnh hưởng tuần hoàn",
        "source_note": None,
        "target_type": "ACTUATOR",
        "sensor_model_codes": (),
        "actuator_model_codes": ("FISH_TANK_PUMP",),
        "feedback_role": "RUNNING_CURRENT",
        "mapping_status": "READY_BY_MODEL",
    },
    "NFT_PUMP_NO_CURRENT": {
        "excel_index": 4,
        "name": "Bơm nước lên giàn NFT mất hoạt động",
        "risk_level": "EXTREME",
        "threshold_text": "Bơm ON nhưng dòng ≈ 0",
        "message": "Bơm nước lên giàn đang có vấn đề, cần kiểm tra!",
        "consequence": "Cây mất nước; rễ có thể khô nếu kéo dài",
        "source_note": None,
        "target_type": "ACTUATOR",
        "sensor_model_codes": (),
        "actuator_model_codes": (),
        "feedback_role": "RUNNING_CURRENT",
        "mapping_status": "NEED_MODEL_OR_ROLE",
    },
    "BIOFILTER_WATER_LEVEL_LOW": {
        "excel_index": 5,
        "name": "Mực nước bể lọc vi sinh thấp",
        "risk_level": "EXTREME",
        "threshold_text": "Float LOW tác động",
        "message": "Mực nước bể lọc vi sinh thấp, kiểm tra bơm hút bể cá và ống nước có bị rò rỉ không",
        "consequence": "Có thể gây hại cho hệ vi sinh",
        "source_note": None,
        "target_type": "SENSOR",
        "sensor_model_codes": ("WATER_LEVEL",),
        "actuator_model_codes": (),
        "feedback_role": None,
        "mapping_status": "NEED_PHYSICAL_ROLE",
    },
    "FISH_TANK_WATER_LEVEL_LOW": {
        "excel_index": 6,
        "name": "Mực nước bể cá thấp / nguy cơ chạy khô bơm",
        "risk_level": "EXTREME",
        "threshold_text": "Float LOW tác động",
        "message": "Mực nước bể cá thấp, hãy kiểm tra các ống nước có bị rò rỉ nước không",
        "consequence": "Có thể phá bơm + mất tuần hoàn, cá có thể chết",
        "source_note": None,
        "target_type": "SENSOR",
        "sensor_model_codes": ("WATER_LEVEL",),
        "actuator_model_codes": (),
        "feedback_role": None,
        "mapping_status": "NEED_PHYSICAL_ROLE",
    },
    "FISH_TANK_WATER_LEVEL_HIGH": {
        "excel_index": 7,
        "name": "Mực nước bể cá quá cao / nguy cơ tràn",
        "risk_level": "EXTREME",
        "threshold_text": "Float HIGH tác động bất thường",
        "message": "Mực nước bể cá cao, nguy cơ cá nhảy ra ngoài",
        "consequence": "Tràn nước, mất nước hệ thống, nguy hiểm điện",
        "source_note": None,
        "target_type": "SENSOR",
        "sensor_model_codes": ("WATER_LEVEL",),
        "actuator_model_codes": (),
        "feedback_role": None,
        "mapping_status": "NEED_PHYSICAL_ROLE",
    },
    "WATER_PH_OUT_OF_RANGE": {
        "excel_index": 8,
        "name": "pH nước",
        "risk_level": "VERY_HIGH",
        "threshold_text": "< 6.0 hoặc > 8.0; vượt xa khoảng an toàn khi < 5.5 hoặc > 8.5",
        "message": "pH bất thường, hãy kiểm tra môi trường nước",
        "consequence": "Ảnh hưởng cá + vi khuẩn nitrification + hấp thu dinh dưỡng",
        "source_note": None,
        "target_type": "SENSOR",
        "sensor_model_codes": ("PH",),
        "actuator_model_codes": (),
        "feedback_role": None,
        "mapping_status": "READY_BY_MODEL",
    },
    "WATER_TEMPERATURE_HIGH": {
        "excel_index": 9,
        "name": "Nhiệt độ nước",
        "risk_level": "VERY_HIGH",
        "threshold_text": "> 30–31°C; nguy cơ tăng rất mạnh khi > 32°C",
        "message": "Nhiệt độ nước bể cá cao, hãy che nắng cho bể cá",
        "consequence": "DO giảm mạnh, cá stress, vi sinh bị ảnh hưởng",
        "source_note": "Tuỳ loại cá có ngưỡng chịu đựng khác nhau",
        "target_type": "SENSOR",
        "sensor_model_codes": ("TEMP",),
        "actuator_model_codes": (),
        "feedback_role": None,
        "mapping_status": "READY_BY_MODEL",
    },
    "BIOFILTER_AERATOR_NO_FEEDBACK": {
        "excel_index": 10,
        "name": "Bơm oxy bể lọc vi sinh mất hoạt động",
        "risk_level": "HIGH",
        "threshold_text": "Command ON nhưng không có dòng/áp khí",
        "message": "Máy sục oxy đang có vấn đề, hãy kiểm tra",
        "consequence": "Biofilter thiếu oxy, nitrification suy giảm",
        "source_note": None,
        "target_type": "ACTUATOR",
        "sensor_model_codes": (),
        "actuator_model_codes": ("AERATOR_PUMP",),
        "feedback_role": "RUNNING_CURRENT",
        "mapping_status": "NEED_PHYSICAL_ROLE",
    },
    "MAIN_PUMP_FLOW_LOW": {
        "excel_index": 11,
        "name": "Flow bơm chính giảm mạnh",
        "risk_level": "HIGH",
        "threshold_text": "< 70–80% giá trị bình thường",
        "message": None,
        "consequence": "Có thể báo hiệu tắc lọc, tắc ống, bơm yếu",
        "source_note": "Hiện tại không có cảm biến lưu lượng",
        "target_type": "SENSOR",
        "sensor_model_codes": (),
        "actuator_model_codes": (),
        "feedback_role": None,
        "mapping_status": "NEED_SENSOR_MODEL",
    },
    "AMMONIA_ABNORMAL": {
        "excel_index": 12,
        "name": "NH₃/NH₄⁺",
        "risk_level": "HIGH",
        "threshold_text": "NH₃ tăng bất thường / NH₄⁺ tăng liên tục",
        "message": None,
        "consequence": "Độc tính với cá, đặc biệt khi pH và nhiệt độ cao",
        "source_note": "Hiện tại chưa có cảm biến",
        "target_type": "SENSOR",
        "sensor_model_codes": (),
        "actuator_model_codes": (),
        "feedback_role": None,
        "mapping_status": "NEED_SENSOR_MODEL",
    },
    "NITRITE_HIGH": {
        "excel_index": 13,
        "name": "NO₂⁻",
        "risk_level": "HIGH",
        "threshold_text": "> 0.5 mg/L; nguy cơ tăng rất mạnh khi > 1 mg/L",
        "message": None,
        "consequence": "Độc với cá, dấu hiệu biofilter có vấn đề",
        "source_note": "Hiện tại chưa có cảm biến",
        "target_type": "SENSOR",
        "sensor_model_codes": (),
        "actuator_model_codes": (),
        "feedback_role": None,
        "mapping_status": "NEED_SENSOR_MODEL",
    },
    "TDS_LOW": {
        "excel_index": 14,
        "name": "TDS",
        "risk_level": "MEDIUM",
        "threshold_text": "TDS < 100 ppm",
        "message": "Nồng độ dinh dưỡng quá thấp",
        "consequence": "Báo hiệu thay đổi hóa học, bay hơi hoặc bổ sung khoáng",
        "source_note": None,
        "target_type": "SENSOR",
        "sensor_model_codes": ("TDS_01", "TDS"),
        "actuator_model_codes": (),
        "feedback_role": None,
        "mapping_status": "READY_WITH_ALIAS",
    },
    "AIR_TEMPERATURE_HIGH": {
        "excel_index": 15,
        "name": "Nhiệt độ không khí",
        "risk_level": "MEDIUM",
        "threshold_text": "> 35°C",
        "message": "Nhiệt độ không khí cao, chú ý che nắng cho giàn",
        "consequence": "Tăng nhiệt nước, stress cây/cá gián tiếp",
        "source_note": None,
        "target_type": "SENSOR",
        "sensor_model_codes": ("AIR_TEMPERATURE",),
        "actuator_model_codes": (),
        "feedback_role": None,
        "mapping_status": "READY_BY_MODEL",
    },
    "AIR_HUMIDITY_HIGH": {
        "excel_index": 16,
        "name": "Độ ẩm không khí",
        "risk_level": "MEDIUM",
        "threshold_text": "> 85–90% kéo dài",
        "message": "Độ ẩm không khí cao, nguy cơ nấm bệnh",
        "consequence": "Tăng nguy cơ nấm bệnh, ngưng tụ",
        "source_note": None,
        "target_type": "SENSOR",
        "sensor_model_codes": ("AIR_HUMIDITY",),
        "actuator_model_codes": (),
        "feedback_role": None,
        "mapping_status": "READY_BY_MODEL_DURATION_PENDING",
    },
    "GROW_LIGHT_NO_CURRENT": {
        "excel_index": 17,
        "name": "Đèn chiếu sáng cho cây",
        "risk_level": "LOW_MEDIUM",
        "threshold_text": "ON theo lịch nhưng dòng = 0",
        "message": "Đèn chiếu sáng đang có vấn đề, cần kiểm tra!",
        "consequence": "Ảnh hưởng sinh trưởng cây, nhưng không nguy hiểm tức thời",
        "source_note": None,
        "target_type": "ACTUATOR",
        "sensor_model_codes": (),
        "actuator_model_codes": ("GROW_LIGHT",),
        "feedback_role": "RUNNING_CURRENT",
        "mapping_status": "READY_MODEL_SCHEDULE_PENDING",
    },
    "ENVIRONMENT_LIGHT_LOW_LONG_TERM": {
        "excel_index": 18,
        "name": "Cường độ ánh sáng môi trường",
        "risk_level": "LOW",
        "threshold_text": "Cường độ ánh sáng thấp trong nhiều ngày",
        "message": "Cường độ ánh sáng thấp trong nhiều ngày, nguy cơ rau kém phát triển",
        "consequence": "Chủ yếu ảnh hưởng tốc độ sinh trưởng",
        "source_note": None,
        "target_type": "SENSOR",
        "sensor_model_codes": ("ILLUMINANCE",),
        "actuator_model_codes": (),
        "feedback_role": None,
        "mapping_status": "READY_MODEL_WINDOW_PENDING",
    },
    "TDS_LOW_LONG_TERM": {
        "excel_index": 19,
        "name": "TDS/EC thay đổi chậm",
        "risk_level": "LOW",
        "threshold_text": "TDS <150 trong nhiều ngày",
        "message": "Nồng độ dinh dưỡng thấp trong nhiều ngày",
        "consequence": "Cần theo dõi xu hướng hơn là báo động tức thời",
        "source_note": None,
        "target_type": "SENSOR",
        "sensor_model_codes": ("TDS_01", "TDS"),
        "actuator_model_codes": (),
        "feedback_role": None,
        "mapping_status": "READY_WITH_ALIAS_WINDOW_PENDING",
    },
}

# Only unambiguous mappings are inferred automatically. Ambiguous physical
# roles (e.g. WATER_LEVEL location or AERATOR_PUMP fish-tank vs biofilter)
# require the caller/evaluator to pass business_rule_code explicitly.
SENSOR_MODEL_DEFAULT_BUSINESS_RULE = {
    "DO": "FISH_TANK_DO_LOW",
    "PH": "WATER_PH_OUT_OF_RANGE",
    "TEMP": "WATER_TEMPERATURE_HIGH",
    "TDS_01": "TDS_LOW",
    "TDS": "TDS_LOW",
    "AIR_TEMPERATURE": "AIR_TEMPERATURE_HIGH",
    "AIR_HUMIDITY": "AIR_HUMIDITY_HIGH",
}

ACTUATOR_MODEL_DEFAULT_BUSINESS_RULE = {
    ("FISH_TANK_PUMP", "RUNNING_CURRENT"): "FISH_TO_RFF_PUMP_NO_CURRENT",
    ("GROW_LIGHT", "RUNNING_CURRENT"): "GROW_LIGHT_NO_CURRENT",
}



def _label(mapping: dict[str, str], value: object, fallback: str = "Chưa xác định") -> str:
    return mapping.get(_enum_value(value), fallback)


def _state(value: bool | None) -> str:
    return "Bật" if value is True else "Tắt" if value is False else "Chưa xác định"


def _severity_increased(previous: str | None, current: str) -> bool:
    return previous is not None and SEVERITY_ORDER.get(current, -1) > SEVERITY_ORDER.get(_enum_value(previous), -1)


class Notifier(Protocol):
    configured: bool

    async def send_message(self, chat_id: str, text: str) -> TelegramDeliveryResult: ...


def format_display_time(value: datetime | None) -> str:
    if not isinstance(value, datetime):
        return "—"
    try:
        zone = ZoneInfo(settings.display_timezone)
    except ZoneInfoNotFoundError:
        zone = ZoneInfo("UTC")
    return f"{value.astimezone(zone).strftime('%d/%m/%Y %H:%M:%S')} ({settings.display_timezone})"


def _number(value: float | None) -> str:
    return "—" if value is None else f"{value:.2f}".rstrip("0").rstrip(".")


def _enum_value(value: object) -> str:
    return str(getattr(value, "value", value))


def get_business_alert_rule(rule_code: str | None) -> dict[str, object] | None:
    if not rule_code:
        return None
    return BUSINESS_ALERT_RULES.get(rule_code)


def _business_rule_fallback_message(rule: dict[str, object]) -> str:
    message = rule.get("message")
    if isinstance(message, str) and message.strip():
        return message.strip()
    name = str(rule.get("name") or "Thông số/sự kiện")
    return f"{name} đang ở trạng thái bất thường, cần kiểm tra."


def _business_rule_lines(rule: dict[str, object] | None, *, include_source_note: bool = False) -> list[str]:
    if rule is None:
        return []
    risk = str(rule.get("risk_level") or "")
    threshold_text = str(rule.get("threshold_text") or "").strip()
    consequence = str(rule.get("consequence") or "").strip()
    source_note = str(rule.get("source_note") or "").strip()
    lines = [
        f"Quy tắc nghiệp vụ: {rule.get('name') or '—'}",
        f"Mức rủi ro: {RISK_LABELS.get(risk, risk or 'Chưa xác định')}",
    ]
    if threshold_text:
        lines.append(f"Ngưỡng/điều kiện nghiệp vụ: {threshold_text}")
    lines.append(f"Nội dung cảnh báo: {_business_rule_fallback_message(rule)}")
    if consequence:
        lines.append(f"Hậu quả nếu không xử lý: {consequence}")
    # Excel contains a few implementation-status notes such as
    # "Hiện tại chưa có cảm biến". Keep them in the catalogue for audit, but do
    # not send stale implementation notes to operators by default.
    if include_source_note and source_note:
        lines.append(f"Ghi chú từ bảng nghiệp vụ: {source_note}")
    elif source_note and not source_note.lower().startswith("hiện tại"):
        lines.append(f"Ghi chú: {source_note}")
    return lines


def _resolve_sensor_business_rule(
    sensor_model_code: str | None,
    explicit_rule_code: str | None,
) -> tuple[str | None, dict[str, object] | None]:
    if explicit_rule_code:
        return explicit_rule_code, get_business_alert_rule(explicit_rule_code)
    if not sensor_model_code:
        return None, None
    rule_code = SENSOR_MODEL_DEFAULT_BUSINESS_RULE.get(sensor_model_code)
    return rule_code, get_business_alert_rule(rule_code)


def _resolve_actuator_business_rule(
    actuator_model_code: str | None,
    feedback_role: str | None,
    explicit_rule_code: str | None,
) -> tuple[str | None, dict[str, object] | None]:
    if explicit_rule_code:
        return explicit_rule_code, get_business_alert_rule(explicit_rule_code)
    if not actuator_model_code or not feedback_role:
        return None, None
    rule_code = ACTUATOR_MODEL_DEFAULT_BUSINESS_RULE.get((actuator_model_code, feedback_role))
    return rule_code, get_business_alert_rule(rule_code)


def _risk_label_for_rule(rule: dict[str, object] | None) -> str:
    if rule is None:
        return "Chưa xác định"
    risk = str(rule.get("risk_level") or "")
    return RISK_LABELS.get(risk, risk or "Chưa xác định")


def _risk_heading(rule: dict[str, object] | None, *, recovered: bool = False) -> str:
    if recovered:
        return "✅ CẢNH BÁO ĐÃ ĐƯỢC KHẮC PHỤC"
    return f"🚨 CẢNH BÁO MỨC {_risk_label_for_rule(rule).upper()}"


def format_alert_message(
    *,
    transition: str,
    project_name: str,
    alert: SensorAlert,
    device_name: str,
    project_code: str = "",
    sensor: Sensor | None = None,
    sensor_model: SensorModel | None = None,
    sensor_name: str | None = None,
    observed_value: float | None = None,
    observed_at: datetime | None = None,
    occurrence_count: int | None = None,
    previous_severity: str | None = None,
    business_rule_code: str | None = None,
) -> str:
    """Format one business-level sensor notification.

    WARNING/CRITICAL remain implementation details of legacy SensorAlert and are
    intentionally not shown to operators. The only user-visible alert level is
    the Vietnamese business risk level from the Excel catalogue.
    """
    del occurrence_count, previous_severity  # kept only for caller compatibility

    project_label = f"{project_name} ({project_code})" if project_code else project_name
    display_sensor_name = sensor.name if sensor is not None else sensor_name or "—"
    sensor_model_code = sensor_model.code if sensor_model is not None else None
    resolved_rule_code, business_rule = _resolve_sensor_business_rule(sensor_model_code, business_rule_code)
    risk_label = _risk_label_for_rule(business_rule)

    if transition == "RESOLVED_CONFIRMED":
        actor_name = alert.resolved_by_user.full_name if alert.resolved_by_user else f"User #{alert.resolved_by_user_id}"
        return "\n".join(
            [
                "✅ CẢNH BÁO ĐÃ ĐƯỢC XÁC NHẬN KHẮC PHỤC",
                "",
                f"Dự án: {project_label}",
                f"Mức độ: {risk_label}",
                f"Thiết bị/Cảm biến: {device_name} / {display_sensor_name}",
                *([f"Mã quy tắc: {resolved_rule_code}"] if resolved_rule_code else []),
                *_business_rule_lines(business_rule),
                f"Vấn đề: {alert.message}",
                f"Xác nhận bởi: {actor_name}",
                f"Ghi chú: {alert.resolution_note or '—'}",
                f"Thời gian xác nhận: {format_display_time(alert.resolved_at)}",
            ]
        )

    value = alert.trigger_value if observed_value is None else observed_value
    event_time = observed_at or alert.last_triggered_at or alert.started_at
    lower = sensor.lower_threshold if sensor is not None else None
    upper = sensor.upper_threshold if sensor is not None else None
    unit = sensor_model.unit if sensor_model is not None else ""

    if alert.alert_type == AlertType.ABOVE_UPPER_THRESHOLD and upper is not None and value is not None:
        threshold = f"Ngưỡng tối đa: {_number(upper)} {unit}".strip()
        state = f"Cao hơn ngưỡng: +{_number(value - upper)} {unit}".strip()
    elif alert.alert_type == AlertType.BELOW_LOWER_THRESHOLD and lower is not None and value is not None:
        threshold = f"Ngưỡng tối thiểu: {_number(lower)} {unit}".strip()
        state = f"Thấp hơn ngưỡng: -{_number(lower - value)} {unit}".strip()
    else:
        threshold = f"Ngưỡng cho phép: {_number(lower)} – {_number(upper)} {unit}".strip()
        state = str(alert.message)

    recovered = transition == "RECOVERED"
    return "\n".join(
        [
            _risk_heading(business_rule, recovered=recovered),
            "",
            f"Dự án: {project_label}",
            f"Mức độ: {risk_label}",
            f"Thiết bị: {device_name}",
            f"Cảm biến: {display_sensor_name}",
            *([f"Mã quy tắc: {resolved_rule_code}"] if resolved_rule_code else []),
            *_business_rule_lines(business_rule),
            f"Giá trị hiện tại: {_number(value)} {unit}".strip(),
            threshold,
            state,
            f"Thời gian: {format_display_time(event_time)}",
        ]
    )


async def dispatch_alert_transition(
    db: AsyncSession,
    *,
    alert_id: int,
    transition: str,
    notifier: Notifier | None = None,
    observed_value: float | None = None,
    observed_at: datetime | None = None,
    occurrence_count: int | None = None,
    previous_severity: str | None = None,
    business_rule_code: str | None = None,
) -> None:
    """Dispatch a sensor notification once per business incident transition.

    Hard anti-spam rules for V1:
    - OPENED is sent only for the first occurrence of an incident.
    - ABNORMAL_READING is never a Telegram event.
    - WARNING/CRITICAL changes never create extra Telegram messages.
    - RECOVERED/RESOLVED_CONFIRMED remain lifecycle events.

    This deliberately protects Telegram even if an upstream caller mistakenly
    emits OPENED for every abnormal telemetry sample.
    """
    if transition not in {"OPENED", "ABNORMAL_READING", "RESOLVED_CONFIRMED", "RECOVERED"}:
        logger.warning(
            "event=telegram_alert_skipped alert_id=%s reason=unsupported_transition transition=%s",
            alert_id,
            transition,
        )
        return

    # A raw abnormal telemetry sample is not a notification event, ever.
    if transition == "ABNORMAL_READING":
        logger.debug("event=telegram_alert_skipped alert_id=%s reason=abnormal_sample_not_event", alert_id)
        return

    notifier = notifier or TelegramNotifier()
    row = (
        await db.execute(
            select(SensorAlert, Sensor, SensorModel, Device, Project, ProjectNotificationSettings)
            .join(Sensor, Sensor.id == SensorAlert.sensor_id)
            .join(SensorModel, SensorModel.id == Sensor.sensor_model_id)
            .join(Device, Device.id == Sensor.device_id)
            .join(Project, Project.id == Device.project_id)
            .outerjoin(ProjectNotificationSettings, ProjectNotificationSettings.project_id == Project.id)
            .where(SensorAlert.id == alert_id)
        )
    ).first()
    if row is None:
        return

    alert, sensor, sensor_model, device, project, notification_settings = row
    if notification_settings is None or not notification_settings.telegram_enabled:
        return

    resolved_rule_code, business_rule = _resolve_sensor_business_rule(sensor_model.code, business_rule_code)

    # Only alerts with an explicit business-risk mapping are allowed onto
    # Telegram. This prevents generic Sensor lower/upper thresholds from
    # becoming business alerts by accident (e.g. ILLUMINANCE immediate low
    # threshold while Excel requires a multi-day condition).
    if business_rule is None:
        logger.info(
            "event=telegram_alert_skipped project_id=%s alert_id=%s sensor_model=%s reason=no_business_rule_mapping",
            project.id,
            alert.id,
            sensor_model.code,
        )
        return

    effective_count = occurrence_count if occurrence_count is not None else getattr(alert, "occurrence_count", None)
    if transition == "OPENED" and isinstance(effective_count, int) and effective_count > 1:
        logger.info(
            "event=telegram_alert_skipped project_id=%s alert_id=%s occurrence_count=%s reason=incident_already_open",
            project.id,
            alert.id,
            effective_count,
        )
        return

    if transition == "OPENED" and not notification_settings.notify_alert_opened:
        return
    if transition == "RECOVERED" and not notification_settings.notify_alert_recovered:
        return
    if transition == "RESOLVED_CONFIRMED" and not notification_settings.notify_alert_resolved:
        return
    if not notifier.configured:
        logger.info("event=telegram_skipped project_id=%s alert_id=%s reason=not_configured", project.id, alert.id)
        return

    recipients = list(
        (
            await db.scalars(
                select(ProjectNotificationRecipient).where(
                    ProjectNotificationRecipient.project_id == project.id,
                    ProjectNotificationRecipient.enabled.is_(True),
                )
            )
        ).all()
    )

    message = format_alert_message(
        transition=transition,
        project_name=project.name,
        project_code=project.code,
        alert=alert,
        sensor=sensor,
        sensor_model=sensor_model,
        device_name=device.name,
        observed_value=observed_value,
        observed_at=observed_at,
        occurrence_count=effective_count,
        previous_severity=previous_severity,
        business_rule_code=resolved_rule_code,
    )

    async def deliver(recipient: ProjectNotificationRecipient) -> None:
        try:
            result = await notifier.send_message(recipient.telegram_chat_id, message)
        except Exception:
            logger.exception(
                "event=telegram_delivery project_id=%s alert_id=%s recipient_id=%s sent=false error_category=UNEXPECTED",
                project.id,
                alert.id,
                recipient.id,
            )
            return
        logger.info(
            "event=telegram_delivery project_id=%s alert_id=%s recipient_id=%s sent=%s status_code=%s error_category=%s",
            project.id,
            alert.id,
            recipient.id,
            result.sent,
            result.status_code,
            result.error_category,
        )

    await asyncio.gather(*(deliver(recipient) for recipient in recipients), return_exceptions=True)


async def _dispatch_project_message(
    db: AsyncSession,
    *,
    project_id: int,
    message: str,
    event: str,
    notifier: Notifier | None = None,
) -> None:
    notifier = notifier or TelegramNotifier()
    notification_settings = await db.scalar(
        select(ProjectNotificationSettings).where(ProjectNotificationSettings.project_id == project_id)
    )
    if notification_settings is None or not notification_settings.telegram_enabled or not notifier.configured:
        return
    recipients = list(
        (
            await db.scalars(
                select(ProjectNotificationRecipient).where(
                    ProjectNotificationRecipient.project_id == project_id,
                    ProjectNotificationRecipient.enabled.is_(True),
                )
            )
        ).all()
    )

    async def deliver(recipient: ProjectNotificationRecipient) -> None:
        try:
            result = await notifier.send_message(recipient.telegram_chat_id, message)
            logger.info(
                "event=telegram_operational project_id=%s operation=%s recipient_id=%s sent=%s status_code=%s error_category=%s",
                project_id, event, recipient.id, result.sent, result.status_code, result.error_category,
            )
        except Exception:
            logger.exception(
                "event=telegram_operational project_id=%s operation=%s recipient_id=%s sent=false error_category=UNEXPECTED",
                project_id, event, recipient.id,
            )

    await asyncio.gather(*(deliver(recipient) for recipient in recipients), return_exceptions=True)


def _duration_text(started_at: datetime | None, ended_at: datetime) -> str:
    if started_at is None:
        return "Không xác định"
    seconds = max(0, int((ended_at - started_at).total_seconds()))
    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    parts = []
    if hours:
        parts.append(f"{hours} giờ")
    if minutes:
        parts.append(f"{minutes} phút")
    parts.append(f"{seconds} giây")
    return " ".join(parts)


async def _load_actuator_electrical_context(
    db: AsyncSession, *, actuator_id: int, feedback_role: str,
) -> dict[str, object] | None:
    """Load one explicit actuator feedback binding and its latest reading.

    The sensor may live on another Device, but it must belong to the same
    Project. This is deliberately a read model for notifications; it never
    creates a binding or evaluates an incident.
    """
    latest = (
        select(TelemetryReading.sensor_id, func.max(TelemetryReading.recorded_at).label("recorded_at"))
        .group_by(TelemetryReading.sensor_id).subquery()
    )
    parent_row = (await db.execute(
        select(Actuator, Device, Project)
        .join(Device, Device.id == Actuator.device_id)
        .join(Project, Project.id == Device.project_id)
        .where(Actuator.id == actuator_id)
    )).first()
    if parent_row is None:
        return None
    actuator, parent_device, project = parent_row
    binding = await db.scalar(select(ActuatorFeedbackBinding).where(
        ActuatorFeedbackBinding.actuator_id == actuator_id,
        ActuatorFeedbackBinding.feedback_role == feedback_role,
        ActuatorFeedbackBinding.is_enabled.is_(True),
    ))
    if binding is None:
        return {"configured": False, "actuator": actuator, "device": parent_device, "project": project}
    sensor_row = (
        await db.execute(
            select(Sensor, SensorModel, TelemetryReading)
            .join(SensorModel, SensorModel.id == Sensor.sensor_model_id)
            .join(Device, Device.id == Sensor.device_id)
            .outerjoin(latest, latest.c.sensor_id == Sensor.id)
            .outerjoin(TelemetryReading, and_(TelemetryReading.sensor_id == latest.c.sensor_id, TelemetryReading.recorded_at == latest.c.recorded_at))
            .where(Sensor.id == binding.sensor_id, Device.project_id == project.id)
        )
    ).first()
    if sensor_row is None:
        return {"configured": False, "actuator": actuator, "device": parent_device, "project": project}
    sensor, model, reading = sensor_row
    definition = await db.get(ActuatorModelFeedbackDefinition, binding.model_feedback_id) if binding.model_feedback_id else await db.scalar(select(ActuatorModelFeedbackDefinition).where(
        ActuatorModelFeedbackDefinition.actuator_model_id == actuator.actuator_model_id,
        ActuatorModelFeedbackDefinition.feedback_role == feedback_role,
        ActuatorModelFeedbackDefinition.is_enabled.is_(True),
    ))
    value = reading.value if reading else None
    quality, _, _, _ = classify_measurement_quality(model.code, value)
    freshness = "FRESH" if reading and reading.received_at and (datetime.now(UTC) - reading.received_at).total_seconds() <= settings.device_offline_seconds else "STALE" if reading else "NO_DATA"
    if freshness == "STALE" and quality == "VALID":
        quality = "STALE"
    return {
        "configured": True, "actuator": actuator, "device": parent_device,
        "project": project, "binding": binding, "sensor": sensor,
        "sensor_model": model, "definition": definition, "sensor_id": sensor.id,
        "sensor_code": sensor.code, "sensor_model_code": model.code, "value": value,
        "unit": binding.unit or model.unit, "quality": quality, "freshness": freshness,
        "recorded_at": reading.recorded_at if reading else None,
        "received_at": reading.received_at if reading else None,
        "lower_threshold": binding.lower_threshold if binding.lower_threshold is not None else definition.default_lower_threshold if definition else None,
        "upper_threshold": binding.upper_threshold if binding.upper_threshold is not None else definition.default_upper_threshold if definition else None,
    }


def _format_electrical_feedback(context: dict[str, object]) -> str:
    if not context.get("configured"):
        return "Chưa cấu hình"
    quality = str(context.get("quality") or "")
    if quality == "NO_DATA":
        return "Không có dữ liệu"
    if quality == "INVALID":
        return "Không hợp lệ"
    value = context.get("value")
    unit = str(context.get("unit") or "")
    result = f"{_number(value if isinstance(value, (int, float)) else None)} {unit}".strip()
    return f"{result} (Dữ liệu cũ)" if quality == "STALE" else result


def _threshold_status(value: object, lower: object, upper: object) -> str:
    if not isinstance(value, (int, float)):
        return "Không có dữ liệu mới."
    if isinstance(lower, (int, float)) and value < lower:
        return "Thấp hơn ngưỡng"
    if isinstance(upper, (int, float)) and value > upper:
        return "Cao hơn ngưỡng"
    return "Trong phạm vi"


async def dispatch_actuator_electrical_transition(
    db: AsyncSession, *, actuator_id: int, feedback_role: str, transition: str,
    notifier: Notifier | None = None, severity: str | None = None,
    business_risk_level: str | None = None, occurred_at: datetime | None = None,
    business_rule_code: str | None = None,
) -> None:
    if feedback_role not in {"RUNNING_CURRENT", "SUPPLY_VOLTAGE"} or transition not in {"OPENED", "ESCALATED", "RECOVERED", "RESOLVED", "REMINDER"}:
        return
    # V1 only exposes the Excel business risk level; technical severity
    # escalation is not a separate Telegram event.
    if transition == "ESCALATED":
        return
    context = await _load_actuator_electrical_context(db, actuator_id=actuator_id, feedback_role=feedback_role)
    if context is None or not context.get("configured"):
        return
    project = context["project"]
    if transition in {"OPENED", "ESCALATED", "REMINDER"} and _enum_value(context["device"].status) == "OFFLINE" and context.get("freshness") in {"STALE", "NO_DATA"}:
        return
    notification_settings = await db.scalar(select(ProjectNotificationSettings).where(ProjectNotificationSettings.project_id == project.id))
    if notification_settings is None or not notification_settings.telegram_enabled:
        return
    allowed = {"OPENED": notification_settings.notify_alert_opened, "ESCALATED": notification_settings.notify_alert_escalated, "RECOVERED": notification_settings.notify_alert_recovered, "RESOLVED": notification_settings.notify_alert_resolved, "REMINDER": notification_settings.notify_alert_reminder}[transition]
    if not allowed:
        return
    actuator_model = getattr(context["actuator"], "actuator_model", None)
    actuator_model_code = getattr(actuator_model, "code", None)
    resolved_rule_code, business_rule = _resolve_actuator_business_rule(
        actuator_model_code,
        feedback_role,
        business_rule_code,
    )
    # If caller already supplied business risk, keep it. Otherwise use the
    # Excel risk level for the resolved business rule.
    if business_risk_level is None and business_rule is not None:
        business_risk_level = str(business_rule.get("risk_level") or "") or None
    if business_risk_level is None:
        logger.info(
            "event=telegram_operational_skipped actuator_id=%s feedback_role=%s reason=no_business_risk",
            actuator_id, feedback_role,
        )
        return
    unit_label = "Dòng điện" if feedback_role == "RUNNING_CURRENT" else "Điện áp"
    heading = "🟢 THÔNG SỐ ĐIỆN ĐÃ TRỞ LẠI BÌNH THƯỜNG" if transition in {"RECOVERED", "RESOLVED"} else f"⚡ CẢNH BÁO {unit_label.upper()} CƠ CẤU CHẤP HÀNH"
    message = "\n".join([
        heading, "", f"Dự án: {project.name} ({project.code})",
        f"Thiết bị: {context['device'].name}", f"Cơ cấu chấp hành: {context['actuator'].name}",
        f"Model: {context['actuator'].actuator_model.name if context['actuator'].actuator_model else '—'}",
        *([f"Mã quy tắc: {resolved_rule_code}"] if resolved_rule_code else []),
        *_business_rule_lines(business_rule),
        f"Yêu cầu: {_state(context['actuator'].desired_state)}", f"Báo về: {_state(context['actuator'].reported_state)}",
        f"{unit_label} hiện tại: {_format_electrical_feedback(context)}",
        f"Ngưỡng dưới: {_number(context.get('lower_threshold'))} {context.get('unit') or ''}".strip(),
        f"Ngưỡng trên: {_number(context.get('upper_threshold'))} {context.get('unit') or ''}".strip(),
        f"Trạng thái: {_threshold_status(context.get('value'), context.get('lower_threshold'), context.get('upper_threshold'))}",
        f"Chất lượng dữ liệu: {QUALITY_LABELS.get(str(context.get('quality')), 'Chưa xác định')}",
        f"Thời gian đo: {format_display_time(context.get('recorded_at'))}",
        f"Thời gian nhận: {format_display_time(context.get('received_at'))}",
        f"Thời gian: {format_display_time(occurred_at or datetime.now(UTC))}",
        *( [f"Mức độ: {_label(RISK_LABELS, business_risk_level)}"] if business_risk_level and business_rule is None else [] ),
    ])
    await _dispatch_project_message(db, project_id=project.id, message=message, event=f"ACTUATOR_{feedback_role}_{transition}", notifier=notifier)


async def dispatch_device_connectivity_transition(
    db: AsyncSession,
    *,
    device_id: int,
    transition: str,
    disconnected_at: datetime | None = None,
    occurred_at: datetime | None = None,
    notifier: Notifier | None = None,
) -> None:
    occurred_at = occurred_at or datetime.now(UTC)
    row = (
        await db.execute(
            select(Device, Project).join(Project, Project.id == Device.project_id).where(Device.id == device_id)
        )
    ).first()
    if row is None:
        return
    device, project = row
    latest = (
        select(TelemetryReading.sensor_id, func.max(TelemetryReading.recorded_at).label("recorded_at"))
        .group_by(TelemetryReading.sensor_id)
        .subquery()
    )
    values = list(
        (
            await db.execute(
                select(Sensor, SensorModel, TelemetryReading)
                .join(SensorModel, SensorModel.id == Sensor.sensor_model_id)
                .outerjoin(latest, latest.c.sensor_id == Sensor.id)
                .outerjoin(
                    TelemetryReading,
                    (TelemetryReading.sensor_id == latest.c.sensor_id)
                    & (TelemetryReading.recorded_at == latest.c.recorded_at),
                )
                .where(
                    Sensor.device_id == device.id,
                    Sensor.is_enabled.is_(True),
                    Sensor.is_deleted.is_(False),
                    Sensor.deleted_at.is_(None),
                )
                .order_by(Sensor.id)
            )
        ).all()
    )
    actuators = list(
        (
            await db.scalars(
                select(Actuator)
                .where(
                    Actuator.device_id == device.id,
                    Actuator.is_enabled.is_(True),
                    Actuator.is_deleted.is_(False),
                    Actuator.removed_at.is_(None),
                )
                .order_by(Actuator.id)
            )
        ).all()
    )
    if transition == "DISCONNECTED":
        value_lines = [
            f"• {sensor.name}: {_number(reading.value) if reading else '—'} {model.unit}"
            for sensor, model, reading in values[: settings.telegram_device_sensor_limit]
        ]
        if len(values) > settings.telegram_device_sensor_limit:
            value_lines.append("• Xem Monitoring để xem đầy đủ.")
        message = "\n".join(
            [
                "🔌 THIẾT BỊ MẤT KẾT NỐI", "",
                f"Dự án: {project.name} ({project.code})",
                f"Thiết bị: {device.name}",
                "Trạng thái: Mất kết nối",
                f"Dữ liệu cuối: {format_display_time(device.last_seen_at)}",
                f"Ảnh hưởng: {len(values)} cảm biến không còn dữ liệu mới.",
                f"• {len(actuators)} cơ cấu chấp hành không thể xác nhận trạng thái mới.",
                "", "Giá trị cuối:", *value_lines,
                "", "Các giá trị trên là dữ liệu cuối trước khi mất kết nối.",
                "", "Cơ cấu chấp hành bị ảnh hưởng:",
                *(f"• {actuator.name} — trạng thái cuối: {_state(actuator.reported_state)}" for actuator in actuators),
                f"Phát hiện mất kết nối: {format_display_time(occurred_at)}",
            ]
        )
    elif transition == "RECONNECTED":
        message = "\n".join(
            [
                "🟢 THIẾT BỊ ĐÃ KẾT NỐI LẠI", "",
                f"Dự án: {project.name} ({project.code})",
                f"Thiết bị: {device.name}",
                f"Mất kết nối từ: {format_display_time(disconnected_at)}",
                f"Kết nối lại: {format_display_time(occurred_at)}",
                f"Thời gian gián đoạn: {_duration_text(disconnected_at, occurred_at)}",
                f"Khôi phục kết nối cho: {len(values)} cảm biến, {len(actuators)} cơ cấu chấp hành",
                "Có thể tiếp tục nhận dữ liệu và đồng bộ trạng thái.",
            ]
        )
    else:
        return
    await _dispatch_project_message(
        db, project_id=project.id, message=message, event=f"DEVICE_{transition}", notifier=notifier
    )


async def dispatch_actuator_command_transition(
    db: AsyncSession,
    *,
    command_id: int,
    transition: str,
    notifier: Notifier | None = None,
) -> None:
    row = (
        await db.execute(
            select(ActuatorCommand, Actuator, Device, Project, User)
            .join(Actuator, Actuator.id == ActuatorCommand.actuator_id)
            .join(Device, Device.id == Actuator.device_id)
            .join(Project, Project.id == Device.project_id)
            .join(User, User.id == ActuatorCommand.requested_by_user_id)
            .where(ActuatorCommand.id == command_id)
        )
    ).first()
    if row is None:
        return
    command, actuator, device, project, actor = row
    desired = _state(command.desired_state)
    reported = _state(command.reported_state)
    if transition == "ACKNOWLEDGED":
        if not settings.telegram_notify_actuator_ack:
            return
        heading = "🟢 LỆNH ĐÃ ĐƯỢC XÁC NHẬN"
        detail = "Thiết bị đã xác nhận trạng thái yêu cầu."
        event_time = command.acknowledged_at
    elif transition in {"FAILED", "TIMEOUT"}:
        heading = "🔴 LỆNH ĐIỀU KHIỂN THẤT BẠI" if transition == "FAILED" else "🔴 LỆNH ĐIỀU KHIỂN HẾT THỜI GIAN CHỜ"
        detail = f"Không thể xác nhận thiết bị đã chuyển sang {desired}."
        event_time = command.failed_at or command.timed_out_at
    else:
        return
    message = "\n".join(
        [
            heading, "", f"Dự án: {project.name} ({project.code})",
            f"Cơ cấu chấp hành: {actuator.name}", f"Yêu cầu: {desired}",
            f"Trạng thái cuối nhận được: {reported}", detail,
            f"Thiết bị điều khiển: {device.name}",
            *(["Thiết bị điều khiển hiện mất kết nối."] if _enum_value(device.status) == "OFFLINE" else []),
            f"Model: {actuator.actuator_model.name if actuator.actuator_model else '—'}",
            f"Người thực hiện: {actor.full_name or actor.username}",
            f"Thời gian: {format_display_time(event_time)}",
        ]
    )
    await _dispatch_project_message(
        db, project_id=project.id, message=message, event=f"ACTUATOR_{transition}", notifier=notifier
    )


async def dispatch_business_rule_transition(
    db: AsyncSession,
    *,
    project_id: int,
    business_rule_code: str,
    transition: str,
    target_name: str | None = None,
    detail_lines: list[str] | None = None,
    occurred_at: datetime | None = None,
    notifier: Notifier | None = None,
) -> None:
    """Send a notification for one of the 19 Excel business rules.

    This is intentionally a notification-only entry point for the V1 hard-coded
    evaluator. It does not evaluate thresholds or create incidents.
    """
    if transition not in {"OPENED", "ESCALATED", "REMINDER", "RECOVERED", "RESOLVED"}:
        return
    rule = get_business_alert_rule(business_rule_code)
    if rule is None:
        logger.warning(
            "event=telegram_business_rule_skipped project_id=%s rule=%s reason=unknown_rule",
            project_id,
            business_rule_code,
        )
        return
    project = await db.get(Project, project_id)
    if project is None:
        return
    heading = {
        "OPENED": "🚨 CẢNH BÁO NGHIỆP VỤ",
        "ESCALATED": "🔴 MỨC CẢNH BÁO ĐÃ TĂNG",
        "REMINDER": "⏰ NHẮC LẠI CẢNH BÁO",
        "RECOVERED": "🟢 ĐIỀU KIỆN ĐÃ TRỞ LẠI BÌNH THƯỜNG",
        "RESOLVED": "✅ CẢNH BÁO ĐÃ ĐƯỢC XỬ LÝ",
    }[transition]
    message = "\n".join(
        [
            heading,
            "",
            f"Dự án: {project.name} ({project.code})",
            f"Mã quy tắc: {business_rule_code}",
            *([f"Đối tượng: {target_name}"] if target_name else []),
            *_business_rule_lines(rule),
            *(detail_lines or []),
            f"Thời gian: {format_display_time(occurred_at or datetime.now(UTC))}",
        ]
    )
    await _dispatch_project_message(
        db,
        project_id=project.id,
        message=message,
        event=f"BUSINESS_RULE_{business_rule_code}_{transition}",
        notifier=notifier,
    )


async def dispatch_project_health_message(
    db: AsyncSession,
    *,
    project_id: int,
    message: str,
    notifier: Notifier | None = None,
) -> None:
    await _dispatch_project_message(
        db, project_id=project_id, message=message, event="PROJECT_HEALTH", notifier=notifier
    )
