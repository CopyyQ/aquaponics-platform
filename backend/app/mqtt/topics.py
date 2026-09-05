import re


TOPIC_PATTERN = re.compile(r"^aquaponics/(?P<device_code>[A-Z0-9_-]+)/(telemetry|status|command-ack)$")


def parse_topic(topic: str) -> tuple[str, str] | None:
    match = TOPIC_PATTERN.fullmatch(topic)
    if match is None:
        return None
    return match.group("device_code"), topic.rsplit("/", 1)[-1]
