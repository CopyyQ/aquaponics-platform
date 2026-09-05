from datetime import datetime, timedelta, timezone

from sqlalchemy import and_, column, func, literal, select, table, true
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from app.core.enums import AggregatePeriod, SensorPurpose
from app.models.actuator import Actuator, ActuatorCommand, ActuatorStateHistory
from app.models.actuator_model import ActuatorModelFeedbackDefinition
from app.models.device import Device
from app.models.device_template import DeviceTemplate
from app.models.operational_alert import (
    ActuatorFeedbackBinding,
    AlertRule,
    AlertRuleActuatorOverride,
    AlertRuleProfile,
    AlertRuleProjectOverride,
    OperationalIncident,
)
from app.models.sensor import Sensor
from app.models.sensor_model import SensorModel
from app.models.telemetry import TelemetryAggregate, TelemetryReading


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
                    Sensor.purpose == SensorPurpose.GENERAL,
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
    """Resolve voltage/current feedback and latest readings in one Project query."""
    latest_reading = (
        select(
            TelemetryReading.value.label("feedback_value"),
            TelemetryReading.recorded_at.label("recorded_at"),
            TelemetryReading.received_at.label("received_at"),
        )
        .where(TelemetryReading.sensor_id == ActuatorFeedbackBinding.sensor_id)
        .order_by(TelemetryReading.received_at.desc(), TelemetryReading.id.desc())
        .limit(1)
        .lateral("latest_feedback_reading")
    )
    actuator_profile_links = table(
        "alert_rule_actuator_model_profiles", column("profile_id"), column("actuator_model_id")
    )
    profile = (
        select(
            AlertRuleProfile.config.label("profile_config"),
            AlertRuleProjectOverride.config.label("project_override_config"),
            AlertRuleActuatorOverride.config.label("actuator_override_config"),
            AlertRule.id.label("profile_rule_id"),
        )
        .select_from(AlertRuleProfile)
        .join(
            actuator_profile_links,
            actuator_profile_links.c.profile_id == AlertRuleProfile.id,
        )
        .join(AlertRule, AlertRule.id == AlertRuleProfile.rule_id)
        .outerjoin(AlertRuleProjectOverride, (AlertRuleProjectOverride.rule_id == AlertRule.id) & (AlertRuleProjectOverride.project_id == Device.project_id) & AlertRuleProjectOverride.is_enabled.is_(True))
        .outerjoin(AlertRuleActuatorOverride, (AlertRuleActuatorOverride.rule_id == AlertRule.id) & (AlertRuleActuatorOverride.actuator_id == Actuator.id) & AlertRuleActuatorOverride.is_enabled.is_(True))
        .where(
            actuator_profile_links.c.actuator_model_id == Actuator.actuator_model_id,
            AlertRuleProfile.is_enabled.is_(True),
            AlertRule.is_enabled.is_(True),
            AlertRule.evaluator_type.in_(("ACTUATOR_FEEDBACK", "SCHEDULE_FEEDBACK")),
        )
        .order_by(AlertRule.id)
        .limit(1)
        .lateral("resolved_current_profile")
    )
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
        .join(AlertRule, AlertRule.id == OperationalIncident.rule_id)
        .where(
            OperationalIncident.actuator_id == Actuator.id,
            OperationalIncident.status.in_(("PENDING", "OPEN", "ACKNOWLEDGED", "NORMALIZED")),
        )
        .order_by(OperationalIncident.started_at.desc())
        .limit(1)
        .lateral("active_operational_incident")
    )
    source_device = aliased(Device)
    query = (
        select(
            Actuator.id,
            ActuatorFeedbackBinding.sensor_id,
            ActuatorFeedbackBinding.feedback_role,
            SensorModel.code.label("sensor_model_code"),
            Sensor.code.label("sensor_code"),
            Sensor.name.label("sensor_name"),
            source_device.id.label("source_device_id"),
            source_device.code.label("source_device_code"),
            source_device.name.label("source_device_name"),
            ActuatorFeedbackBinding.value_key,
            ActuatorFeedbackBinding.lower_threshold,
            ActuatorFeedbackBinding.upper_threshold,
            ActuatorModelFeedbackDefinition.default_lower_threshold,
            ActuatorModelFeedbackDefinition.default_upper_threshold,
            latest_reading.c.feedback_value,
            latest_reading.c.recorded_at,
            latest_reading.c.received_at,
            profile.c.profile_config,
            profile.c.project_override_config,
            profile.c.actuator_override_config,
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
        .outerjoin(ActuatorFeedbackBinding, and_(ActuatorFeedbackBinding.actuator_id == Actuator.id, ActuatorFeedbackBinding.is_enabled.is_(True)))
        .outerjoin(Sensor, Sensor.id == ActuatorFeedbackBinding.sensor_id)
        .outerjoin(source_device, source_device.id == Sensor.device_id)
        .outerjoin(SensorModel, SensorModel.id == Sensor.sensor_model_id)
        .outerjoin(ActuatorModelFeedbackDefinition, ActuatorModelFeedbackDefinition.id == ActuatorFeedbackBinding.model_feedback_id)
        .outerjoin(latest_reading, true())
        .outerjoin(profile, true())
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
            Sensor.purpose == SensorPurpose.GENERAL,
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


async def device_power_series_rows(
    db: AsyncSession,
    *,
    project_id: int,
    device_id: int,
    start: datetime,
    end: datetime,
    bucket_size: timedelta,
):
    epoch = datetime(1970, 1, 1, tzinfo=timezone.utc)
    bucket = func.date_bin(
        literal(bucket_size), TelemetryReading.recorded_at, literal(epoch)
    ).label("bucket_time")
    return (
        await db.execute(
            select(
                bucket,
                func.avg(TelemetryReading.value).label("avg_value"),
                func.min(TelemetryReading.value).label("min_value"),
                func.max(TelemetryReading.value).label("max_value"),
                func.count(TelemetryReading.id).label("reading_count"),
            )
            .join(Sensor, Sensor.id == TelemetryReading.sensor_id)
            .join(Device, Device.id == Sensor.device_id)
            .join(DeviceTemplate, DeviceTemplate.id == Device.device_template_id)
            .join(SensorModel, SensorModel.id == Sensor.sensor_model_id)
            .where(
                Device.id == device_id,
                Device.project_id == project_id,
                Device.is_deleted.is_(False),
                DeviceTemplate.device_kind == "ENERGY_MONITOR",
                Sensor.is_deleted.is_(False),
                SensorModel.code == "POWER_W",
                # Raw out-of-engineering-range values remain stored for
                # diagnosis, but must never affect the operational chart.
                TelemetryReading.value.between(0, 100000),
                TelemetryReading.recorded_at.between(start, end),
            )
            .group_by(bucket)
            .order_by(bucket)
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
