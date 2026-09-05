import asyncio
import logging
import signal

import paho.mqtt.client as mqtt

from app.core.config import settings
from app.mqtt.handlers import handle_command_ack, handle_status, handle_telemetry
from app.mqtt.topics import parse_topic

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def main() -> None:
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=settings.mqtt_client_id)

    def on_connect(client: mqtt.Client, _userdata: object, _flags: object, reason_code: object, _properties: object) -> None:
        if getattr(reason_code, "is_failure", False):
            logger.error("Không thể kết nối MQTT reason_code=%s", reason_code)
            return
        client.subscribe([(settings.mqtt_telemetry_topic, 0), (settings.mqtt_status_topic, 0), (settings.mqtt_ack_topic, 0)])
        logger.info("Đã subscribe MQTT telemetry, status và command-ack")

    def on_message(_client: mqtt.Client, _userdata: object, message: mqtt.MQTTMessage) -> None:
        parsed = parse_topic(message.topic)
        if parsed is None:
            logger.warning("Bỏ qua MQTT topic không hợp lệ topic=%s", message.topic)
            return
        device_code, kind = parsed
        handler = handle_telemetry if kind == "telemetry" else handle_command_ack if kind == "command-ack" else handle_status
        future = asyncio.run_coroutine_threadsafe(handler(device_code, message.payload), loop)
        future.add_done_callback(lambda item: logger.exception("MQTT handler lỗi", exc_info=item.exception()) if item.exception() else None)

    client.on_connect = on_connect
    client.on_message = on_message
    client.connect_async(settings.mqtt_host, settings.mqtt_port, keepalive=60)
    client.loop_start()
    stop = asyncio.Event()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, stop.set)
    try:
        loop.run_until_complete(stop.wait())
    finally:
        client.disconnect()
        client.loop_stop()
        loop.close()


if __name__ == "__main__":
    main()
