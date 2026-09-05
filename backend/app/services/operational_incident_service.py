from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.actuator import Actuator, ActuatorCommand
from app.models.actuator_model import ActuatorModelFeedbackDefinition
from app.models.device import Device
from app.models.operational_alert import (
    ActuatorFeedbackBinding,
    AlertRule,
    AlertRuleActuatorModelProfile,
    AlertRuleActuatorOverride,
    AlertRuleProfile,
    AlertRuleProjectOverride,
    AlertRuleRevision,
    AlertRuleSensorModelProfile,
    AlertRuleSensorOverride,
    NotificationOutbox,
    OperationalIncident,
)
from app.models.project import Project
from app.models.sensor import Sensor
from app.models.sensor_model import SensorModel
from app.models.telemetry import TelemetryReading
from app.services.alert_evaluators import EVALUATOR_REGISTRY, validate_condition_config
from app.services.measurement_quality import classify_measurement_quality
from app.services.sensor_threshold_config import evaluate_sensor_threshold, resolve_sensor_threshold_config

ACTIVE_INCIDENT_STATUSES = ("PENDING", "OPEN", "ACKNOWLEDGED", "NORMALIZED")
BUSINESS_RISK_ORDER = {"LOW": 0, "LOW_MEDIUM": 1, "MEDIUM": 2, "HIGH": 3, "VERY_HIGH": 4, "EXTREME": 5}


async def evaluate_sensor_threshold_incident(
    db: AsyncSession,
    *,
    device: Device,
    sensor: Sensor,
    sensor_model: SensorModel,
    value: float,
    quality: str,
    recorded_at: datetime,
    received_at: datetime,
) -> OperationalIncident | None:
    """Evaluate the Sensor-owned threshold exactly once per accepted reading.

    This deliberately does not read AlertRule: normal measurement semantics,
    messages and risk belong to the Sensor (with catalog defaults materialized
    when the Sensor is provisioned).
    """
    config = resolve_sensor_threshold_config(sensor, sensor_model)
    # A model without an engineering envelope is still valid threshold-bearing
    # runtime telemetry.  Only values that are invalid or outside a declared
    # engineering range must be excluded from operational threshold alerts.
    if not config.alerts_enabled or quality not in {"VALID", "UNVALIDATED"}:
        return None
    evaluation = evaluate_sensor_threshold(value, config)
    direction = evaluation.state if evaluation.state in {"BELOW", "ABOVE"} else None
    threshold = evaluation.threshold
    configured_message = evaluation.message

    project = await db.get(Project, device.project_id)
    if project is None:
        return None
    active_key_prefix = f"sensor:{sensor.id}:threshold:"
    active_incidents = list(
        (await db.scalars(
            select(OperationalIncident)
            .where(
                OperationalIncident.project_id == project.id,
                OperationalIncident.rule_id.is_(None),
                OperationalIncident.context_key.like(f"{active_key_prefix}%"),
                OperationalIncident.status.in_(ACTIVE_INCIDENT_STATUSES),
            )
            .with_for_update()
        )).all()
    )
    if direction is None:
        for incident in active_incidents:
            was_pending = incident.status == "PENDING"
            incident.status = "RESOLVED"
            incident.normalized_at = received_at
            incident.resolved_at = received_at
            if not was_pending:
                await _enqueue(db, incident, "RESOLVED", incident.trigger_snapshot)
        return active_incidents[0] if active_incidents else None

    context_key = f"{active_key_prefix}{direction}"
    incident = next((item for item in active_incidents if item.context_key == context_key), None)
    # Crossing directly from below to above is a recovery of the old condition
    # and an opening of a distinct, direction-specific incident.
    for other in active_incidents:
        if other is not incident:
            was_pending = other.status == "PENDING"
            other.status = "RESOLVED"
            other.normalized_at = received_at
            other.resolved_at = received_at
            if not was_pending:
                await _enqueue(db, other, "RESOLVED", other.trigger_snapshot)

    message = (configured_message or "").strip() or (
        f"{sensor.name} thấp hơn ngưỡng cho phép" if direction == "BELOW"
        else f"{sensor.name} cao hơn ngưỡng cho phép"
    )
    risk = evaluation.risk_level or "MEDIUM"
    snapshot = {
        "incident_type": "SENSOR_THRESHOLD",
        "threshold_direction": direction,
        "message": message,
        "project_code": project.code,
        "project_name": project.name,
        "device_name": device.name,
        "device_code": device.code,
        "sensor_name": sensor.name,
        "sensor_code": sensor.code,
        "value": value,
        "threshold": threshold,
        "operator": "LT" if direction == "BELOW" else "GT",
        "unit": sensor_model.unit,
        "quality": quality,
        "freshness": "FRESH",
        "recorded_at": recorded_at.isoformat(),
        "received_at": received_at.isoformat(),
        "business_risk_level": risk,
    }
    if incident is None:
        delayed = config.delay_seconds > 0
        incident = OperationalIncident(
            project_id=project.id, rule_id=None, rule_revision_id=None,
            device_id=device.id, sensor_id=sensor.id, actuator_id=None,
            context_key=context_key, status="PENDING" if delayed else "OPEN",
            technical_severity="WARNING", business_risk_level_snapshot=risk,
            started_at=received_at, opened_at=None if delayed else received_at,
            last_triggered_at=received_at, occurrence_count=1,
            trigger_snapshot=snapshot,
        )
        try:
            async with db.begin_nested():
                db.add(incident)
                await db.flush()
        except IntegrityError:
            return await db.scalar(
                select(OperationalIncident).where(
                    OperationalIncident.project_id == project.id,
                    OperationalIncident.rule_id.is_(None),
                    OperationalIncident.context_key == context_key,
                    OperationalIncident.status.in_(ACTIVE_INCIDENT_STATUSES),
                ).with_for_update()
            )
        if not delayed:
            await _enqueue(db, incident, "OPEN", snapshot)
        return incident
    incident.last_triggered_at = received_at
    incident.occurrence_count += 1
    incident.trigger_snapshot = snapshot
    incident.technical_severity = "WARNING"
    if incident.status == "PENDING" and received_at >= incident.started_at + timedelta(seconds=config.delay_seconds):
        incident.status = "OPEN"
        incident.opened_at = received_at
        await _enqueue(db, incident, "OPEN", snapshot)
    return incident


def _business_condition_snapshot(rule: AlertRule, config: dict[str, Any]) -> dict[str, Any]:
    """Persist the operator-facing business threshold, not a deeper technical band."""
    bands = config.get("bands")
    if rule.evaluator_type == "RANGE_BANDS" and isinstance(bands, list) and bands:
        broadest = bands[0]
        if isinstance(broadest, dict) and broadest.get("lower") is not None and broadest.get("upper") is not None:
            return {
                "operator": "OUTSIDE",
                "lower": float(broadest["lower"]),
                "upper": float(broadest["upper"]),
                "unit": config.get("unit"),
            }
    return {}


async def evaluate_operational_rules_for_sensor(
    db: AsyncSession,
    *,
    sensor: Sensor,
    value: float,
    quality: str,
    recorded_at: datetime,
    received_at: datetime,
    model_code: str | None = None,
) -> list[int]:
    """Evaluate only rules reached through this Sensor's explicit bindings."""
    published_revision_id = (
        select(AlertRuleRevision.id)
        .where(AlertRuleRevision.rule_id == AlertRule.id, AlertRuleRevision.status == "PUBLISHED")
        .order_by(AlertRuleRevision.revision.desc())
        .limit(1)
        .correlate(AlertRule)
        .scalar_subquery()
    )
    # Sensor AlertRule profiles are legacy configuration. Sensor threshold
    # incidents are evaluated by evaluate_sensor_threshold_incident above;
    # retain this service only for explicit actuator-feedback rule bindings.
    changed: list[int] = []
    latest_command_status = (
        select(ActuatorCommand.status)
        .where(ActuatorCommand.actuator_id == Actuator.id)
        .order_by(ActuatorCommand.requested_at.desc(), ActuatorCommand.id.desc())
        .limit(1)
        .scalar_subquery()
    )
    rows = (
        await db.execute(
            select(ActuatorFeedbackBinding, Actuator, Device, Project, AlertRuleProfile, AlertRule, AlertRuleRevision, AlertRuleProjectOverride, AlertRuleActuatorOverride, ActuatorModelFeedbackDefinition, latest_command_status)
            .join(Actuator, Actuator.id == ActuatorFeedbackBinding.actuator_id)
            .join(Device, Device.id == Actuator.device_id)
            .join(Project, Project.id == Device.project_id)
            .join(AlertRuleActuatorModelProfile, AlertRuleActuatorModelProfile.actuator_model_id == Actuator.actuator_model_id)
            .join(AlertRuleProfile, AlertRuleProfile.id == AlertRuleActuatorModelProfile.profile_id)
            .join(AlertRule, AlertRule.id == AlertRuleProfile.rule_id)
            .join(AlertRuleRevision, AlertRuleRevision.id == published_revision_id)
            .outerjoin(AlertRuleProjectOverride, (AlertRuleProjectOverride.rule_id == AlertRule.id) & (AlertRuleProjectOverride.project_id == Project.id) & AlertRuleProjectOverride.is_enabled.is_(True))
            .outerjoin(AlertRuleActuatorOverride, (AlertRuleActuatorOverride.rule_id == AlertRule.id) & (AlertRuleActuatorOverride.actuator_id == Actuator.id) & AlertRuleActuatorOverride.is_enabled.is_(True))
            .outerjoin(ActuatorModelFeedbackDefinition, ActuatorModelFeedbackDefinition.id == ActuatorFeedbackBinding.model_feedback_id)
            .where(
                ActuatorFeedbackBinding.sensor_id == sensor.id,
                ActuatorFeedbackBinding.is_enabled.is_(True),
                Actuator.is_enabled.is_(True),
                Actuator.is_deleted.is_(False),
                AlertRuleProfile.is_enabled.is_(True),
                AlertRule.is_enabled.is_(True),
                AlertRule.evaluator_type.in_(("ACTUATOR_FEEDBACK", "SCHEDULE_FEEDBACK")),
            )
        )
    ).all()
    for binding, actuator, device, project, profile, rule, revision, project_override, actuator_override, definition, command_status in rows:
        config = {**revision.condition_config, **profile.config, **(project_override.config if project_override else {}), **(actuator_override.config if actuator_override else {})}
        configured_role = str(config.get("feedback_role") or "RUNNING_CURRENT")
        if configured_role != binding.feedback_role:
            continue
        resolved_lower = binding.lower_threshold if binding.lower_threshold is not None else definition.default_lower_threshold if definition else None
        resolved_upper = binding.upper_threshold if binding.upper_threshold is not None else definition.default_upper_threshold if definition else None
        operator = config.get("operator")
        if config.get("threshold") is None:
            config["threshold"] = resolved_lower if operator in {"LT", "LTE"} else resolved_upper if operator in {"GT", "GTE"} else None
        if validate_condition_config(rule.evaluator_type, config):
            continue
        freshness = "FRESH"
        context = {
            "expected_on": bool(actuator.desired_state),
            "reported_state": actuator.reported_state,
            "current_a": value if binding.feedback_role == "RUNNING_CURRENT" else None,
            "voltage_v": value if binding.feedback_role == "SUPPLY_VOLTAGE" else None,
            "feedback_value": value,
            "quality": quality,
            "freshness": freshness,
        }
        result = EVALUATOR_REGISTRY[rule.evaluator_type].evaluate(config, context)
        incident = await _transition_incident(
            db,
            project=project,
            device=device,
            sensor=sensor,
            actuator=actuator,
            rule=rule,
            revision=revision,
            config=config,
            active=result.active,
            severity=result.severity or "WARNING",
            observed_at=received_at,
            snapshot={
                "rule_code": rule.code,
                "rule_name": rule.name,
                "evaluator_type": rule.evaluator_type,
                "message": revision.message_template,
                "consequence": revision.consequence,
                "recommended_action": revision.recommended_action,
                "project_code": project.code,
                "project_name": project.name,
                "device_name": device.name,
                "device_code": device.code,
                "actuator_name": actuator.name,
                "actuator_code": actuator.code,
                "sensor_name": sensor.name,
                "sensor_code": sensor.code,
                "business_risk_level": revision.business_risk_level,
                "desired_state": actuator.desired_state,
                "reported_state": actuator.reported_state,
                "command_status": command_status,
                "feedback_role": binding.feedback_role,
                "feedback_value": value,
                "current_a": value if binding.feedback_role == "RUNNING_CURRENT" else None,
                "voltage_v": value if binding.feedback_role == "SUPPLY_VOLTAGE" else None,
                "minimum_running_current_a": config.get("min_running_current_a"),
                "lower_threshold": resolved_lower,
                "upper_threshold": resolved_upper,
                "unit": binding.unit,
                "quality": quality,
                "freshness": freshness,
                "recorded_at": recorded_at.isoformat(),
                "received_at": received_at.isoformat(),
                **(result.evidence or {}),
            },
        )
        if incident is not None:
            changed.append(incident.id)
    return changed


async def _evaluate_sensor_profiles(
    db: AsyncSession,
    *,
    sensor: Sensor,
    value: float,
    quality: str,
    recorded_at: datetime,
    received_at: datetime,
    model_code: str | None,
) -> list[int]:
    published_revision_id = (
        select(AlertRuleRevision.id)
        .where(AlertRuleRevision.rule_id == AlertRule.id, AlertRuleRevision.status == "PUBLISHED")
        .order_by(AlertRuleRevision.revision.desc())
        .limit(1)
        .correlate(AlertRule)
        .scalar_subquery()
    )
    rows = (
        await db.execute(
            select(Device, Project, AlertRuleProfile, AlertRule, AlertRuleRevision, AlertRuleProjectOverride, AlertRuleSensorOverride)
            .join(Project, Project.id == Device.project_id)
            .join(AlertRuleSensorModelProfile, AlertRuleSensorModelProfile.sensor_model_id == sensor.sensor_model_id)
            .join(AlertRuleProfile, AlertRuleProfile.id == AlertRuleSensorModelProfile.profile_id)
            .join(AlertRule, AlertRule.id == AlertRuleProfile.rule_id)
            .join(AlertRuleRevision, AlertRuleRevision.id == published_revision_id)
            .outerjoin(AlertRuleProjectOverride, (AlertRuleProjectOverride.rule_id == AlertRule.id) & (AlertRuleProjectOverride.project_id == Project.id) & AlertRuleProjectOverride.is_enabled.is_(True))
            .outerjoin(AlertRuleSensorOverride, (AlertRuleSensorOverride.rule_id == AlertRule.id) & (AlertRuleSensorOverride.sensor_id == sensor.id) & AlertRuleSensorOverride.is_enabled.is_(True))
            .where(
                Device.id == sensor.device_id,
                AlertRuleProfile.is_enabled.is_(True),
                AlertRule.is_enabled.is_(True),
                AlertRule.target_type == "SENSOR",
            )
        )
    ).all()
    resolved_model_code = model_code or await db.scalar(select(SensorModel.code).where(SensorModel.id == sensor.sensor_model_id)) or ""
    resolved_rows = []
    for row in rows:
        device, project, profile, rule, revision, project_override, sensor_override = row
        config = {**revision.condition_config, **profile.config, **(project_override.config if project_override else {}), **(sensor_override.config if sensor_override else {})}
        resolved_rows.append((device, project, profile, rule, revision, config))
    maximum_window = max((_history_window_seconds(rule.evaluator_type, config) for _, _, _, rule, _, config in resolved_rows), default=0)
    history_rows = []
    if maximum_window > 0:
        history_rows = list((await db.execute(select(TelemetryReading.value, TelemetryReading.received_at).where(TelemetryReading.sensor_id == sensor.id, TelemetryReading.received_at >= received_at - timedelta(seconds=maximum_window), TelemetryReading.received_at <= received_at).order_by(TelemetryReading.received_at, TelemetryReading.id))).all())
    changed: list[int] = []
    for device, project, profile, rule, revision, config in resolved_rows:
        if validate_condition_config(rule.evaluator_type, config):
            continue
        context = {"value": value, "quality": quality, "freshness": "FRESH"}
        window_seconds = _history_window_seconds(rule.evaluator_type, config)
        if window_seconds > 0:
            window_start = received_at - timedelta(seconds=window_seconds)
            samples = [{"value": float(sample_value), "received_at": sample_at, "quality": classify_measurement_quality(resolved_model_code, float(sample_value))[0]} for sample_value, sample_at in history_rows if sample_at >= window_start]
            span_seconds = (samples[-1]["received_at"] - samples[0]["received_at"]).total_seconds() if len(samples) > 1 else 0
            context.update({"samples": samples, "coverage_ratio": min(1.0, span_seconds / window_seconds)})
        result = EVALUATOR_REGISTRY[rule.evaluator_type].evaluate(config, context)
        incident = await _transition_sensor_incident(
            db,
            project=project,
            device=device,
            sensor=sensor,
            rule=rule,
            revision=revision,
            config=config,
            active=result.active,
            severity=result.severity or "WARNING",
            observed_at=received_at,
            snapshot={"rule_code": rule.code, "rule_name": rule.name, "evaluator_type": rule.evaluator_type, "message": revision.message_template, "consequence": revision.consequence, "recommended_action": revision.recommended_action, "project_code": project.code, "project_name": project.name, "device_name": device.name, "device_code": device.code, "sensor_name": sensor.name, "sensor_code": sensor.code, "business_risk_level": revision.business_risk_level, "value": value, "unit": config.get("unit"), "quality": quality, "freshness": "FRESH", "recorded_at": recorded_at.isoformat(), "received_at": received_at.isoformat(), **(result.evidence or {}), **_business_condition_snapshot(rule, config)},
        )
        if incident is not None:
            changed.append(incident.id)
    return changed


def _history_window_seconds(evaluator_type: str, config: dict[str, Any]) -> int:
    field = "window_seconds" if evaluator_type == "BASELINE_DEVIATION" else "window_duration_seconds" if evaluator_type in {"WINDOW_DURATION", "TREND"} else None
    value = config.get(field) if field else None
    return max(0, int(value)) if value is not None else 0


async def _transition_sensor_incident(
    db: AsyncSession,
    *,
    project: Project,
    device: Device,
    sensor: Sensor,
    rule: AlertRule,
    revision: AlertRuleRevision,
    config: dict[str, Any],
    active: bool,
    severity: str,
    observed_at: datetime,
    snapshot: dict[str, Any],
) -> OperationalIncident | None:
    context_key = f"sensor:{sensor.id}"
    incident = await db.scalar(select(OperationalIncident).where(OperationalIncident.rule_id == rule.id, OperationalIncident.context_key == context_key, OperationalIncident.status.in_(ACTIVE_INCIDENT_STATUSES)).with_for_update())
    if not active:
        if incident is not None and incident.status != "RESOLVED":
            was_pending = incident.status == "PENDING"
            incident.status = "RESOLVED"
            incident.normalized_at = observed_at
            incident.resolved_at = observed_at
            if not was_pending:
                await _enqueue(db, incident, "RESOLVED", snapshot)
        return incident
    if incident is None:
        delayed = rule.evaluator_type == "THRESHOLD_DURATION"
        incident = OperationalIncident(project_id=project.id, rule_id=rule.id, rule_revision_id=revision.id, device_id=device.id, sensor_id=sensor.id, actuator_id=None, context_key=context_key, status="PENDING" if delayed else "OPEN", technical_severity=severity, business_risk_level_snapshot=revision.business_risk_level, started_at=observed_at, opened_at=None if delayed else observed_at, last_triggered_at=observed_at, occurrence_count=1, trigger_snapshot=snapshot)
        try:
            async with db.begin_nested():
                db.add(incident)
                await db.flush()
        except IntegrityError:
            incident = await db.scalar(select(OperationalIncident).where(OperationalIncident.rule_id == rule.id, OperationalIncident.context_key == context_key, OperationalIncident.status.in_(ACTIVE_INCIDENT_STATUSES)).with_for_update())
            return incident
        if not delayed:
            await _enqueue(db, incident, "OPEN", snapshot)
        return incident
    previous_risk = incident.business_risk_level_snapshot
    incident.last_triggered_at = observed_at
    incident.occurrence_count += 1
    incident.trigger_snapshot = snapshot
    if incident.status == "PENDING" and observed_at >= incident.started_at + timedelta(seconds=int(config["duration_seconds"])):
        incident.status = "OPEN"
        incident.opened_at = observed_at
        await _enqueue(db, incident, "OPEN", snapshot)
        return incident
    incident.technical_severity = severity
    if BUSINESS_RISK_ORDER.get(revision.business_risk_level, -1) > BUSINESS_RISK_ORDER.get(previous_risk, -1):
        incident.business_risk_level_snapshot = revision.business_risk_level
        incident.rule_revision_id = revision.id
        await _enqueue(db, incident, "ESCALATED", {**snapshot, "previous_business_risk_level": previous_risk})
    return incident


async def _transition_incident(
    db: AsyncSession,
    *,
    project: Project,
    device: Device,
    sensor: Sensor,
    actuator: Actuator,
    rule: AlertRule,
    revision: AlertRuleRevision,
    config: dict[str, Any],
    active: bool,
    severity: str,
    observed_at: datetime,
    snapshot: dict[str, Any],
) -> OperationalIncident | None:
    context_key = f"actuator:{actuator.id}"
    incident = await db.scalar(
        select(OperationalIncident).where(
            OperationalIncident.rule_id == rule.id,
            OperationalIncident.context_key == context_key,
            OperationalIncident.status.in_(ACTIVE_INCIDENT_STATUSES),
        ).with_for_update()
    )
    # Once an incident is active, require the distinct recovery threshold so
    # samples between open/recovery thresholds cannot flap the state.
    if (
        not active
        and incident is not None
        and snapshot.get("feedback_value") is not None
        and _inside_hysteresis(config, float(snapshot["feedback_value"]))
    ):
        active = True
    if not active:
        if incident is None:
            return None
        recovery_seconds = int(config.get("recovery_duration_seconds", 0))
        if incident.status == "PENDING":
            incident.status = "RESOLVED"
            incident.normalized_at = observed_at
            incident.resolved_at = observed_at
        elif incident.status != "NORMALIZED":
            incident.status = "NORMALIZED"
            incident.normalized_at = observed_at
            await _enqueue(db, incident, "RECOVERED", snapshot)
        elif incident.normalized_at and observed_at >= incident.normalized_at + timedelta(seconds=recovery_seconds):
            incident.status = "RESOLVED"
            incident.resolved_at = observed_at
            await _enqueue(db, incident, "RESOLVED", snapshot)
        return incident

    startup_grace = int(config.get("startup_grace_seconds", 0))
    if actuator.last_command_at and observed_at < actuator.last_command_at + timedelta(seconds=startup_grace):
        return None
    if incident is None:
        incident = OperationalIncident(
            project_id=project.id,
            rule_id=rule.id,
            rule_revision_id=revision.id,
            device_id=device.id,
            sensor_id=sensor.id,
            actuator_id=actuator.id,
            context_key=context_key,
            status="PENDING",
            technical_severity=severity,
            business_risk_level_snapshot=revision.business_risk_level,
            started_at=observed_at,
            last_triggered_at=observed_at,
            occurrence_count=1,
            trigger_snapshot=snapshot,
        )
        try:
            async with db.begin_nested():
                db.add(incident)
                await db.flush()
        except IntegrityError:
            return await db.scalar(select(OperationalIncident).where(OperationalIncident.rule_id == rule.id, OperationalIncident.context_key == context_key, OperationalIncident.status.in_(ACTIVE_INCIDENT_STATUSES)).with_for_update())
        return incident
    previous_risk = incident.business_risk_level_snapshot
    incident.last_triggered_at = observed_at
    incident.occurrence_count += 1
    incident.trigger_snapshot = snapshot
    incident.normalized_at = None
    if incident.status == "NORMALIZED":
        incident.status = "OPEN"
    if incident.status == "PENDING" and observed_at >= incident.started_at + timedelta(seconds=int(config.get("debounce_seconds", 0))):
        incident.status = "OPEN"
        incident.opened_at = observed_at
        await _enqueue(db, incident, "OPEN", snapshot)
    else:
        incident.technical_severity = severity
    if incident.status in {"OPEN", "ACKNOWLEDGED"} and BUSINESS_RISK_ORDER.get(revision.business_risk_level, -1) > BUSINESS_RISK_ORDER.get(previous_risk, -1):
        incident.business_risk_level_snapshot = revision.business_risk_level
        incident.rule_revision_id = revision.id
        await _enqueue(db, incident, "ESCALATED", {**snapshot, "previous_business_risk_level": previous_risk})
    return incident


def _inside_hysteresis(config: dict[str, Any], observed: float) -> bool:
    recovery = config.get("recovery_threshold", config.get("recovery_current_a"))
    if recovery is None:
        return False
    operator = config.get("operator")
    if operator in {"LT", "LTE"} or operator is None:
        return observed < float(recovery)
    if operator in {"GT", "GTE"}:
        return observed > float(recovery)
    return False


async def _enqueue(db: AsyncSession, incident: OperationalIncident, event_type: str, snapshot: dict[str, Any]) -> None:
    key = f"incident:{incident.id}:{event_type}"
    if event_type == "ESCALATED":
        key = f"{key}:{incident.business_risk_level_snapshot}"
    event_at = incident.resolved_at or incident.last_triggered_at
    duration_seconds = max(0, int((event_at - incident.started_at).total_seconds()))
    await db.execute(
        insert(NotificationOutbox)
        .values(
            incident_id=incident.id,
            event_type=event_type,
            idempotency_key=key,
            payload_snapshot={**snapshot, "incident_id": incident.id, "event_type": event_type, "technical_severity": incident.technical_severity, "business_risk_level": incident.business_risk_level_snapshot, "started_at": incident.started_at.isoformat(), "opened_at": incident.opened_at.isoformat() if incident.opened_at else None, "duration_seconds": duration_seconds},
            status="PENDING",
            available_at=datetime.now(UTC),
            attempt_count=0,
        )
        .on_conflict_do_nothing(index_elements=["idempotency_key"])
    )


async def enqueue_incident_notification(db: AsyncSession, incident: OperationalIncident, event_type: str) -> None:
    """Queue a lifecycle notification in the caller's transaction."""
    await _enqueue(db, incident, event_type, incident.trigger_snapshot)
