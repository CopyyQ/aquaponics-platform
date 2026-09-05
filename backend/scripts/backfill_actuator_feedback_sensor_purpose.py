"""Mark only verifiably auto-generated actuator feedback sensors as internal."""

from __future__ import annotations

import argparse
import asyncio

from sqlalchemy import select

from app.core.enums import SensorPurpose
from app.db.session import AsyncSessionLocal, engine
from app.models.actuator import Actuator
from app.models.operational_alert import ActuatorFeedbackBinding
from app.models.sensor import Sensor
from app.services.actuator_electrical_feedback_service import generated_electrical_sensor_code


async def run(*, dry_run: bool) -> dict[str, int]:
    totals = {"bindings_scanned": 0, "classified": 0, "already_internal": 0, "ambiguous": 0}
    async with AsyncSessionLocal() as db:
        rows = (await db.execute(select(Actuator, ActuatorFeedbackBinding, Sensor)
            .join(ActuatorFeedbackBinding, ActuatorFeedbackBinding.actuator_id == Actuator.id)
            .join(Sensor, Sensor.id == ActuatorFeedbackBinding.sensor_id)
            .where(ActuatorFeedbackBinding.feedback_role.in_(("SUPPLY_VOLTAGE", "RUNNING_CURRENT"))))).all()
        for actuator, binding, sensor in rows:
            totals["bindings_scanned"] += 1
            expected = generated_electrical_sensor_code(actuator.code, binding.feedback_role)
            if sensor.device_id != actuator.device_id or sensor.code != expected:
                totals["ambiguous"] += 1
                continue
            if sensor.purpose == SensorPurpose.ACTUATOR_FEEDBACK:
                totals["already_internal"] += 1
                continue
            sensor.purpose = SensorPurpose.ACTUATOR_FEEDBACK
            totals["classified"] += 1
        if dry_run:
            await db.rollback()
        else:
            await db.commit()
    await engine.dispose()
    return totals


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true")
    print(asyncio.run(run(dry_run=parser.parse_args().dry_run)))


if __name__ == "__main__":
    main()
