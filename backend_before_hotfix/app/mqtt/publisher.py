import json
import logging
import paho.mqtt.publish as mqtt_publish

from app.core.config import settings

logger = logging.getLogger(__name__)


def publish_actuator_command(device_code: str, command_id: int, actuator_code: str, desired_state: bool, requested_at: str) -> None:
    topic = settings.mqtt_command_topic.format(device_code=device_code)
    payload = json.dumps({
        "command_id": str(command_id),
        "actuator_code": actuator_code,
        "desired_state": desired_state,
        "requested_at": requested_at,
    })
    mqtt_publish.single(topic, payload=payload, hostname=settings.mqtt_host, port=settings.mqtt_port, qos=0, retain=False)
    logger.info("event=actuator_command_published command_id=%s device_code=%s actuator_code=%s desired_state=%s", command_id, device_code, actuator_code, desired_state)
