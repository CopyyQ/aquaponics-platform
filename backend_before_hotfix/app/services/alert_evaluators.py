from __future__ import annotations

from dataclasses import dataclass
from itertools import pairwise
from statistics import median
from typing import Any, Protocol


@dataclass(frozen=True)
class EvaluationResult:
    active: bool
    severity: str | None = None
    reason: str | None = None
    evidence: dict[str, Any] | None = None


class Evaluator(Protocol):
    required_fields: tuple[str, ...]

    def validate(self, config: dict[str, Any]) -> list[str]: ...
    def evaluate(self, config: dict[str, Any], context: dict[str, Any]) -> EvaluationResult: ...


class BaseEvaluator:
    required_fields: tuple[str, ...] = ()

    def validate(self, config: dict[str, Any]) -> list[str]:
        return [field for field in self.required_fields if config.get(field) is None]


def _compare(operator: str, observed: float, threshold: float) -> bool:
    return {"LT": observed < threshold, "LTE": observed <= threshold, "GT": observed > threshold, "GTE": observed >= threshold, "EQ": observed == threshold}.get(operator, False)


def _valid_values(context: dict[str, Any]) -> list[float]:
    values: list[float] = []
    for sample in context.get("samples") or []:
        value = sample.get("value") if isinstance(sample, dict) else sample
        quality = sample.get("quality", "VALID") if isinstance(sample, dict) else "VALID"
        if value is not None and quality == "VALID":
            values.append(float(value))
    return values


class ThresholdEvaluator(BaseEvaluator):
    required_fields = ("operator", "value")

    def evaluate(self, config: dict[str, Any], context: dict[str, Any]) -> EvaluationResult:
        value = context.get("value")
        if value is None or context.get("quality") != "VALID" or context.get("freshness") != "FRESH":
            return EvaluationResult(False, reason="Không có dữ liệu mới và hợp lệ để đánh giá")
        active = _compare(config["operator"], float(value), float(config["value"]))
        return EvaluationResult(active, config.get("severity", "WARNING") if active else None, evidence={"operator": config["operator"], "threshold": float(config["value"])})


class ThresholdBandsEvaluator(BaseEvaluator):
    required_fields = ("bands",)

    def validate(self, config: dict[str, Any]) -> list[str]:
        missing = super().validate(config)
        for index, band in enumerate(config.get("bands") or []):
            for field in ("severity", "operator", "value"):
                if band.get(field) is None:
                    missing.append(f"bands.{index}.{field}")
        return missing

    def evaluate(self, config: dict[str, Any], context: dict[str, Any]) -> EvaluationResult:
        if context.get("value") is None or context.get("quality") != "VALID" or context.get("freshness") != "FRESH":
            return EvaluationResult(False, reason="Không có dữ liệu mới và hợp lệ để đánh giá")
        matched = [band for band in config["bands"] if _compare(band["operator"], float(context["value"]), float(band["value"]))]
        if not matched:
            return EvaluationResult(False)
        severity = "CRITICAL" if any(item["severity"] == "CRITICAL" for item in matched) else "WARNING"
        selected = next(item for item in matched if item["severity"] == severity)
        return EvaluationResult(True, severity, evidence={"operator": selected["operator"], "threshold": float(selected["value"])})


class RangeBandsEvaluator(BaseEvaluator):
    required_fields = ("bands",)

    def validate(self, config: dict[str, Any]) -> list[str]:
        if isinstance(config.get("range"), dict):
            bounds = config["range"]
            errors = []
            if config.get("range_mode") not in {"INSIDE_RANGE", "OUTSIDE_RANGE"}:
                errors.append("range_mode")
            if bounds.get("min") is None and bounds.get("max") is None:
                errors.append("range")
            if bounds.get("min") is not None and bounds.get("max") is not None and float(bounds["min"]) > float(bounds["max"]):
                errors.append("range")
            return errors
        missing = super().validate(config)
        for index, band in enumerate(config.get("bands") or []):
            for field in ("severity", "lower", "upper"):
                if band.get(field) is None:
                    missing.append(f"bands.{index}.{field}")
        return missing

    def evaluate(self, config: dict[str, Any], context: dict[str, Any]) -> EvaluationResult:
        value = context.get("value")
        if value is None or context.get("quality") != "VALID" or context.get("freshness") != "FRESH":
            return EvaluationResult(False)
        if isinstance(config.get("range"), dict):
            inside = _inside_range(value, config["range"])
            active = inside if config["range_mode"] == "INSIDE_RANGE" else not inside
            return EvaluationResult(active, config.get("severity", "WARNING") if active else None,
                evidence={"operator": config["range_mode"], **config["range"]})
        matched = [band for band in config["bands"] if float(value) < float(band["lower"]) or float(value) > float(band["upper"])]
        if not matched:
            return EvaluationResult(False)
        severity = "CRITICAL" if any(item["severity"] == "CRITICAL" for item in matched) else "WARNING"
        selected = next(item for item in matched if item["severity"] == severity)
        return EvaluationResult(True, severity, evidence={"lower": float(selected["lower"]), "upper": float(selected["upper"]), "operator": "OUTSIDE"})


class DigitalStateEvaluator(BaseEvaluator):
    required_fields = ("active_state", "active_value")

    def evaluate(self, config: dict[str, Any], context: dict[str, Any]) -> EvaluationResult:
        value = context.get("value")
        if value is None or context.get("quality") != "VALID" or context.get("freshness") != "FRESH":
            return EvaluationResult(False)
        active = float(value) == float(config["active_value"])
        return EvaluationResult(active, config.get("severity", "CRITICAL") if active else None)


def _inside_range(value: object, bounds: object) -> bool:
    if value is None or not isinstance(bounds, dict):
        return False
    lower, upper, observed = bounds.get("min"), bounds.get("max"), float(value)
    return (lower is None or observed >= float(lower)) and (upper is None or observed <= float(upper))


def _matches_numeric_condition(value: object, condition: object) -> bool:
    if value is None or not isinstance(condition, dict):
        return False
    if condition.get("operator") in {"LT", "LTE", "GT", "GTE", "EQ"} and condition.get("value") is not None:
        return _compare(str(condition["operator"]), float(value), float(condition["value"]))
    return _inside_range(value, condition)


class MultiConditionEvaluator(BaseEvaluator):
    """Match one coherent Actuator snapshot; zero and equal bounds are valid."""

    def validate(self, config: dict[str, Any]) -> list[str]:
        errors: list[str] = []
        if config.get("logic", "AND") != "AND":
            errors.append("logic")
        if all(config.get(field) is None for field in ("reported_state", "voltage", "current")):
            errors.append("conditions")
        for field in ("voltage", "current"):
            bounds = config.get(field)
            if bounds is None:
                continue
            if not isinstance(bounds, dict):
                errors.append(field)
            elif bounds.get("operator") is not None:
                if bounds.get("operator") not in {"LT", "LTE", "GT", "GTE", "EQ"} or bounds.get("value") is None:
                    errors.append(field)
            elif bounds.get("min") is None and bounds.get("max") is None:
                errors.append(field)
            elif bounds.get("min") is not None and bounds.get("max") is not None and float(bounds["min"]) > float(bounds["max"]):
                errors.append(f"{field}.range")
        duration = config.get("duration_seconds", 0)
        if int(duration) < 0:
            errors.append("duration_seconds")
        return errors

    def evaluate(self, config: dict[str, Any], context: dict[str, Any]) -> EvaluationResult:
        conditions: list[bool] = []
        if config.get("reported_state") is not None:
            conditions.append(context.get("reported_state") is config["reported_state"])
        if config.get("voltage") is not None:
            conditions.append(_matches_numeric_condition(context.get("voltage_v"), config["voltage"]))
        if config.get("current") is not None:
            conditions.append(_matches_numeric_condition(context.get("current_a"), config["current"]))
        active = bool(conditions) and all(conditions)
        return EvaluationResult(active, config.get("severity", "WARNING") if active else None, evidence={
            "reported_state": context.get("reported_state"), "desired_state": context.get("desired_state"),
            "voltage_v": context.get("voltage_v"), "current_a": context.get("current_a"),
        })


class ThresholdDurationEvaluator(ThresholdEvaluator):
    required_fields = ("operator", "value", "duration_seconds")

    def validate(self, config: dict[str, Any]) -> list[str]:
        missing = super().validate(config)
        if not missing and int(config["duration_seconds"]) < 0:
            missing.append("duration_seconds")
        return missing


class BaselineDeviationEvaluator(BaseEvaluator):
    required_fields = ("baseline_source", "deviation_operator", "deviation_percent", "minimum_samples", "window_seconds")

    def validate(self, config: dict[str, Any]) -> list[str]:
        missing = super().validate(config)
        if config.get("baseline_source") == "FIXED" and config.get("baseline_value") is None:
            missing.append("baseline_value")
        if config.get("baseline_source") not in {None, "FIXED", "ROLLING_AVERAGE", "ROLLING_MEDIAN"}:
            missing.append("baseline_source")
        if config.get("deviation_operator") not in {None, "BELOW", "ABOVE"}:
            missing.append("deviation_operator")
        if config.get("deviation_percent") is not None and not 0 <= float(config["deviation_percent"]) <= 100:
            missing.append("deviation_percent")
        if config.get("minimum_samples") is not None and int(config["minimum_samples"]) < 1:
            missing.append("minimum_samples")
        if config.get("window_seconds") is not None and int(config["window_seconds"]) <= 0:
            missing.append("window_seconds")
        return list(dict.fromkeys(missing))

    def evaluate(self, config: dict[str, Any], context: dict[str, Any]) -> EvaluationResult:
        if context.get("quality") != "VALID" or context.get("freshness") != "FRESH" or context.get("value") is None:
            return EvaluationResult(False, reason="Không có dữ liệu mới và hợp lệ để đánh giá")
        values = _valid_values(context)
        source = config["baseline_source"]
        if source == "FIXED":
            baseline = float(config["baseline_value"])
        else:
            if len(values) < int(config["minimum_samples"]):
                return EvaluationResult(False, reason="Chưa đủ mẫu để tính đường cơ sở")
            baseline = sum(values) / len(values) if source == "ROLLING_AVERAGE" else float(median(values))
        deviation = float(config["deviation_percent"]) / 100
        operator = config["deviation_operator"]
        threshold = baseline * (1 - deviation if operator == "BELOW" else 1 + deviation)
        active = float(context["value"]) < threshold if operator == "BELOW" else float(context["value"]) > threshold
        return EvaluationResult(active, config.get("severity", "WARNING") if active else None, evidence={"baseline": baseline, "operator": "LT" if operator == "BELOW" else "GT", "threshold": threshold, "deviation_percent": float(config["deviation_percent"])})


class WindowDurationEvaluator(BaseEvaluator):
    required_fields = ("condition", "threshold", "window_duration_seconds", "minimum_coverage", "minimum_samples", "aggregation")

    def validate(self, config: dict[str, Any]) -> list[str]:
        missing = super().validate(config)
        if config.get("condition") not in {None, "LT", "LTE", "GT", "GTE"}:
            missing.append("condition")
        if config.get("aggregation") not in {None, "AVERAGE", "MINIMUM", "MAXIMUM", "LATEST"}:
            missing.append("aggregation")
        if config.get("window_duration_seconds") is not None and int(config["window_duration_seconds"]) <= 0:
            missing.append("window_duration_seconds")
        if config.get("minimum_samples") is not None and int(config["minimum_samples"]) < 1:
            missing.append("minimum_samples")
        if config.get("minimum_coverage") is not None and not 0 < float(config["minimum_coverage"]) <= 1:
            missing.append("minimum_coverage")
        return list(dict.fromkeys(missing))

    def evaluate(self, config: dict[str, Any], context: dict[str, Any]) -> EvaluationResult:
        if context.get("quality") != "VALID" or context.get("freshness") != "FRESH":
            return EvaluationResult(False, reason="Không có dữ liệu mới và hợp lệ để đánh giá")
        values = _valid_values(context)
        if len(values) < int(config["minimum_samples"]):
            return EvaluationResult(False, reason="Chưa đủ mẫu trong cửa sổ đánh giá")
        if float(context.get("coverage_ratio", 0)) < float(config["minimum_coverage"]):
            return EvaluationResult(False, reason="Độ phủ dữ liệu chưa đủ")
        aggregation = config["aggregation"]
        observed = {"AVERAGE": sum(values) / len(values), "MINIMUM": min(values), "MAXIMUM": max(values), "LATEST": values[-1]}[aggregation]
        threshold = float(config["threshold"])
        active = _compare(config["condition"], observed, threshold)
        return EvaluationResult(active, config.get("severity", "WARNING") if active else None, evidence={"aggregation": aggregation, "operator": config["condition"], "threshold": threshold, "aggregated_value": observed, "window_duration_seconds": int(config["window_duration_seconds"]), "sample_count": len(values)})


class TrendEvaluator(BaseEvaluator):
    required_fields = ("direction", "window_duration_seconds", "minimum_samples", "minimum_delta")

    def validate(self, config: dict[str, Any]) -> list[str]:
        missing = super().validate(config)
        if config.get("direction") not in {None, "INCREASING", "DECREASING"}:
            missing.append("direction")
        if config.get("window_duration_seconds") is not None and int(config["window_duration_seconds"]) <= 0:
            missing.append("window_duration_seconds")
        if config.get("minimum_samples") is not None and int(config["minimum_samples"]) < 2:
            missing.append("minimum_samples")
        if config.get("minimum_delta") is not None and float(config["minimum_delta"]) <= 0:
            missing.append("minimum_delta")
        return list(dict.fromkeys(missing))

    def evaluate(self, config: dict[str, Any], context: dict[str, Any]) -> EvaluationResult:
        if context.get("quality") != "VALID" or context.get("freshness") != "FRESH":
            return EvaluationResult(False, reason="Không có dữ liệu mới và hợp lệ để đánh giá")
        values = _valid_values(context)
        if len(values) < int(config["minimum_samples"]):
            return EvaluationResult(False, reason="Chưa đủ mẫu để đánh giá xu hướng")
        direction = config["direction"]
        adjacent = list(pairwise(values))
        monotonic = all(right >= left for left, right in adjacent) if direction == "INCREASING" else all(right <= left for left, right in adjacent)
        delta = values[-1] - values[0]
        active = monotonic and (delta >= float(config["minimum_delta"]) if direction == "INCREASING" else -delta >= float(config["minimum_delta"]))
        return EvaluationResult(active, config.get("severity", "WARNING") if active else None, evidence={"direction": direction, "delta": delta, "window_duration_seconds": int(config["window_duration_seconds"]), "sample_count": len(values)})


EVALUATOR_REGISTRY: dict[str, Evaluator] = {
    "THRESHOLD": ThresholdEvaluator(),
    "THRESHOLD_BANDS": ThresholdBandsEvaluator(),
    "RANGE_BANDS": RangeBandsEvaluator(),
    "DIGITAL_STATE": DigitalStateEvaluator(),
    "THRESHOLD_DURATION": ThresholdDurationEvaluator(),
    "BASELINE_DEVIATION": BaselineDeviationEvaluator(),
    "WINDOW_DURATION": WindowDurationEvaluator(),
    "TREND": TrendEvaluator(),
    "MULTI_CONDITION": MultiConditionEvaluator(),
}


def validate_condition_config(evaluator_type: str, config: dict[str, Any]) -> list[str]:
    evaluator = EVALUATOR_REGISTRY.get(evaluator_type)
    return ["evaluator_type"] if evaluator is None else evaluator.validate(config)
