from datetime import UTC, datetime

from app.models.alert import SensorAlert
from app.models.sensor import Sensor, SensorModel
from app.services.project_notification_service import (
    ACTUATOR_MODEL_DISPLAY,
    SENSOR_MODEL_DISPLAY,
    _format_electrical_feedback,
    _threshold_status,
    format_alert_message,
)


def test_catalog_and_electrical_states_are_semantic_and_not_zero_filled() -> None:
    assert SENSOR_MODEL_DISPLAY["TDS_01"] == ("Tổng chất rắn hòa tan", "ppm")
    assert ACTUATOR_MODEL_DISPLAY["FISH_TANK_PUMP"] == "Bơm hút bể cá"
    assert _format_electrical_feedback({"configured": False}) == "Chưa cấu hình"
    assert _format_electrical_feedback({"configured": True, "quality": "NO_DATA", "value": None}) == "Không có dữ liệu"
    assert _format_electrical_feedback({"configured": True, "quality": "VALID", "value": 0, "unit": "A"}) == "0 A"
    assert _format_electrical_feedback({"configured": True, "quality": "STALE", "value": 0.12, "unit": "A"}) == "0.12 A (Dữ liệu cũ)"
    assert _threshold_status(None, 0.3, 2.0) == "Không có dữ liệu mới."


def test_sensor_alert_uses_vietnamese_severity_and_escalation_heading() -> None:
    now = datetime(2026, 8, 27, tzinfo=UTC)
    sensor = Sensor(id=1, device_id=1, sensor_model_id=1, code="PH", name="pH", lower_threshold=6.5, upper_threshold=8.5)
    model = SensorModel(id=1, code="PH", name="pH", unit="pH")
    alert = SensorAlert(id=1, sensor_id=1, message="Vượt ngưỡng", trigger_value=9.0, started_at=now, severity="CRITICAL")
    message = format_alert_message(
        transition="OPENED", project_name="Dự án", project_code="P1", alert=alert,
        device_name="Thiết bị", sensor=sensor, sensor_model=model,
        previous_severity="WARNING", observed_at=now,
    )
    assert "🚨 CẢNH BÁO MỨC RẤT CAO" in message
    assert "Mức độ: Rất cao" in message
    assert "WARNING" not in message
    assert "CRITICAL" not in message
    assert "9 pH" in message
