"""Operator-facing content catalog derived from the Telegram workbook.

The catalog contains meaning and response guidance only. It deliberately has
no numeric Sensor threshold fields; runtime thresholds belong exclusively to
ThresholdAlertConfig.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class AlertMessage:
    condition_key: str
    title: str
    consequence: str
    recommended_actions: tuple[str, ...]
    version: int = 1


CATALOG: dict[str, AlertMessage] = {
    "ACTUATOR_ON_NO_LOAD": AlertMessage(
        "ACTUATOR_ON_NO_LOAD", "Có điện nhưng tải có khả năng không hoạt động",
        "Thiết bị được báo Bật và có điện áp gần định mức nhưng dòng tải quá thấp; chức năng vận hành có khả năng đã dừng.",
        ("Hãy xác minh trạng thái thực tế của tải.", "Kiểm tra giắc cắm, dây dẫn và kết nối tải.", "Kiểm tra kẹt cơ khí hoặc hỏng tải; cô lập nguồn trước khi thao tác điện."),
    ),
    "ACTUATOR_ON_NO_POWER": AlertMessage(
        "ACTUATOR_ON_NO_POWER", "Thiết bị đang Bật nhưng không có nguồn tải",
        "Thiết bị được yêu cầu Bật nhưng điện áp và dòng điện gần bằng không; nguồn, relay, driver hoặc dây dẫn có khả năng gặp sự cố.",
        ("Hãy xác minh trạng thái và nguồn cấp tại vị trí an toàn.", "Kiểm tra relay/driver, bảo vệ nguồn và dây dẫn.", "Cô lập nguồn trước khi kiểm tra phần điện; liên hệ kỹ thuật nếu chưa xác định nguyên nhân."),
    ),
}

# Wording may vary by Actuator type, but this never changes the semantic
# condition selected by the single composite evaluator.
ACTUATOR_TITLES: dict[tuple[str, str], str] = {
    ("ACTUATOR_ON_NO_POWER", "AIR_PUMP"): "Máy sủi đang được bật nhưng không có nguồn điện",
    ("ACTUATOR_ON_NO_LOAD", "AIR_PUMP"): "Máy sủi có điện nhưng tải có khả năng không hoạt động",
    ("ACTUATOR_ON_NO_POWER", "FISH_TANK_PUMP"): "Bơm bể cá đang được bật nhưng không có nguồn điện",
    ("ACTUATOR_ON_NO_LOAD", "FISH_TANK_PUMP"): "Bơm bể cá có điện nhưng tải có khả năng không hoạt động",
    ("ACTUATOR_ON_NO_POWER", "IRRIGATION_PUMP"): "Bơm tưới đang được bật nhưng không có nguồn điện",
    ("ACTUATOR_ON_NO_LOAD", "IRRIGATION_PUMP"): "Bơm tưới có điện nhưng tải có khả năng không hoạt động",
}


def sensor_condition_key(model_code: str, direction: str) -> str:
    code = model_code.upper()
    if code == "PH":
        return "SENSOR_PH_LOW" if direction == "BELOW" else "SENSOR_PH_HIGH"
    if code in {"TEMP", "WATER_TEMPERATURE"} and direction == "ABOVE":
        return "SENSOR_WATER_TEMPERATURE_HIGH"
    if code == "TDS" and direction == "BELOW":
        return "SENSOR_TDS_LOW"
    if code == "WATER_LEVEL" and direction == "BELOW":
        return "SENSOR_WATER_LEVEL_LOW"
    return "SENSOR_THRESHOLD_LOW" if direction == "BELOW" else "SENSOR_THRESHOLD_HIGH"


def catalog_snapshot(condition_key: str) -> dict[str, object]:
    if condition_key.startswith("SENSOR_"):
        return {
            "condition_key": condition_key,
            "title": (
                "Giá trị thấp hơn ngưỡng dưới"
                if condition_key.endswith("LOW")
                else "Giá trị vượt ngưỡng trên"
            ),
            "catalog_version": 1,
        }
    item = CATALOG[condition_key]
    return {
        "condition_key": item.condition_key,
        "title": item.title,
        "consequence": item.consequence,
        "recommended_actions": list(item.recommended_actions),
        "catalog_version": item.version,
    }


def actuator_catalog_snapshot(condition_key: str, model_code: str | None) -> dict[str, object]:
    snapshot = catalog_snapshot(condition_key)
    title = ACTUATOR_TITLES.get((condition_key, (model_code or "").upper()))
    if title:
        snapshot["title"] = title
    return snapshot
