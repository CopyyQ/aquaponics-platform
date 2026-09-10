import logging
from datetime import UTC, datetime

from pydantic import ValidationError
from sqlalchemy import select

from app.db.session import async_session_factory
from app.models.actuator import Actuator, ActuatorCommand, ActuatorReading
from app.models.device import Device
from app.mqtt.schemas import MqttCommandAckPayload, MqttStatusPayload, MqttTelemetryPayload
from app.services.actuator_state_service import (
    acknowledge_matching_actuator_command,
    record_actuator_reported_state,
)
from app.services.audit_service import write_audit
from app.services.device_status_service import update_device_status
from app.services.project_notification_service import dispatch_actuator_command_transition
from app.services.operational_incident_service import evaluate_actuator_composite_incident
from app.services.telemetry_ingest_service import ingest_mqtt_telemetry

logger = logging.getLogger(__name__)


async def handle_telemetry(device_code: str, raw_payload: bytes) -> None:
    try:
        payload = MqttTelemetryPayload.model_validate_json(raw_payload)
    except ValidationError as exc:
        logger.warning(
            "event=mqtt_invalid_telemetry device_code=%s errors=%s",
            device_code,
            exc.error_count(),
        )
        return
    async with async_session_factory() as db:
        result = await ingest_mqtt_telemetry(
            db, device_code=device_code, payload=payload
        )
        if result is not None:
            logger.info(
                "event=mqtt_telemetry_processed device_code=%s accepted_count=%s "
                "rejected_count=%s duplicate_count=%s",
                device_code,
                result.accepted,
                result.rejected,
                result.duplicates,
            )


async def handle_status(device_code: str, raw_payload: bytes) -> None:
    try:
        payload = MqttStatusPayload.model_validate_json(raw_payload)
    except ValidationError as exc:
        logger.warning(
            "event=mqtt_invalid_status device_code=%s errors=%s",
            device_code,
            exc.error_count(),
        )
        return
    received_at = datetime.now(UTC)
    async with async_session_factory() as db:
        accepted = await update_device_status(
            db, device_code=device_code, payload=payload, received_at=received_at
        )
        device = await db.scalar(select(Device).where(Device.code == device_code, Device.is_enabled.is_(True), Device.is_deleted.is_(False)))
        if device is not None and accepted:
            for item in payload.actuators:
                actuator = await db.scalar(select(Actuator).where(Actuator.device_id == device.id, Actuator.code == item.actuator_code, Actuator.is_enabled.is_(True), Actuator.is_deleted.is_(False), Actuator.removed_at.is_(None)))
                if actuator is None:
                    logger.warning(
                        "event=mqtt_actuator_unknown device_code=%s actuator_code=%s",
                        device_code,
                        item.actuator_code,
                    )
                    continue
                updated = await record_actuator_reported_state(
                    db,
                    actuator=actuator,
                    state=item.state,
                    source="PERIODIC_STATUS",
                    # Freshness means the server has received a valid status
                    # heartbeat, not when an unsynchronised device claims it
                    # observed the state. This must advance on every packet.
                    received_at=received_at,
                    state_reported_at=payload.sent_at,
                )
                if updated or actuator.reported_state == item.state:
                    await acknowledge_matching_actuator_command(
                        db,
                        actuator=actuator,
                        reported_state=item.state,
                        acknowledged_at=received_at,
                    )
                if item.voltage_v is not None or item.current_a is not None:
                    recorded_at = item.recorded_at or payload.sent_at
                    actuator.voltage_v = item.voltage_v
                    actuator.current_a = item.current_a
                    actuator.electrical_recorded_at = recorded_at
                    actuator.electrical_received_at = received_at
                    db.add(ActuatorReading(
                        actuator_id=actuator.id, voltage_v=item.voltage_v,
                        current_a=item.current_a, recorded_at=recorded_at,
                        received_at=received_at, quality="VALID",
                    ))
                    await evaluate_actuator_composite_incident(
                        db, device=device, actuator=actuator,
                        recorded_at=recorded_at, received_at=received_at,
                    )
            await db.commit()
        logger.info(
            "event=mqtt_status_processed device_code=%s accepted=%s",
            device_code,
            accepted,
        )


async def handle_command_ack(device_code: str, raw_payload: bytes) -> None:
    try:
        payload = MqttCommandAckPayload.model_validate_json(raw_payload)
    except ValidationError:
        logger.warning("event=invalid_ack device_code=%s", device_code)
        return
    async with async_session_factory() as db:
        device = await db.scalar(select(Device).where(Device.code == device_code, Device.is_enabled.is_(True), Device.is_deleted.is_(False)))
        if device is None:
            return
        command = await db.scalar(select(ActuatorCommand).join(Actuator).where(ActuatorCommand.id == payload.command_id, ActuatorCommand.actuator_id == Actuator.id, Actuator.device_id == device.id, Actuator.removed_at.is_(None)))
        if command is None:
            logger.warning("event=unknown_ack command_id=%s device_code=%s", payload.command_id, device_code)
            return
        actuator = await db.get(Actuator, command.actuator_id)
        if actuator is None or actuator.code != payload.actuator_code:
            logger.warning("event=invalid_ack command_id=%s device_code=%s", payload.command_id, device_code)
            return
        if command.status == "ACKNOWLEDGED":
            return
        now = datetime.now(UTC)
        command.status = payload.status
        command.acknowledged_at = now
        if payload.status == "FAILED":
            command.failed_at = now
            command.failure_reason = "Thiết bị trả về FAILED"
        command.reported_state = payload.reported_state
        await record_actuator_reported_state(
            db,
            actuator=actuator,
            state=payload.reported_state,
            source="COMMAND_ACK",
            command_id=command.id,
        )
        await write_audit(
            db,
            user_id=command.requested_by_user_id,
            project_id=device.project_id,
            action=f"ACTUATOR_COMMAND_{payload.status}",
            entity_type="ACTUATOR",
            entity_id=actuator.id,
            description="Thiết bị phản hồi lệnh điều khiển",
            new_data={"display_name": actuator.name, "desired_state": command.desired_state, "reported_state": payload.reported_state, "status": payload.status},
        )
        await db.commit()
        await dispatch_actuator_command_transition(
            db, command_id=command.id, transition=payload.status
        )
