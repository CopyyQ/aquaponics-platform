import json

import pytest
from pydantic import ValidationError

from app.mqtt.schemas import (
    MqttCommandAckPayload,
    MqttStatusPayload,
    MqttTelemetryPayload,
)
from app.mqtt.topics import parse_topic


def test_mqtt_topics_only_expose_device_code() -> None:
    assert parse_topic("aquaponics/DEVICE-001/telemetry") == ("DEVICE-001", "telemetry")
    assert parse_topic("aquaponics/DEVICE-001/status") == ("DEVICE-001", "status")
    assert parse_topic("aquaponics/12/99/telemetry") is None


def test_telemetry_payload_does_not_need_project_or_database_ids() -> None:
    payload = MqttTelemetryPayload.model_validate_json(json.dumps({
        "sent_at": "2026-07-21T03:00:00Z",
        "readings": [{"sensor_code": "PH-01", "value": 7.2, "recorded_at": "2026-07-21T03:00:00Z"}],
    }))
    assert payload.readings[0].sensor_code == "PH-01"
    assert "project_id" not in payload.model_dump()


def test_mqtt_payload_requires_recorded_at() -> None:
    with pytest.raises(ValidationError):
        MqttTelemetryPayload.model_validate({"sent_at": "2026-07-21T03:00:00Z", "readings": [{"sensor_code": "PH-01", "value": 7.2}]})


@pytest.mark.parametrize("value", [float("nan"), float("inf"), float("-inf")])
def test_mqtt_payload_rejects_non_finite_readings(value: float) -> None:
    with pytest.raises(ValidationError):
        MqttTelemetryPayload.model_validate(
            {
                "sent_at": "2026-07-21T03:00:00Z",
                "readings": [
                    {
                        "sensor_code": "ENV-01",
                        "value": value,
                        "recorded_at": "2026-07-21T03:00:00Z",
                    }
                ],
            }
        )


def test_status_payload_is_limited_to_online_or_offline() -> None:
    payload = {"status": "ONLINE", "sent_at": "2026-07-21T03:00:00Z", "actuators": []}
    assert MqttStatusPayload.model_validate(payload).status == "ONLINE"
    assert MqttStatusPayload.model_validate({**payload, "status": "online"}).status == "ONLINE"
    with pytest.raises(ValidationError):
        MqttStatusPayload.model_validate({**payload, "status": "disabled"})
    with pytest.raises(ValidationError):
        MqttStatusPayload.model_validate(
            {"status": "ONLINE", "sent_at": "2026-07-21T03:00:00Z"}
        )


def test_command_ack_requires_complete_contract() -> None:
    payload = MqttCommandAckPayload.model_validate(
        {
            "command_id": 12,
            "actuator_code": "PUMP-01",
            "reported_state": True,
            "status": "ACKNOWLEDGED",
            "sent_at": "2026-07-21T03:00:02Z",
        }
    )
    assert payload.status == "ACKNOWLEDGED"
    with pytest.raises(ValidationError):
        MqttCommandAckPayload.model_validate(
            {
                "command_id": 12,
                "actuator_code": "PUMP-01",
                "reported_state": True,
                "status": "ACKNOWLEDGED",
            }
        )
