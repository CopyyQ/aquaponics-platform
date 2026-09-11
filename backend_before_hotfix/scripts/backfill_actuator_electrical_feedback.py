"""Reconcile enabled actuator feedback from persisted ActuatorModel defaults.

Run with ``python scripts/backfill_actuator_electrical_feedback.py --dry-run``
first.  The command deliberately contains no project/device identifiers.
"""

from __future__ import annotations

import argparse
import asyncio

from sqlalchemy import select

from app.db.session import AsyncSessionLocal, engine
from app.models.actuator import Actuator
from app.models.device import Device
from app.services.actuator_electrical_feedback_service import ensure_actuator_electrical_feedback


async def run(*, dry_run: bool) -> dict[str, int]:
    totals = {"actuators_scanned": 0, "sensors_created": 0, "bindings_created": 0, "bindings_repaired": 0, "bindings_migrated": 0, "bindings_preserved": 0, "errors": 0}
    async with AsyncSessionLocal() as db:
        actuators = list((await db.scalars(select(Actuator).join(Device, Device.id == Actuator.device_id).where(
            Actuator.is_enabled.is_(True),
            Actuator.is_deleted.is_(False),
            Actuator.removed_at.is_(None),
            Device.is_deleted.is_(False),
            Device.deleted_at.is_(None),
        ).order_by(Actuator.id))).all())
        for actuator in actuators:
            totals["actuators_scanned"] += 1
            try:
                result = await ensure_actuator_electrical_feedback(db, actuator=actuator)
                totals["sensors_created"] += result.sensors_created
                totals["bindings_created"] += result.bindings_created
                totals["bindings_repaired"] += result.bindings_repaired
                totals["bindings_migrated"] += result.bindings_migrated
                totals["bindings_preserved"] += result.bindings_preserved
            except ValueError:
                totals["errors"] += 1
        if dry_run:
            await db.rollback()
        else:
            await db.commit()
    await engine.dispose()
    return totals


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="Report changes then roll them back")
    args = parser.parse_args()
    print(asyncio.run(run(dry_run=args.dry_run)))


if __name__ == "__main__":
    main()
