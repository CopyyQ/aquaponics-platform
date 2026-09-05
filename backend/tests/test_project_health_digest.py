from datetime import UTC, datetime
from types import SimpleNamespace

from app.jobs.project_health_evaluator import format_health_digest
from app.services.monitoring_service import _actuator_sync


def _snapshot() -> dict:
    return {
        "health": "WARNING",
        "devices": {"devices_online": 1, "devices_total": 2, "devices_offline": 1, "devices_waiting": 0, "sensors_reporting": 7, "sensors_stale": 1, "sensors_offline": 1},
        "device_issues": [{"name": "Energy Monitor", "code": "EM-01", "last_seen_at": "2026-08-27T02:00:00+00:00", "sensor_count": 6, "actuator_count": 0}],
        "sensor_issues": [{"name": "Điện áp đầu vào", "code": "EM-01-IN-V", "device_name": "Energy Monitor", "device_code": "EM-01", "freshness": "STALE", "value": 12.2, "unit": "V", "recorded_at": "2026-08-27T02:00:00+00:00", "received_at": "2026-08-27T02:00:01+00:00"}],
        "actuators": {"responding": 2, "out_of_sync": 1, "failed": 0},
        "actuator_issues": [{"name": "Máy sủi oxy 01", "code": "AERATOR-01", "device_name": "Bộ điều khiển", "device_code": "CTRL-01", "desired_state": False, "reported_state": True, "synchronization_status": "OUT_OF_SYNC", "command_status": "ACKNOWLEDGED", "last_reported_at": "2026-08-27T02:00:00+00:00", "electrical": {}}],
        "business_alerts": {"counts": {"EXTREME": 1, "VERY_HIGH": 2, "HIGH": 3, "MEDIUM": 0, "LOW_MEDIUM": 0, "LOW": 0}, "items": [{"risk": "VERY_HIGH", "rule_name": "pH nước bất thường", "device_name": "Thiết bị môi trường", "device_code": "ENV-01", "sensor_name": "Cảm biến pH", "sensor_code": "ENV-01-PH", "value": 2, "unit": "pH", "condition": "Giá trị cảm biến nằm ngoài khoảng vận hành.", "started_at": "2026-08-27T01:00:00+00:00", "duration_seconds": 3600, "message": "pH bất thường, hãy kiểm tra môi trường nước.", "actuator_name": None}]},
    }


def test_actuator_sync_uses_state_not_historical_command() -> None:
    assert _actuator_sync(True, True, "TIMEOUT") == "IN_SYNC"
    assert _actuator_sync(False, True, None) == "OUT_OF_SYNC"


def test_health_digest_is_detailed_vietnamese_business_report() -> None:
    message = format_health_digest(SimpleNamespace(name="Dự án cá trê", code="TB-0015"), _snapshot(), datetime(2026, 8, 27, 3, tzinfo=UTC), False)
    assert "Cực cao: 1" in message
    assert "Rất cao: 2" in message
    assert "Cao: 3" in message
    assert "CRITICAL" not in message and "WARNING" not in message
    assert "True" not in message and "False" not in message
    assert "Yêu cầu: Tắt" in message and "Báo về: Bật" in message
    assert "Điện áp đầu vào" in message and "EM-01-IN-V" in message
    assert "Energy Monitor (EM-01)" in message
    assert "12,2 V" in message
    assert "Đo lần cuối:" in message and "Nhận lần cuối:" in message
