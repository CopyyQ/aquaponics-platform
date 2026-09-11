from datetime import datetime, timedelta, timezone

from sqlalchemy import and_, func, literal, select, true
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from app.core.enums import AggregatePeriod
from app.models.actuator import Actuator, ActuatorCommand, ActuatorStateHistory
from app.models.device import Device
from app.models.operational_alert import (
    AlertRule,
    OperationalIncident,
)
from app.models.sensor import Sensor
from app.models.sensor_model import SensorModel
from app.models.telemetry import TelemetryAggregate, TelemetryReading
from app.models.threshold_alert_config import ThresholdAlertConfig


async def latest_project_sensor_rows(db: AsyncSession, project_id: int):
    latest_reading = (
        select(
            TelemetryReading.value.label("value"),
            TelemetryReading.recorded_at.label("recorded_at"),
            TelemetryReading.received_at.label("received_at"),
        )
        .where(TelemetryReading.sensor_id == Sensor.id)
        .order_by(TelemetryReading.recorded_at.desc(), TelemetryReading.id.desc())
        .limit(1)
        .lateral("latest_reading")
    )
    return (
        await db.execute(
            select(
                Device,
                Sensor,
                SensorModel,
                latest_reading.c.value,
                latest_reading.c.recorded_at,
                latest_reading.c.received_at,
            )
            .select_from(Device)
            .outerjoin(
                Sensor,
                and_(
                    Sensor.device_id == Device.id,
                    Sensor.is_deleted.is_(False),
                    Sensor.deleted_at.is_(None),
                    Sensor.is_enabled.is_(True),
                ),
            )
            .outerjoin(SensorModel, SensorModel.id == Sensor.sensor_model_id)
            .outerjoin(latest_reading, true())
            .where(
                Device.project_id == project_id,
                Device.is_deleted.is_(False),
                Device.deleted_at.is_(None),
                Device.is_enabled.is_(True),
            )
            .order_by(Device.name, Sensor.name.nulls_last())
        )
    ).all()


async def latest_project_actuator_rows(db: AsyncSession, project_id: int):
    latest_command = (
        select(
            ActuatorCommand.status.label("status"),
            ActuatorCommand.requested_at.label("requested_at"),
        )
        .where(ActuatorCommand.actuator_id == Actuator.id)
        .order_by(ActuatorCommand.requested_at.desc(), ActuatorCommand.id.desc())
        .limit(1)
        .lateral("latest_command")
    )
    return (
        await db.execute(
            select(
                Device.id,
                Actuator,
                latest_command.c.status,
                latest_command.c.requested_at,
            )
            .join(Actuator, Actuator.device_id == Device.id)
            .outerjoin(latest_command, true())
            .where(
                Device.project_id == project_id,
                Device.is_enabled.is_(True),
                Device.is_deleted.is_(False),
                Device.deleted_at.is_(None),
                Actuator.is_enabled.is_(True),
                Actuator.is_deleted.is_(False),
                Actuator.deleted_at.is_(None),
                Actuator.removed_at.is_(None),
            )
            .order_by(Device.name, Actuator.name)
        )
    ).all()


async def latest_project_actuator_electrical_rows(db: AsyncSession, project_id: int, *, include_disabled: bool = False):
    """Read canonical actuator electrical snapshots and threshold policy."""
    voltage_config = aliased(ThresholdAlertConfig)
    current_config = aliased(ThresholdAlertConfig)
    active_incident = (
        select(
            OperationalIncident.id.label("incident_id"),
            OperationalIncident.technical_severity.label("incident_severity"),
            OperationalIncident.business_risk_level_snapshot.label("incident_risk"),
            OperationalIncident.status.label("incident_status"),
            OperationalIncident.started_at.label("incident_started_at"),
            OperationalIncident.trigger_snapshot.label("incident_trigger_snapshot"),
            AlertRule.name.label("incident_rule_name"),
            AlertRule.evaluator_type.label("incident_evaluator_type"),
        )
        .outerjoin(AlertRule, AlertRule.id == OperationalIncident.rule_id)
        .where(
            OperationalIncident.actuator_id == Actuator.id,
            OperationalIncident.status.in_(("PENDING", "OPEN", "ACKNOWLEDGED")),
        )
        .order_by(OperationalIncident.started_at.desc())
        .limit(1)
        .lateral("active_operational_incident")
    )
    query = (
        select(
            Actuator.id,
            Actuator.voltage_v,
            Actuator.current_a,
            Actuator.electrical_recorded_at,
            Actuator.electrical_received_at,
            voltage_config.enabled.label("voltage_alerts_enabled"),
            voltage_config.lower_threshold.label("voltage_lower_threshold"),
            voltage_config.upper_threshold.label("voltage_upper_threshold"),
            current_config.enabled.label("current_alerts_enabled"),
            current_config.lower_threshold.label("current_lower_threshold"),
            current_config.upper_threshold.label("current_upper_threshold"),
            active_incident.c.incident_id,
            active_incident.c.incident_severity,
            active_incident.c.incident_risk,
            active_incident.c.incident_status,
            active_incident.c.incident_started_at,
            active_incident.c.incident_trigger_snapshot,
            active_incident.c.incident_rule_name,
            active_incident.c.incident_evaluator_type,
        )
        .join(Device, Device.id == Actuator.device_id)
        .outerjoin(voltage_config, and_(voltage_config.actuator_id == Actuator.id, voltage_config.metric_type == "VOLTAGE"))
        .outerjoin(current_config, and_(current_config.actuator_id == Actuator.id, current_config.metric_type == "CURRENT"))
        .outerjoin(active_incident, true())
        .where(Device.project_id == project_id, Device.is_enabled.is_(True), Device.is_deleted.is_(False), Actuator.is_deleted.is_(False), Actuator.removed_at.is_(None))
        .order_by(Actuator.id)
    )
    if not include_disabled:
        query = query.where(Actuator.is_enabled.is_(True))
    return (await db.execute(query)).all()


async def project_sensor_metadata_rows(
    db: AsyncSession, project_id: int, device_id: int | None = None
):
    query = (
        select(Sensor.id, SensorModel.unit)
        .join(Device, Device.id == Sensor.device_id)
        .join(SensorModel, SensorModel.id == Sensor.sensor_model_id)
        .where(
            Device.project_id == project_id,
            Device.is_enabled.is_(True),
            Device.is_deleted.is_(False),
            Device.deleted_at.is_(None),
            Sensor.is_enabled.is_(True),
            Sensor.is_deleted.is_(False),
            Sensor.deleted_at.is_(None),
        )
        .order_by(Sensor.id)
    )
    if device_id is not None:
        query = query.where(Device.id == device_id)
    return (
        await db.execute(query)
    ).all()


async def project_series_rows(
    db: AsyncSession,
    *,
    project_id: int,
    sensor_ids: list[int],
    start: datetime,
    end: datetime,
    resolution: str,
):
    if not sensor_ids:
        return []
    scoped_ids = select(Sensor.id).join(Device, Device.id == Sensor.device_id).where(
        Device.project_id == project_id,
        Device.is_enabled.is_(True),
        Device.is_deleted.is_(False),
        Sensor.is_enabled.is_(True),
        Sensor.is_deleted.is_(False),
        Sensor.id.in_(sensor_ids),
    )
    if resolution == "raw":
        return (
            await db.execute(
                select(
                    TelemetryReading.sensor_id,
                    TelemetryReading.recorded_at,
                    TelemetryReading.value,
                )
                .where(
                    TelemetryReading.sensor_id.in_(scoped_ids),
                    TelemetryReading.recorded_at.between(start, end),
                )
                .order_by(TelemetryReading.sensor_id, TelemetryReading.recorded_at)
            )
        ).all()
    if resolution in {"5m", "10m", "15m", "1h"}:
        bucket_size = (
            timedelta(hours=1)
            if resolution == "1h"
            else timedelta(minutes={"5m": 5, "10m": 10, "15m": 15}[resolution])
        )
        epoch = datetime(1970, 1, 1, tzinfo=timezone.utc)
        bucket = func.date_bin(
            literal(bucket_size),
            TelemetryReading.recorded_at,
            literal(epoch),
        ).label("bucket_time")
        return (
            await db.execute(
                select(
                    TelemetryReading.sensor_id,
                    bucket,
                    func.avg(TelemetryReading.value),
                )
                .where(
                    TelemetryReading.sensor_id.in_(scoped_ids),
                    TelemetryReading.recorded_at.between(start, end),
                )
                .group_by(TelemetryReading.sensor_id, bucket)
                .order_by(TelemetryReading.sensor_id, bucket)
            )
        ).all()
    period = AggregatePeriod.DAY
    return (
        await db.execute(
            select(
                TelemetryAggregate.sensor_id,
                TelemetryAggregate.bucket_time,
                TelemetryAggregate.avg_value,
            )
            .where(
                TelemetryAggregate.sensor_id.in_(scoped_ids),
                TelemetryAggregate.period == period,
                TelemetryAggregate.bucket_time.between(start, end),
            )
            .order_by(TelemetryAggregate.sensor_id, TelemetryAggregate.bucket_time)
        )
    ).all()


async def device_actuator_history_rows(
    db: AsyncSession,
    *,
    project_id: int,
    device_id: int,
    start: datetime,
    end: datetime,
):
    actuator_ids = select(Actuator.id).join(Device, Device.id == Actuator.device_id).where(
        Device.id == device_id,
        Device.project_id == project_id,
        Device.is_enabled.is_(True),
        Device.is_deleted.is_(False),
        Device.deleted_at.is_(None),
        Actuator.is_enabled.is_(True),
        Actuator.is_deleted.is_(False),
        Actuator.deleted_at.is_(None),
        Actuator.removed_at.is_(None),
    )
    return (
        await db.execute(
            select(
                ActuatorStateHistory.actuator_id,
                ActuatorStateHistory.recorded_at,
                ActuatorStateHistory.state,
            )
            .where(
                ActuatorStateHistory.actuator_id.in_(actuator_ids),
                ActuatorStateHistory.recorded_at.between(start, end),
            )
            .order_by(
                ActuatorStateHistory.actuator_id,
                ActuatorStateHistory.recorded_at,
                ActuatorStateHistory.id,
            )
        )
    ).all()
