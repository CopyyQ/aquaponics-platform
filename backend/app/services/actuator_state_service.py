from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.actuator import Actuator, ActuatorCommand, ActuatorStateHistory


async def record_actuator_reported_state(
    db: AsyncSession,
    *,
    actuator: Actuator,
    state: bool,
    source: str,
    command_id: int | None = None,
    received_at: datetime | None = None,
    state_reported_at: datetime | None = None,
) -> bool:
    """Persist a state transition and refresh the trusted status heartbeat.

    ``last_reported_at`` is always backend receipt time.  ``state_reported_at``
    is only used to stop an older device observation from reversing a newer
    state; it never controls freshness.
    """

    timestamp = received_at or datetime.now(UTC)
    await db.execute(
        select(Actuator.id).where(Actuator.id == actuator.id).with_for_update()
    )
    future_limit = timestamp + timedelta(
        seconds=settings.mqtt_max_future_skew_seconds
    )
    # A legacy clock bug may have written a future freshness value.  A valid
    # server-received heartbeat must repair it instead of leaving the actuator
    # permanently stale until that future instant.
    if (
        actuator.last_reported_at is None
        or actuator.last_reported_at > future_limit
        or timestamp > actuator.last_reported_at
    ):
        actuator.last_reported_at = timestamp
    # Explicit final-architecture name for the trusted server receipt time.
    actuator.status_received_at = timestamp

    observed_at = state_reported_at or timestamp
    # Do not let a retained/duplicate older MQTT packet overwrite newer state.
    # Its arrival still refreshed last_reported_at above.
    if (
        actuator.reported_state_at is not None
        and observed_at < actuator.reported_state_at
    ):
        return False
    previous_state = actuator.reported_state
    actuator.reported_state = state
    actuator.reported_state_at = observed_at
    if previous_state is state:
        return False
    db.add(
        ActuatorStateHistory(
            actuator_id=actuator.id,
            state=state,
            recorded_at=timestamp,
            source=source,
            command_id=command_id,
        )
    )
    return True


async def acknowledge_matching_actuator_command(
    db: AsyncSession, *, actuator: Actuator, reported_state: bool, acknowledged_at: datetime
) -> ActuatorCommand | None:
    """Acknowledge only the active command confirmed by a device status report.

    Terminal commands intentionally remain immutable: a late periodic status can
    update the runtime state but cannot rewrite command history.
    """
    command = await db.scalar(
        select(ActuatorCommand)
        .where(
            ActuatorCommand.actuator_id == actuator.id,
            ActuatorCommand.status.in_(("PENDING", "PUBLISHED")),
            ActuatorCommand.desired_state.is_(reported_state),
            ActuatorCommand.requested_at <= acknowledged_at,
        )
        .order_by(ActuatorCommand.requested_at.desc(), ActuatorCommand.id.desc())
        .limit(1)
        .with_for_update()
    )
    if command is None:
        return None
    command.status = "ACKNOWLEDGED"
    command.reported_state = reported_state
    command.acknowledged_at = acknowledged_at
    return command
