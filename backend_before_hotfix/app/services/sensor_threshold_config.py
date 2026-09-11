"""Canonical Sensor threshold resolution and evaluation.

Runtime Sensors are materialized from their template/model defaults at
provisioning.  For legacy or partially configured Sensors, the resolver keeps
the same explicit-``None`` fallback semantics without treating numeric zero as
missing.
"""
from __future__ import annotations

from dataclasses import dataclass

from app.models.device_template import DeviceTemplateSensor
from app.models.sensor import Sensor
from app.models.sensor_model import SensorModel


@dataclass(frozen=True)
class ResolvedSensorThresholdConfig:
    alerts_enabled: bool
    lower_threshold: float | None
    upper_threshold: float | None
    below_threshold_message: str | None
    above_threshold_message: str | None
    below_risk_level: str | None
    above_risk_level: str | None
    delay_seconds: int
    lower_source: str
    upper_source: str


@dataclass(frozen=True)
class SensorThresholdEvaluation:
    state: str  # BELOW, NORMAL, ABOVE, UNCONFIGURED
    message: str | None
    threshold: float | None
    risk_level: str | None


def _resolve(instance: object, template: object | None, model: object, field: str) -> tuple[object | None, str]:
    value = getattr(instance, field)
    if value is not None:
        return value, "SENSOR"
    template_field = f"default_{field}"
    if template is not None and getattr(template, template_field) is not None:
        return getattr(template, template_field), "DEVICE_TEMPLATE"
    return getattr(model, template_field, getattr(model, "default_alert_risk_level", None)), "SENSOR_MODEL"


def resolve_sensor_threshold_config(
    sensor: Sensor, sensor_model: SensorModel, template_sensor: DeviceTemplateSensor | None = None
) -> ResolvedSensorThresholdConfig:
    lower, lower_source = _resolve(sensor, template_sensor, sensor_model, "lower_threshold")
    upper, upper_source = _resolve(sensor, template_sensor, sensor_model, "upper_threshold")
    # alerts_enabled is non-null on a materialized Sensor, so it remains the
    # runtime authority; defaults apply only to incomplete legacy instances.
    enabled = sensor.alerts_enabled if sensor.alerts_enabled is not None else (
        template_sensor.default_alerts_enabled if template_sensor and template_sensor.default_alerts_enabled is not None else sensor_model.default_warning_enabled
    )
    below, _ = _resolve(sensor, template_sensor, sensor_model, "below_threshold_message")
    above, _ = _resolve(sensor, template_sensor, sensor_model, "above_threshold_message")
    below_risk, _ = _resolve(sensor, template_sensor, sensor_model, "below_risk_level")
    above_risk, _ = _resolve(sensor, template_sensor, sensor_model, "above_risk_level")
    return ResolvedSensorThresholdConfig(bool(enabled), lower, upper, below, above, below_risk, above_risk, sensor.alert_delay_seconds, lower_source, upper_source)


def evaluate_sensor_threshold(value: float | None, config: ResolvedSensorThresholdConfig) -> SensorThresholdEvaluation:
    if not config.alerts_enabled or (config.lower_threshold is None and config.upper_threshold is None):
        return SensorThresholdEvaluation("UNCONFIGURED", None, None, None)
    if value is None:
        return SensorThresholdEvaluation("UNCONFIGURED", None, None, None)
    if config.lower_threshold is not None and value < config.lower_threshold:
        return SensorThresholdEvaluation("BELOW", config.below_threshold_message, config.lower_threshold, config.below_risk_level)
    if config.upper_threshold is not None and value > config.upper_threshold:
        return SensorThresholdEvaluation("ABOVE", config.above_threshold_message, config.upper_threshold, config.above_risk_level)
    return SensorThresholdEvaluation("NORMAL", None, None, None)
