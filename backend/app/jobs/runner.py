import asyncio
import logging
from datetime import UTC, datetime

from app.core.config import settings
from app.core.enums import AggregatePeriod
from app.jobs.actuator_command_timeout import timeout_actuator_commands
from app.jobs.offline_scanner import scan_offline_state
from app.jobs.notification_outbox import dispatch_operational_notifications
from app.jobs.project_health_evaluator import evaluate_project_health
from app.jobs.telemetry_aggregation import aggregate_period

logger = logging.getLogger(__name__)


async def _run_job(job_name: str, job) -> bool:
    try:
        await job()
        return True
    except asyncio.CancelledError:
        raise
    except Exception:
        logger.exception("event=scheduler_job_failed job=%s", job_name)
        return False


async def run_scheduler_cycle(now: datetime | None = None) -> bool:
    cycle_time = now or datetime.now(UTC)
    results = [
        await _run_job("offline_scanner", scan_offline_state),
        await _run_job("actuator_command_timeout", timeout_actuator_commands),
        await _run_job("notification_outbox", dispatch_operational_notifications),
        await _run_job(
            "telemetry_aggregation_hour",
            lambda: aggregate_period(AggregatePeriod.HOUR),
        ),
    ]
    if cycle_time.minute < 2:
        results.append(
            await _run_job(
                "telemetry_aggregation_day",
                lambda: aggregate_period(AggregatePeriod.DAY),
            )
        )
    if cycle_time.minute % 5 == 0:
        results.append(
            await _run_job("project_health_evaluator", evaluate_project_health)
        )
    return all(results)


async def background_loop() -> None:
    while True:
        started_at = datetime.now(UTC)
        try:
            succeeded = await run_scheduler_cycle(started_at)
            duration_ms = int((datetime.now(UTC) - started_at).total_seconds() * 1000)
            logger.info(
                "event=scheduler_cycle_completed succeeded=%s duration_ms=%s",
                succeeded,
                duration_ms,
            )
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("event=scheduler_cycle_failed")
        await asyncio.sleep(settings.job_interval_seconds)


def main() -> None:
    asyncio.run(background_loop())


if __name__ == "__main__":
    main()
