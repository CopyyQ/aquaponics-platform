from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.actuator import Actuator, ActuatorCommand
from app.models.operational_alert import OperationalIncident
from app.models.device import Device
from app.models.scada_dashboard import ScadaDashboard
from app.models.sensor import Sensor
from app.models.telemetry import TelemetryReading


async def project_scada_devices(db: AsyncSession, project_id: int) -> list[Device]:
    return list(
        (
            await db.scalars(
                select(Device)
                .options(
                    selectinload(Device.device_template),
                    selectinload(Device.sensors).selectinload(Sensor.sensor_model),
                    selectinload(Device.actuators).joinedload(Actuator.actuator_model),
                )
                .where(
                    Device.project_id == project_id,
                    Device.is_deleted.is_(False),
                    Device.deleted_at.is_(None),
                )
                .order_by(Device.id)
            )
        ).all()
    )


async def latest_sensor_readings(
    db: AsyncSession, sensor_ids: list[int]
) -> list[TelemetryReading]:
    if not sensor_ids:
        return []
    ranked = (
        select(
            TelemetryReading.id.label("reading_id"),
            func.row_number()
            .over(
                partition_by=TelemetryReading.sensor_id,
                order_by=(
                    TelemetryReading.recorded_at.desc(),
                    TelemetryReading.id.desc(),
                ),
            )
            .label("row_number"),
        )
        .where(TelemetryReading.sensor_id.in_(sensor_ids))
        .subquery()
    )
    return list(
        (
            await db.scalars(
                select(TelemetryReading)
                .join(ranked, ranked.c.reading_id == TelemetryReading.id)
                .where(ranked.c.row_number == 1)
            )
        ).all()
    )


async def latest_actuator_commands(
    db: AsyncSession, actuator_ids: list[int]
) -> list[ActuatorCommand]:
    if not actuator_ids:
        return []
    ranked = (
        select(
            ActuatorCommand.id.label("command_id"),
            func.row_number()
            .over(
                partition_by=ActuatorCommand.actuator_id,
                order_by=(
                    ActuatorCommand.requested_at.desc(),
                    ActuatorCommand.id.desc(),
                ),
            )
            .label("row_number"),
        )
        .where(ActuatorCommand.actuator_id.in_(actuator_ids))
        .subquery()
    )
    return list(
        (
            await db.scalars(
                select(ActuatorCommand)
                .join(ranked, ranked.c.command_id == ActuatorCommand.id)
                .where(ranked.c.row_number == 1)
            )
        ).all()
    )


async def open_project_alerts(
    db: AsyncSession, project_id: int
) -> list[OperationalIncident]:
    return list(
        (
            await db.scalars(
                select(OperationalIncident)
                .where(
                    OperationalIncident.project_id == project_id,
                    OperationalIncident.status.in_(("PENDING", "OPEN", "ACKNOWLEDGED")),
                )
                .order_by(OperationalIncident.started_at.desc(), OperationalIncident.id.desc())
            )
        ).all()
    )


async def latest_scada_dashboard(
    db: AsyncSession, project_id: int, status: str
) -> ScadaDashboard | None:
    return await db.scalar(
        select(ScadaDashboard)
        .where(
            ScadaDashboard.project_id == project_id,
            ScadaDashboard.status == status,
        )
        .order_by(ScadaDashboard.version.desc(), ScadaDashboard.id.desc())
        .limit(1)
    )


async def next_scada_dashboard_version(db: AsyncSession, project_id: int) -> int:
    current = await db.scalar(
        select(func.max(ScadaDashboard.version)).where(
            ScadaDashboard.project_id == project_id
        )
    )
    return int(current or 0) + 1
