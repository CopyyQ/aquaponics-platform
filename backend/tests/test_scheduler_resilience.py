import math
from datetime import UTC, datetime

import pytest

from app.jobs import runner
from app.jobs.telemetry_aggregation import normalize_aggregate_values


@pytest.mark.parametrize(
    ("minimum", "maximum", "average", "expected"),
    [
        (7.2, 7.2, 7.2, (7.2, 7.2, 7.2)),
        (34.1, 34.1, 34.10000000000014, (34.1, 34.1, 34.1)),
        (-5.0, -1.0, -3.0, (-5.0, -1.0, -3.0)),
        (2.0, 4.0, 3.0, (2.0, 4.0, 3.0)),
    ],
)
def test_normalize_aggregate_values_clamps_float_noise(
    minimum: float,
    maximum: float,
    average: float,
    expected: tuple[float, float, float],
) -> None:
    assert normalize_aggregate_values(minimum, maximum, average) == expected


@pytest.mark.parametrize("value", [math.nan, math.inf, -math.inf])
def test_normalize_aggregate_values_rejects_non_finite(value: float) -> None:
    with pytest.raises(ValueError, match="finite"):
        normalize_aggregate_values(0.0, 1.0, value)


@pytest.mark.asyncio
async def test_scheduler_cycle_continues_after_independent_job_failure(monkeypatch) -> None:
    calls: list[str] = []

    async def failing_offline_scanner() -> None:
        calls.append("offline")
        raise RuntimeError("scanner failed")

    async def timeout_commands() -> None:
        calls.append("timeout")

    async def aggregate(period) -> None:
        calls.append(f"aggregate:{period.value}")

    monkeypatch.setattr(runner, "scan_offline_state", failing_offline_scanner)
    monkeypatch.setattr(runner, "timeout_actuator_commands", timeout_commands)
    monkeypatch.setattr(runner, "aggregate_period", aggregate)

    succeeded = await runner.run_scheduler_cycle(datetime(2026, 8, 5, 10, 5, tzinfo=UTC))

    assert succeeded is False
    assert calls == ["offline", "timeout", "aggregate:HOUR"]
