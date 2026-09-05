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
        matched = [band for band in config["bands"] if float(value) < float(band["lower"]) or float(value) > float(band["upper"])]
        if not matched:
            return EvaluationResult(False)
        severity = "CRITICAL" if any(item["severity"] == "CRITICAL" for item in matched) else "WARNING"
        selected = next(item for item in matched if item["severity"] == severity)
        return EvaluationResult(True, severity, evidence={"lower": float(selected["lower"]), "upper": float(selected["upper"]), "operator": "OUTSIDE"})


class ActuatorFeedbackEvaluator(BaseEvaluator):
    required_fields = ("feedback_role",)

    def validate(self, config: dict[str, Any]) -> list[str]:
        missing = super().validate(config)
        if config.get("feedback_role") not in {"RUNNING_CURRENT", "SUPPLY_VOLTAGE"}:
            missing.append("feedback_role")
        legacy = "min_running_current_a" in config or "max_running_current_a" in config
        if legacy:
            for field in ("min_running_current_a", "max_running_current_a"):
                if config.get(field) is None:
                    missing.append(field)
            if not any(field in missing for field in ("min_running_current_a", "max_running_current_a")) and float(config["max_running_current_a"]) <= float(config["min_running_current_a"]):
                missing.append("max_running_current_a")
        else:
            if config.get("operator") not in {"LT", "LTE", "GT", "GTE"}:
                missing.append("operator")
            if config.get("threshold") is None:
                missing.append("threshold")
        for field in ("startup_grace_seconds", "debounce_seconds"):
            if config.get(field) is None:
                missing.append(field)
            elif int(config[field]) < 0:
                missing.append(field)
        recovery_field = "recovery_current_a" if legacy else "recovery_threshold"
        if config.get(recovery_field) is None:
            missing.append(recovery_field)
        if config.get("recovery_duration_seconds") is None:
            missing.append("recovery_duration_seconds")
        elif int(config["recovery_duration_seconds"]) < 0:
            missing.append("recovery_duration_seconds")
        return list(dict.fromkeys(missing))

    def evaluate(self, config: dict[str, Any], context: dict[str, Any]) -> EvaluationResult:
        role = str(config.get("feedback_role") or "RUNNING_CURRENT")
        value = context.get("feedback_value")
        if value is None:
            value = context.get("current_a") if role == "RUNNING_CURRENT" else context.get("voltage_v")
        operator = config.get("operator")
        if role == "RUNNING_CURRENT" and operator in {None, "LT", "LTE"} and not context.get("expected_on"):
            return EvaluationResult(False)
        if context.get("quality") != "VALID" or context.get("freshness") != "FRESH" or value is None:
            return EvaluationResult(False, reason="Không thể xác nhận trạng thái điện")
        observed = float(value)
        if operator:
            threshold = float(config["threshold"])
            active = _compare(operator, observed, threshold)
            return EvaluationResult(active, config.get("severity", "WARNING") if active else None, evidence={"operator": operator, "threshold": threshold, "feedback_role": role})
        minimum = float(config["min_running_current_a"])
        maximum = float(config["max_running_current_a"])
        active = observed < minimum or observed > maximum
        return EvaluationResult(active, config.get("severity", "CRITICAL") if active else None, evidence={"operator": "LT" if observed < minimum else "GT", "threshold": minimum if observed < minimum else maximum, "minimum_running_current_a": minimum, "maximum_running_current_a": maximum, "feedback_role": role})


class ScheduleFeedbackEvaluator(ActuatorFeedbackEvaluator):
    required_fields = ("schedule_id", *ActuatorFeedbackEvaluator.required_fields)


class DigitalStateEvaluator(BaseEvaluator):
    required_fields = ("active_state", "active_value")

    def evaluate(self, config: dict[str, Any], context: dict[str, Any]) -> EvaluationResult:
        value = context.get("value")
        if value is None or context.get("quality") != "VALID" or context.get("freshness") != "FRESH":
            return EvaluationResult(False)
        active = float(value) == float(config["active_value"])
        return EvaluationResult(active, config.get("severity", "CRITICAL") if active else None)


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
    "ACTUATOR_FEEDBACK": ActuatorFeedbackEvaluator(),
    "SCHEDULE_FEEDBACK": ScheduleFeedbackEvaluator(),
    "BASELINE_DEVIATION": BaselineDeviationEvaluator(),
    "WINDOW_DURATION": WindowDurationEvaluator(),
    "TREND": TrendEvaluator(),
}


def validate_condition_config(evaluator_type: str, config: dict[str, Any]) -> list[str]:
    evaluator = EVALUATOR_REGISTRY.get(evaluator_type)
    return ["evaluator_type"] if evaluator is None else evaluator.validate(config)
