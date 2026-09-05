from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class SensorValueRange:
    minimum: float
    maximum: float


SENSOR_VALUE_RANGES: dict[str, SensorValueRange] = {
    "AIR_HUMIDITY": SensorValueRange(minimum=0.0, maximum=100.0),
    "AIR_TEMPERATURE": SensorValueRange(minimum=-50.0, maximum=100.0),
    "AIR_PRESSURE": SensorValueRange(minimum=300.0, maximum=1_200.0),
    "ILLUMINANCE": SensorValueRange(minimum=0.0, maximum=200_000.0),
}


def validate_sensor_value(model_code: str, value: float) -> str | None:
    valid_range = SENSOR_VALUE_RANGES.get(model_code)
    if valid_range is None:
        return None
    if value < valid_range.minimum or value > valid_range.maximum:
        return (
            f"Giá trị ngoài phạm vi kỹ thuật "
            f"{valid_range.minimum:g}–{valid_range.maximum:g}"
        )
    return None
