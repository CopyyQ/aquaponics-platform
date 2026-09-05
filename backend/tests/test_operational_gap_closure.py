from datetime import UTC, datetime

import pytest
from pydantic import ValidationError
from sqlalchemy import select, text
from sqlalchemy.exc import DBAPIError

from app.db.session import AsyncSessionLocal
from app.models.operational_alert import AlertRule, AlertRuleProfile, AlertRuleRevision
from app.schemas.telemetry import DeviceReadingInput
from app.services.alert_evaluators import EVALUATOR_REGISTRY, validate_condition_config
from app.services.measurement_quality import classify_measurement_quality
from app.services.notification_outbox_service import format_operational_message


@pytest.mark.parametrize("value", [float("nan"), float("inf"), float("-inf")])
def test_non_finite_measurements_are_invalid_and_rejected_at_ingestion(value: float) -> None:
    assert classify_measurement_quality("LOAD_CURRENT_A", value)[0] == "INVALID"
    with pytest.raises(ValidationError):
        DeviceReadingInput(sensor_code="CURRENT", value=value, recorded_at=datetime.now(UTC))


@pytest.mark.parametrize(
    ("model_code", "value", "quality"),
    [
        ("LOAD_CURRENT_A", 0.0, "VALID"),
        ("LOAD_CURRENT_A", -0.01, "OUT_OF_RANGE"),
        ("LOAD_CURRENT_A", 1001.0, "OUT_OF_RANGE"),
        ("CUSTOM_CURRENT", 0.5, "UNVALIDATED"),
        ("LOAD_CURRENT_A", None, "NO_DATA"),
    ],
)
def test_measurement_quality_semantics(model_code: str, value: float | None, quality: str) -> None:
    assert classify_measurement_quality(model_code, value)[0] == quality


def test_baseline_deviation_fixed_and_rolling_are_executable() -> None:
    evaluator = EVALUATOR_REGISTRY["BASELINE_DEVIATION"]
    fixed = {"baseline_source": "FIXED", "baseline_value": 100, "deviation_operator": "BELOW", "deviation_percent": 30, "minimum_samples": 3, "window_seconds": 300, "severity": "WARNING"}
    assert not validate_condition_config("BASELINE_DEVIATION", fixed)
    assert not evaluator.evaluate(fixed, {"value": 80, "quality": "VALID", "freshness": "FRESH"}).active
    result = evaluator.evaluate(fixed, {"value": 65, "quality": "VALID", "freshness": "FRESH"})
    assert result.active and result.evidence == {"baseline": 100.0, "operator": "LT", "threshold": 70.0, "deviation_percent": 30.0}
    rolling = {**fixed, "baseline_source": "ROLLING_MEDIAN"}
    rolling.pop("baseline_value")
    assert evaluator.evaluate(rolling, {"value": 65, "quality": "VALID", "freshness": "FRESH", "samples": [100, 101, 99]}).active
    assert not evaluator.evaluate(rolling, {"value": 65, "quality": "VALID", "freshness": "FRESH", "samples": [100]}).active


def test_window_duration_requires_coverage_and_aggregates() -> None:
    evaluator = EVALUATOR_REGISTRY["WINDOW_DURATION"]
    config = {"condition": "LT", "threshold": 150, "window_duration_seconds": 60, "minimum_coverage": 0.9, "minimum_samples": 3, "aggregation": "AVERAGE", "severity": "WARNING"}
    assert not validate_condition_config("WINDOW_DURATION", config)
    assert evaluator.evaluate(config, {"quality": "VALID", "freshness": "FRESH", "samples": [120, 130, 140], "coverage_ratio": 1.0}).active
    assert not evaluator.evaluate(config, {"quality": "VALID", "freshness": "FRESH", "samples": [120, 130, 140], "coverage_ratio": 0.5}).active
    assert not evaluator.evaluate(config, {"quality": "OUT_OF_RANGE", "freshness": "FRESH", "samples": [120, 130, 140], "coverage_ratio": 1.0}).active


def test_trend_is_deterministic_and_requires_monotonic_delta() -> None:
    evaluator = EVALUATOR_REGISTRY["TREND"]
    config = {"direction": "INCREASING", "window_duration_seconds": 300, "minimum_samples": 4, "minimum_delta": 0.5, "severity": "WARNING"}
    assert not validate_condition_config("TREND", config)
    assert evaluator.evaluate(config, {"quality": "VALID", "freshness": "FRESH", "samples": [0.1, 0.2, 0.4, 0.7]}).active
    assert not evaluator.evaluate(config, {"quality": "VALID", "freshness": "FRESH", "samples": [0.1, 0.4, 0.3, 0.8]}).active
    assert not evaluator.evaluate(config, {"quality": "INVALID", "freshness": "FRESH", "samples": [0.1, 0.2, 0.4, 0.7]}).active


def test_telegram_contains_persisted_condition_started_duration_and_vietnamese_escalation() -> None:
    message = format_operational_message({
        "event_type": "ESCALATED", "business_risk_level": "EXTREME", "technical_severity": "CRITICAL", "previous_technical_severity": "WARNING",
        "project_name": "Ao A", "project_code": "A", "device_name": "Thiết bị A", "sensor_name": "Cảm biến DO", "rule_name": "DO nước bể cá",
        "value": 4.2, "unit": "mg/L", "operator": "LT", "threshold": 5.0, "quality": "VALID", "freshness": "FRESH",
        "recorded_at": "2026-08-24T03:20:15Z", "received_at": "2026-08-24T03:20:16Z", "started_at": "2026-08-24T03:20:15Z", "duration_seconds": 272, "incident_id": 9,
    })
    assert "Mức độ nghiệp vụ: CỰC CAO" in message
    assert "Mức kỹ thuật đã tăng: Cảnh báo → Nghiêm trọng" in message
    assert "Giá trị hiện tại: 4,2 mg/L" in message
    assert "Ngưỡng kích hoạt: < 5 mg/L" in message
    assert "Bắt đầu: 24/08/2026 10:20:15" in message
    assert "Đã kéo dài: 4 phút 32 giây" in message
    assert "WARNING" not in message and "CRITICAL" not in message and "EXTREME" not in message


@pytest.mark.asyncio
async def test_seeded_catalog_publishes_only_complete_rules_and_maps_canonical_models() -> None:
    async with AsyncSessionLocal() as db:
        rows = (await db.execute(select(AlertRule.code, AlertRuleRevision.status).join(AlertRuleRevision, AlertRuleRevision.id == AlertRule.current_revision_id))).all()
        statuses = dict(rows)
        assert {code for code, status in statuses.items() if status == "PUBLISHED"} == {"FISH_TANK_DO_LOW", "WATER_PH_OUT_OF_RANGE", "NITRITE_HIGH", "TDS_LOW", "AIR_TEMPERATURE_HIGH"}
        profiles = set((await db.scalars(select(AlertRuleProfile.code))).all())
        # TDS has no canonical SensorModel in this repository. Its published
        # rule remains non-applicable until deployment adds that stable model.
        assert {"FISH_TANK_DO_LOW_CANONICAL", "WATER_PH_OUT_OF_RANGE_CANONICAL", "AIR_TEMPERATURE_HIGH_CANONICAL"}.issubset(profiles)
        assert "TDS_LOW_CANONICAL" not in profiles


@pytest.mark.asyncio
async def test_published_revision_business_content_is_immutable_in_database() -> None:
    async with AsyncSessionLocal() as db:
        revision_id = await db.scalar(select(AlertRuleRevision.id).where(AlertRuleRevision.status == "PUBLISHED").limit(1))
        assert revision_id is not None
        with pytest.raises(DBAPIError, match="Published alert rule revision content is immutable"):
            await db.execute(text("UPDATE alert_rule_revisions SET condition_config='{}'::jsonb WHERE id=:id"), {"id": revision_id})
            await db.flush()
        await db.rollback()
        await db.execute(text("UPDATE alert_rule_revisions SET status='RETIRED' WHERE id=:id"), {"id": revision_id})
        await db.flush()
        with pytest.raises(DBAPIError, match="Published alert rule revision content is immutable"):
            await db.execute(text("UPDATE alert_rule_revisions SET consequence='changed' WHERE id=:id"), {"id": revision_id})
            await db.flush()
        await db.rollback()
