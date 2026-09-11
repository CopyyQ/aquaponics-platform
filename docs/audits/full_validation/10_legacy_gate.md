# Legacy gate

Full pytest collection is blocked by `tests/test_operational_alerts.py` importing the removed `set_feedback_binding` endpoint. This is a legacy expectation that must be retired or replaced with canonical Actuator metric tests.
