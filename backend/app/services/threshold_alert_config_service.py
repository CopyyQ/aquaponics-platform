from dataclasses import dataclass

from sqlalchemy import select
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.threshold_alert_config import ThresholdAlertConfig

DEFAULT_BELOW_RISK_LEVEL = "LOW"
DEFAULT_ABOVE_RISK_LEVEL = "HIGH"


@dataclass(frozen=True)
class ThresholdEvaluation:
    state: str
    threshold: float | None = None
    risk_level: str | None = None
    message: str | None = None


def evaluate_threshold(value: float | None, config: ThresholdAlertConfig | None) -> ThresholdEvaluation:
    """Evaluate only the canonical ThresholdAlertConfig runtime authority."""
    if config is None or not config.enabled or (config.lower_threshold is None and config.upper_threshold is None):
        return ThresholdEvaluation("UNCONFIGURED")
    if value is None:
        return ThresholdEvaluation("NO_DATA")
    if config.lower_threshold is not None and value < config.lower_threshold:
        return ThresholdEvaluation("BELOW", config.lower_threshold, config.below_risk_level, config.below_message)
    if config.upper_threshold is not None and value > config.upper_threshold:
        return ThresholdEvaluation("ABOVE", config.upper_threshold, config.above_risk_level, config.above_message)
    return ThresholdEvaluation("NORMAL")


async def get_sensor_threshold_alert_config(db: AsyncSession, sensor_id: int) -> ThresholdAlertConfig | None:
    return await db.scalar(select(ThresholdAlertConfig).where(
        ThresholdAlertConfig.sensor_id == sensor_id,
        ThresholdAlertConfig.metric_type == "SENSOR_VALUE",
    ))


async def get_actuator_threshold_alert_config(db: AsyncSession, actuator_id: int, metric_type: str) -> ThresholdAlertConfig | None:
    return await db.scalar(select(ThresholdAlertConfig).where(
        ThresholdAlertConfig.actuator_id == actuator_id,
        ThresholdAlertConfig.metric_type == metric_type,
    ))


def ensure_threshold_delivery_defaults(config: ThresholdAlertConfig) -> None:
    """Never leave a configured bound unable to open an incident.

    The FE historically displayed LOW/HIGH as the defaults even when the
    underlying form state was null.  Canonical runtime delivery requires an
    explicit risk on the matching direction, so materialize those defaults.
    """
    if config.lower_threshold is not None and config.below_risk_level is None:
        config.below_risk_level = DEFAULT_BELOW_RISK_LEVEL
    if config.upper_threshold is not None and config.above_risk_level is None:
        config.above_risk_level = DEFAULT_ABOVE_RISK_LEVEL


def apply_threshold_alert_config_update(config: ThresholdAlertConfig, values: dict[str, object]) -> None:
    lower = values.get("lower_threshold", config.lower_threshold)
    upper = values.get("upper_threshold", config.upper_threshold)
    if lower is not None and upper is not None and float(lower) > float(upper):
        raise HTTPException(status_code=422, detail="Ngưỡng dưới không được lớn hơn ngưỡng trên")
    for field, value in values.items():
        setattr(config, field, value)
    ensure_threshold_delivery_defaults(config)
