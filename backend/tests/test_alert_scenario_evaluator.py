import pytest

from app.services.alert_evaluators import EVALUATOR_REGISTRY, validate_condition_config


def config(**overrides):
    return {"logic": "AND", "reported_state": True, "voltage": {"min": 11, "max": 13},
            "current": {"min": 0, "max": 0}, "duration_seconds": 5, **overrides}


def evaluate(condition, **context):
    return EVALUATOR_REGISTRY["MULTI_CONDITION"].evaluate(condition, context).active


def test_on_voltage_range_and_exact_zero_current_matches():
    assert evaluate(config(), reported_state=True, voltage_v=12, current_a=0)


def test_off_does_not_match_even_when_electrical_values_match():
    assert not evaluate(config(), reported_state=False, voltage_v=12, current_a=0)


def test_exact_zero_range_rejects_nonzero_current():
    assert not evaluate(config(), reported_state=True, voltage_v=12, current_a=0.01)


def test_equal_bounds_are_valid_and_inclusive():
    condition = config(voltage={"min": 12, "max": 12})
    assert validate_condition_config("MULTI_CONDITION", condition) == []
    assert evaluate(condition, reported_state=True, voltage_v=12, current_a=0)


def test_reversed_bounds_are_rejected():
    assert "voltage.range" in validate_condition_config("MULTI_CONDITION", config(voltage={"min": 13, "max": 11}))


@pytest.mark.parametrize(("bounds", "value", "expected"), [
    ({"min": None, "max": 0.05}, 0.05, True),
    ({"min": None, "max": 0.05}, 0.051, False),
    ({"min": 13, "max": None}, 13, True),
    ({"min": 13, "max": None}, 12.99, False),
])
def test_open_bounds_are_inclusive(bounds, value, expected):
    assert evaluate(config(current=bounds), reported_state=True, voltage_v=12, current_a=value) is expected


def test_sensor_range_mode_is_explicit():
    evaluator = EVALUATOR_REGISTRY["RANGE_BANDS"]
    context = {"value": 7, "quality": "VALID", "freshness": "FRESH"}
    assert evaluator.evaluate({"range": {"min": 6, "max": 8}, "range_mode": "INSIDE_RANGE"}, context).active
    assert not evaluator.evaluate({"range": {"min": 6, "max": 8}, "range_mode": "OUTSIDE_RANGE"}, context).active
