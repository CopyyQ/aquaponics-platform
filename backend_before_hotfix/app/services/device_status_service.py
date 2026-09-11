import logging
from datetime import UTC, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.enums import DeviceStatus
from app.mqtt.schemas import MqttStatusPayload
from app.queries.device_runtime_queries import get_device_runtime_context
from app.services.project_notification_service import dispatch_device_connectivity_transition
from app.services.telemetry_ingest_service import runtime_is_operational

logger = logging.getLogger(__name__)


async def update_device_status(
    db: AsyncSession,
    *,
    device_code: str,
    payload: MqttStatusPayload,
    received_at: datetime | None = None,
) -> bool:
    received_at = received_at or datetime.now(UTC)
    context = await get_device_runtime_context(db, device_code)
    if context is None:
        logger.warning(
            "event=mqtt_status_rejected device_code=%s reason=unknown_or_disabled_device",
            device_code,
        )
        return False
    device, project, owner = context
    if not runtime_is_operational(device, project, owner):
        logger.warning(
            "event=mqtt_status_rejected device_code=%s reason=runtime_not_operational",
            device_code,
        )
        return False
    future_limit = received_at + timedelta(seconds=settings.mqtt_max_future_skew_seconds)
    past_limit = received_at - timedelta(seconds=settings.mqtt_max_past_age_seconds)
    if not past_limit <= payload.sent_at <= future_limit:
        logger.warning(
            "event=mqtt_status_rejected device_code=%s reason=sent_at_out_of_range "
            "sent_at=%s received_at=%s",
            device_code,
            payload.sent_at.isoformat(),
            received_at.isoformat(),
        )
        return False
    previous_status = device.status
    previous_disconnected_at = device.disconnected_at
    device.status = DeviceStatus.ONLINE if payload.status == "ONLINE" else DeviceStatus.OFFLINE
    if device.status == DeviceStatus.OFFLINE and previous_status != DeviceStatus.OFFLINE:
        device.disconnected_at = received_at
    elif device.status == DeviceStatus.ONLINE:
        device.disconnected_at = None
    device.last_seen_at = received_at
    await db.commit()
    if previous_status != DeviceStatus.OFFLINE and device.status == DeviceStatus.OFFLINE:
        await dispatch_device_connectivity_transition(
            db, device_id=device.id, transition="DISCONNECTED",
            disconnected_at=device.disconnected_at, occurred_at=received_at,
        )
    elif previous_status == DeviceStatus.OFFLINE and device.status == DeviceStatus.ONLINE:
        await dispatch_device_connectivity_transition(
            db, device_id=device.id, transition="RECONNECTED",
            disconnected_at=previous_disconnected_at, occurred_at=received_at,
        )
    return True
