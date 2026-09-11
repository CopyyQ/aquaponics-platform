import logging
from datetime import UTC, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.enums import ProjectStatus, UserStatus
from app.mqtt.schemas import MqttTelemetryPayload
from app.queries.device_runtime_queries import get_device_runtime_context
from app.schemas.telemetry import DeviceTelemetryInput, TelemetryIngestResponse
from app.services.telemetry_service import ingest_telemetry

logger = logging.getLogger(__name__)


def runtime_is_operational(device, project, owner) -> bool:
    return bool(
        device.is_enabled
        and not device.is_deleted
        and project.status == ProjectStatus.ACTIVE
        and not project.is_deleted
        and project.deleted_at is None
        and owner.status == UserStatus.ACTIVE
        and not owner.is_deleted
        and owner.deleted_at is None
    )


async def ingest_mqtt_telemetry(
    db: AsyncSession,
    *,
    device_code: str,
    payload: MqttTelemetryPayload,
    received_at: datetime | None = None,
) -> TelemetryIngestResponse | None:
    received_at = received_at or datetime.now(UTC)
    context = await get_device_runtime_context(db, device_code)
    if context is None:
        logger.warning("event=mqtt_unknown_device device_code=%s", device_code)
        return None
    device, project, owner = context
    if not runtime_is_operational(device, project, owner):
        logger.warning(
            "event=mqtt_disabled_context device_code=%s project_id=%s device_id=%s",
            device_code,
            project.id,
            device.id,
        )
        return None
    future_limit = received_at + timedelta(seconds=settings.mqtt_max_future_skew_seconds)
    past_limit = received_at - timedelta(seconds=settings.mqtt_max_past_age_seconds)
    if payload.sent_at > future_limit or payload.sent_at < past_limit:
        logger.warning("event=mqtt_invalid_sent_at device_code=%s", device_code)
        return None
    accepted_readings = [
        reading
        for reading in payload.readings
        if past_limit <= reading.recorded_at <= future_limit
    ]
    if not accepted_readings:
        logger.warning("event=mqtt_no_valid_timestamps device_code=%s", device_code)
        return None
    return await ingest_telemetry(
        db,
        device=device,
        payload=DeviceTelemetryInput(sent_at=payload.sent_at, readings=accepted_readings),
        received_at=received_at,
    )
