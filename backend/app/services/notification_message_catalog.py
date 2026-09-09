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
    "SENSOR_WATER_LEVEL_LOW": AlertMessage(
        "SENSOR_WATER_LEVEL_LOW",
        "Mức nước thấp hơn ngưỡng vận hành",
        "Mực nước thấp có khả năng làm gián đoạn tuần hoàn và ảnh hưởng cá, cây hoặc hệ vi sinh nếu kéo dài.",
        ("Hãy xác minh số đo và mực nước thực tế.", "Kiểm tra bơm, van cấp nước và tình trạng tắc nghẽn.", "Kiểm tra đường ống và các điểm có khả năng rò rỉ."),
    ),
    "SENSOR_PH_HIGH": AlertMessage(
        "SENSOR_PH_HIGH",
        "pH vượt ngưỡng trên",
        "pH cao có khả năng làm cá và cây giảm hấp thu dinh dưỡng và gây mất ổn định môi trường nước.",
        ("Hãy xác minh phép đo bằng thiết bị đối chứng nếu có.", "Kiểm tra nguồn nước và vật thể lạ trong bể.", "Điều chỉnh pH từ từ theo quy trình vận hành rồi đo lại; tránh thay đổi đột ngột."),
    ),
    "SENSOR_PH_LOW": AlertMessage(
        "SENSOR_PH_LOW",
        "pH thấp hơn ngưỡng dưới",
        "pH thấp có khả năng ức chế hệ vi sinh, ảnh hưởng cá và khả năng hấp thu dinh dưỡng của cây.",
        ("Hãy xác minh phép đo bằng thiết bị đối chứng nếu có.", "Kiểm tra nguồn nước và vật thể lạ trong bể.", "Điều chỉnh pH từ từ theo quy trình vận hành rồi đo lại; tránh thay đổi đột ngột."),
    ),
    "SENSOR_WATER_TEMPERATURE_HIGH": AlertMessage(
        "SENSOR_WATER_TEMPERATURE_HIGH",
        "Nhiệt độ nước vượt ngưỡng trên",
        "Nhiệt độ nước cao có khả năng làm giảm oxy hòa tan, gây stress cho cá và ảnh hưởng hệ vi sinh.",
        ("Hãy xác minh nhiệt độ tại bể.", "Che nắng trực tiếp và kiểm tra tuần hoàn, sục khí.", "Hạ nhiệt từ từ; tránh thay đổi nhiệt độ đột ngột."),
    ),
    "SENSOR_TDS_LOW": AlertMessage(
        "SENSOR_TDS_LOW",
        "TDS thấp hơn ngưỡng dưới",
        "TDS thấp có khả năng cho thấy dinh dưỡng hòa tan chưa đáp ứng nhu cầu của cây.",
        ("Hãy xác minh đầu dò và phép đo.", "Kiểm tra tương quan sinh khối cá và số lượng cây.", "Kiểm tra quy trình bổ sung dinh dưỡng/vi sinh theo hướng dẫn của hệ thống."),
    ),
    "SENSOR_THRESHOLD_LOW": AlertMessage(
        "SENSOR_THRESHOLD_LOW", "Giá trị thấp hơn ngưỡng dưới",
        "Chỉ số nằm ngoài khoảng vận hành đã cấu hình.",
        ("Hãy xác minh số đo.", "Kiểm tra thiết bị đo và điều kiện vận hành liên quan."),
    ),
    "SENSOR_THRESHOLD_HIGH": AlertMessage(
        "SENSOR_THRESHOLD_HIGH", "Giá trị vượt ngưỡng trên",
        "Chỉ số nằm ngoài khoảng vận hành đã cấu hình.",
        ("Hãy xác minh số đo.", "Kiểm tra thiết bị đo và điều kiện vận hành liên quan."),
    ),
    "ACTUATOR_ON_NO_LOAD": AlertMessage(
        "ACTUATOR_ON_NO_LOAD", "Có điện nhưng tải có khả năng không hoạt động",
        "Thiết bị được báo Bật và có điện áp gần định mức nhưng dòng tải quá thấp; chức năng vận hành có khả năng đã dừng.",
        ("Hãy xác minh trạng thái thực tế của tải.", "Kiểm tra giắc cắm, dây dẫn và kết nối tải.", "Kiểm tra kẹt cơ khí hoặc hỏng tải; cô lập nguồn trước khi thao tác điện."),
    ),
    "ACTUATOR_NO_POWER": AlertMessage(
        "ACTUATOR_NO_POWER", "Thiết bị đang Bật nhưng không có nguồn tải",
        "Thiết bị được yêu cầu Bật nhưng điện áp và dòng điện gần bằng không; nguồn, relay, driver hoặc dây dẫn có khả năng gặp sự cố.",
        ("Hãy xác minh trạng thái và nguồn cấp tại vị trí an toàn.", "Kiểm tra relay/driver, bảo vệ nguồn và dây dẫn.", "Cô lập nguồn trước khi kiểm tra phần điện; liên hệ kỹ thuật nếu chưa xác định nguyên nhân."),
    ),
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
    item = CATALOG[condition_key]
    return {
        "condition_key": item.condition_key,
        "title": item.title,
        "consequence": item.consequence,
        "recommended_actions": list(item.recommended_actions),
        "catalog_version": item.version,
    }

