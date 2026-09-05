"""Provision model-defined electrical feedback for physical actuators.

Model feedback definitions describe capability.  Bindings describe the concrete
sensor that supplies a reading for one installed actuator.  Existing operator
bindings are preserved; only a generated internal binding whose source has
been removed or moved is repaired to its deterministic local Sensor.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.actuator import Actuator
from app.models.actuator_model import ActuatorModel, ActuatorModelFeedbackDefinition
from app.models.device import Device
from app.models.operational_alert import ActuatorFeedbackBinding
from app.models.sensor import Sensor
from app.core.enums import SensorPurpose


@dataclass(frozen=True)
class ElectricalFeedbackProvisionResult:
    actuator_id: int
    sensors_created: int = 0
    bindings_created: int = 0
    bindings_repaired: int = 0
    bindings_migrated: int = 0
    bindings_preserved: int = 0


def generated_electrical_sensor_code(actuator_code: str, feedback_role: str) -> str:
    """Return a deterministic, MQTT-safe code within Sensor.code's 80 chars."""
    suffix = "-VOLTAGE" if feedback_role == "SUPPLY_VOLTAGE" else "-CURRENT"
    normalized = actuator_code.strip().upper()
    if len(normalized) + len(suffix) <= 80:
        return f"{normalized}{suffix}"
    digest = hashlib.sha256(normalized.encode()).hexdigest()[:8].upper()
    prefix_size = 80 - len(suffix) - len(digest) - 1
    return f"{normalized[:prefix_size]}-{digest}{suffix}"


async def ensure_actuator_electrical_feedback(
    db: AsyncSession,
    *,
    actuator: Actuator,
    actor_id: int | None = None,
) -> ElectricalFeedbackProvisionResult:
    """Add missing *enabled* model feedback definitions to an actuator.

    The caller owns the transaction.  A per-actuator PostgreSQL advisory lock
    serializes concurrent provisioning while the schema unique constraint keeps
    the role binding unique in every database.
    """
    if not actuator.is_enabled or actuator.removed_at is not None or actuator.is_deleted:
        return ElectricalFeedbackProvisionResult(actuator_id=actuator.id)
    actuator_device = await db.get(Device, actuator.device_id)
    if actuator_device is None or actuator_device.is_deleted or actuator_device.deleted_at is not None:
        return ElectricalFeedbackProvisionResult(actuator_id=actuator.id)
    if db.bind and db.bind.dialect.name == "postgresql":
        await db.execute(
            text("SELECT pg_advisory_xact_lock(hashtext(:key))"),
            {"key": f"actuator-electrical-feedback:{actuator.id}"},
        )
    model = await db.scalar(
        select(ActuatorModel)
        .options(selectinload(ActuatorModel.feedback_definitions).selectinload(ActuatorModelFeedbackDefinition.sensor_model))
        .where(ActuatorModel.id == actuator.actuator_model_id)
    )
    if model is None:
        return ElectricalFeedbackProvisionResult(actuator_id=actuator.id)
    definitions = [
        item for item in model.feedback_definitions
        if item.is_enabled and item.feedback_role in {"SUPPLY_VOLTAGE", "RUNNING_CURRENT"}
    ]
    if not definitions:
        return ElectricalFeedbackProvisionResult(actuator_id=actuator.id)
    existing = {
        binding.feedback_role: (binding, sensor, source_device)
        for binding, sensor, source_device in (await db.execute(
            select(ActuatorFeedbackBinding, Sensor, Device)
            .join(Sensor, Sensor.id == ActuatorFeedbackBinding.sensor_id)
            .join(Device, Device.id == Sensor.device_id)
            .where(ActuatorFeedbackBinding.actuator_id == actuator.id)
        )).all()
    }
    sensors_created = bindings_created = bindings_repaired = bindings_migrated = bindings_preserved = 0
    for definition in definitions:
        current = existing.get(definition.feedback_role)
        if current is not None:
            binding, current_sensor, source_device = current
            repairable_generated_binding = (
                current_sensor.purpose == SensorPurpose.ACTUATOR_FEEDBACK
                and (
                    source_device.id != actuator.device_id
                    or source_device.is_deleted
                    or source_device.deleted_at is not None
                    or current_sensor.is_deleted
                    or current_sensor.deleted_at is not None
                )
            )
            # Pre-provenance automatic defaults had no model definition link,
            # default payload metadata and pointed at a generic, cross-device
            # Sensor. Explicit bindings made by the current API carry the
            # definition link and are therefore never rewritten here.
            legacy_automatic_binding = (
                binding.model_feedback_id is None
                and current_sensor.purpose == SensorPurpose.GENERAL
                and source_device.id != actuator.device_id
                and binding.value_key == definition.value_key
                and binding.unit == definition.unit
                and binding.data_type == definition.data_type
                and binding.lower_threshold is None
                and binding.upper_threshold is None
            )
            if repairable_generated_binding or legacy_automatic_binding:
                sensor_code = generated_electrical_sensor_code(actuator.code, definition.feedback_role)
                sensor = await db.scalar(
                    select(Sensor).where(
                        Sensor.device_id == actuator.device_id,
                        Sensor.code == sensor_code,
                        Sensor.is_deleted.is_(False),
                    )
                )
                if sensor is not None and sensor.sensor_model_id != definition.sensor_model_id:
                    raise ValueError(f"Cảm biến {sensor_code} đã tồn tại nhưng không khớp SensorModel cho {definition.feedback_role}")
                if sensor is None:
                    sensor = Sensor(device_id=actuator.device_id, sensor_model_id=definition.sensor_model_id, code=sensor_code, name=f"{actuator.name} · {definition.sensor_model.name}", purpose=SensorPurpose.ACTUATOR_FEEDBACK, lower_threshold=definition.default_lower_threshold, upper_threshold=definition.default_upper_threshold)
                    db.add(sensor)
                    await db.flush()
                    sensors_created += 1
                binding.sensor_id = sensor.id
                binding.model_feedback_id = definition.id
                binding.value_key = definition.value_key
                binding.unit = definition.unit
                binding.data_type = definition.data_type
                binding.updated_by = actor_id
                bindings_repaired += 1
                bindings_migrated += int(legacy_automatic_binding)
                continue
            bindings_preserved += 1
            continue
        sensor_code = generated_electrical_sensor_code(actuator.code, definition.feedback_role)
        sensor = await db.scalar(
            select(Sensor).where(
                Sensor.device_id == actuator.device_id,
                Sensor.code == sensor_code,
                Sensor.is_deleted.is_(False),
            )
        )
        if sensor is not None and sensor.sensor_model_id != definition.sensor_model_id:
            raise ValueError(
                f"Cảm biến {sensor_code} đã tồn tại nhưng không khớp SensorModel cho {definition.feedback_role}"
            )
        if sensor is None:
            sensor = Sensor(
                device_id=actuator.device_id,
                sensor_model_id=definition.sensor_model_id,
                code=sensor_code,
                name=f"{actuator.name} · {definition.sensor_model.name}",
                purpose=SensorPurpose.ACTUATOR_FEEDBACK,
                lower_threshold=definition.default_lower_threshold,
                upper_threshold=definition.default_upper_threshold,
            )
            db.add(sensor)
            await db.flush()
            sensors_created += 1
        db.add(
            ActuatorFeedbackBinding(
                actuator_id=actuator.id,
                sensor_id=sensor.id,
                feedback_role=definition.feedback_role,
                model_feedback_id=definition.id,
                value_key=definition.value_key,
                unit=definition.unit,
                data_type=definition.data_type,
                is_enabled=True,
                created_by=actor_id,
                updated_by=actor_id,
            )
        )
        await db.flush()
        bindings_created += 1
    return ElectricalFeedbackProvisionResult(
        actuator_id=actuator.id,
        sensors_created=sensors_created,
        bindings_created=bindings_created,
        bindings_repaired=bindings_repaired,
        bindings_migrated=bindings_migrated,
        bindings_preserved=bindings_preserved,
    )


async def ensure_device_actuator_electrical_feedback(
    db: AsyncSession, *, device_id: int, actor_id: int | None = None
) -> list[ElectricalFeedbackProvisionResult]:
    actuators = list((await db.scalars(select(Actuator).where(
        Actuator.device_id == device_id,
        Actuator.is_enabled.is_(True),
        Actuator.is_deleted.is_(False),
        Actuator.removed_at.is_(None),
    ))).all())
    return [
        await ensure_actuator_electrical_feedback(db, actuator=actuator, actor_id=actor_id)
        for actuator in actuators
    ]
