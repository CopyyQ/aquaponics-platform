from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.actuator import Actuator
from app.models.device import Device
from app.models.operational_alert import (
    AlertRule,
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
from app.services.notification_message_catalog import (
    actuator_catalog_snapshot,
    catalog_snapshot,
    sensor_condition_key,
)
from app.services.threshold_alert_config_service import (
    evaluate_threshold,
    get_actuator_threshold_alert_config,
    get_sensor_threshold_alert_config,
)

ACTIVE_INCIDENT_STATUSES = ("PENDING", "OPEN", "ACKNOWLEDGED")
BUSINESS_RISK_ORDER = {"LOW": 0, "LOW_MEDIUM": 1, "MEDIUM": 2, "HIGH": 3, "VERY_HIGH": 4, "EXTREME": 5}
SIMPLE_SENSOR_THRESHOLD_EVALUATORS = {
    "THRESHOLD", "THRESHOLD_BANDS", "RANGE_BANDS", "THRESHOLD_DURATION",
}


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
    # Invalid data is neither abnormal nor proof of recovery. Keep the current
    # incident untouched until a usable reading arrives.
    if quality not in {"VALID", "UNVALIDATED"}:
        return None
    config = await get_sensor_threshold_alert_config(db, sensor.id)
    evaluation = evaluate_threshold(value, config)
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
    if config is None or not config.enabled or direction is None:
        for incident in active_incidents:
            was_pending = incident.status == "PENDING"
            incident.status = "RESOLVED" if was_pending else "NORMALIZED"
            incident.normalized_at = received_at
            if not was_pending:
                await _enqueue(db, incident, "RECOVERED", incident.trigger_snapshot)
        return active_incidents[0] if active_incidents else None

    context_key = f"{active_key_prefix}{direction}"
    incident = next((item for item in active_incidents if item.context_key == context_key), None)
    # Crossing directly from below to above is a recovery of the old condition
    # and an opening of a distinct, direction-specific incident.
    for other in active_incidents:
        if other is not incident:
            was_pending = other.status == "PENDING"
            other.status = "RESOLVED" if was_pending else "NORMALIZED"
            other.normalized_at = received_at
            if not was_pending:
                await _enqueue(db, other, "RECOVERED", other.trigger_snapshot)

    # A canonical threshold must carry its own delivery risk.  Do not invent
    # business meaning in the notification path or from a service constant.
    risk = evaluation.risk_level
    if risk is None:
        return None
    condition_key = sensor_condition_key(sensor_model.code, direction)
    message_catalog = catalog_snapshot(condition_key)
    message = (configured_message or "").strip() or str(message_catalog["title"])
    snapshot = {
        **message_catalog,
        "incident_type": "SENSOR_THRESHOLD",
        "resource_type": "SENSOR",
        "resource_name": sensor.name,
        "metric_type": "SENSOR_VALUE",
        "threshold_direction": direction,
        "message": message,
        "consequence": evaluation.consequence,
        "recommended_actions": evaluation.recommended_actions,
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


async def reevaluate_latest_sensor_threshold(
    db: AsyncSession, *, device: Device, sensor: Sensor, observed_at: datetime | None = None
) -> OperationalIncident | None:
    """Reconcile a saved canonical config against the latest persisted value."""
    reading = await db.scalar(
        select(TelemetryReading)
        .where(TelemetryReading.sensor_id == sensor.id)
        .order_by(TelemetryReading.recorded_at.desc(), TelemetryReading.id.desc())
        .limit(1)
    )
    if reading is None:
        return None
    sensor_model = await db.get(SensorModel, sensor.sensor_model_id)
    if sensor_model is None:
        return None
    quality = classify_measurement_quality(sensor_model.code, reading.value)[0]
    return await evaluate_sensor_threshold_incident(
        db,
        device=device,
        sensor=sensor,
        sensor_model=sensor_model,
        value=reading.value,
        quality=quality,
        recorded_at=reading.recorded_at,
        received_at=observed_at or datetime.now(UTC),
    )


async def evaluate_actuator_composite_incident(
    db: AsyncSession, *, device: Device, actuator: Actuator,
    recorded_at: datetime, received_at: datetime,
) -> OperationalIncident | None:
    """Evaluate mutually exclusive ON electrical faults from model capability."""
    model = None
    if actuator.actuator_model_id is not None:
        from app.models.actuator_model import ActuatorModel
        model = await db.get(ActuatorModel, actuator.actuator_model_id)
    prefix = f"actuator:{actuator.id}:composite:"
    active = list((await db.scalars(select(OperationalIncident).where(
        OperationalIncident.project_id == device.project_id,
        OperationalIncident.rule_id.is_(None),
        OperationalIncident.context_key.like(f"{prefix}%"),
        OperationalIncident.status.in_(ACTIVE_INCIDENT_STATUSES),
    ).with_for_update())).all())
    condition_key: str | None = None
    if (
        actuator.electrical_alerts_enabled and actuator.reported_state is True and model is not None
        and actuator.voltage_v is not None and actuator.current_a is not None
        and model.minimum_running_current_a is not None
    ):
        current_is_low = actuator.current_a < model.minimum_running_current_a
        if model.zero_voltage_max_v is not None and actuator.voltage_v <= model.zero_voltage_max_v and current_is_low:
            condition_key = "ACTUATOR_ON_NO_POWER"
        elif (
            model.nominal_voltage_v is not None and model.voltage_tolerance_v is not None
            and abs(actuator.voltage_v - model.nominal_voltage_v) <= model.voltage_tolerance_v
            and current_is_low
        ):
            condition_key = "ACTUATOR_ON_NO_LOAD"
    incident = next((item for item in active if item.context_key == f"{prefix}{condition_key}"), None)
    for other in active:
        if condition_key is None or other is not incident:
            was_pending = other.status == "PENDING"
            other.status = "RESOLVED" if was_pending else "NORMALIZED"
            other.normalized_at = received_at
            if not was_pending:
                await _enqueue(db, other, "RECOVERED", other.trigger_snapshot)
    if condition_key is None or model is None:
        return active[0] if active else None
    content = actuator_catalog_snapshot(condition_key, model.code)
    risk = "EXTREME" if condition_key == "ACTUATOR_ON_NO_POWER" else "VERY_HIGH"
    snapshot = {
        **content,
        "incident_type": "ACTUATOR_COMPOSITE",
        "resource_type": "ACTUATOR",
        "resource_name": actuator.name,
        "metric_type": "ELECTRICAL_STATE",
        "message": content["title"],
        "project_name": (await db.get(Project, device.project_id)).name,
        "device_name": device.name,
        "device_code": device.code,
        "actuator_name": actuator.name,
        "actuator_code": actuator.code,
        "desired_state": actuator.desired_state,
        "reported_state": actuator.reported_state,
        "voltage_v": actuator.voltage_v,
        "current_a": actuator.current_a,
        "recorded_at": recorded_at.isoformat(),
        "received_at": received_at.isoformat(),
        "business_risk_level": risk,
    }
    if incident is None:
        incident = OperationalIncident(
            project_id=device.project_id, rule_id=None, rule_revision_id=None,
            device_id=device.id, sensor_id=None, actuator_id=actuator.id,
            context_key=f"{prefix}{condition_key}", status="OPEN",
            technical_severity="CRITICAL" if risk == "EXTREME" else "WARNING",
            business_risk_level_snapshot=risk, started_at=received_at,
            opened_at=received_at, last_triggered_at=received_at,
            occurrence_count=1, trigger_snapshot=snapshot,
        )
        db.add(incident)
        await db.flush()
        await _enqueue(db, incident, "OPEN", snapshot)
    else:
        incident.last_triggered_at = received_at
        incident.occurrence_count += 1
        incident.trigger_snapshot = snapshot
    return incident


async def evaluate_alert_scenarios_for_actuator(
    db: AsyncSession, *, device: Device, actuator: Actuator,
    recorded_at: datetime, received_at: datetime,
) -> list[int]:
    """Evaluate user scenarios against one coherent Actuator runtime snapshot."""
    from app.models.operational_alert import AlertRuleActuatorOverride

    rows = (await db.execute(
        select(AlertRule, AlertRuleRevision)
        .join(AlertRuleActuatorOverride, AlertRuleActuatorOverride.rule_id == AlertRule.id)
        .join(AlertRuleRevision, AlertRuleRevision.id == AlertRule.current_revision_id)
        .where(AlertRuleActuatorOverride.actuator_id == actuator.id,
               AlertRuleActuatorOverride.is_enabled.is_(True), AlertRule.target_type == "ACTUATOR",
               AlertRule.evaluator_type == "MULTI_CONDITION", AlertRule.retired_at.is_(None))
    )).all()
    changed: list[int] = []
    project = await db.get(Project, device.project_id)
    if project is None:
        return changed
    context = {"reported_state": actuator.reported_state, "desired_state": actuator.desired_state,
               "voltage_v": actuator.voltage_v, "current_a": actuator.current_a}
    for rule, revision in rows:
        config = revision.condition_config
        active = rule.is_enabled and not validate_condition_config("MULTI_CONDITION", config) and EVALUATOR_REGISTRY["MULTI_CONDITION"].evaluate(config, context).active
        key = f"actuator:{actuator.id}:rule:{rule.id}"
        incident = await db.scalar(select(OperationalIncident).where(
            OperationalIncident.rule_id == rule.id, OperationalIncident.context_key == key,
            OperationalIncident.status.in_(ACTIVE_INCIDENT_STATUSES)).with_for_update())
        snapshot = {"incident_type": "ALERT_SCENARIO", "resource_type": "ACTUATOR",
            "scenario_id": str(rule.public_id), "scenario_name": rule.name, "rule_code": rule.code,
            "message": revision.message_template, "consequence": revision.consequence,
            "recommended_action": revision.recommended_action, "business_risk_level": revision.business_risk_level,
            "project_name": project.name, "device_name": device.name, "device_code": device.code,
            "actuator_name": actuator.name, "actuator_code": actuator.code,
            **context, "recorded_at": recorded_at.isoformat(), "received_at": received_at.isoformat()}
        if not active:
            if incident is not None:
                was_pending = incident.status == "PENDING"
                incident.status = "RESOLVED" if was_pending else "NORMALIZED"
                incident.normalized_at = received_at
                if not was_pending:
                    await _enqueue(db, incident, "RECOVERED", snapshot)
                changed.append(incident.id)
            continue
        if incident is None:
            duration = int(config.get("duration_seconds", 0))
            incident = OperationalIncident(project_id=project.id, rule_id=rule.id, rule_revision_id=revision.id,
                device_id=device.id, sensor_id=None, actuator_id=actuator.id, context_key=key,
                status="PENDING" if duration > 0 else "OPEN", technical_severity="WARNING",
                business_risk_level_snapshot=revision.business_risk_level, started_at=received_at,
                opened_at=None if duration > 0 else received_at, last_triggered_at=received_at,
                occurrence_count=1, trigger_snapshot=snapshot)
            db.add(incident); await db.flush()
            if duration == 0: await _enqueue(db, incident, "OPEN", snapshot)
        else:
            incident.last_triggered_at = received_at; incident.occurrence_count += 1; incident.trigger_snapshot = snapshot
            if incident.status == "PENDING" and received_at >= incident.started_at + timedelta(seconds=int(config.get("duration_seconds", 0))):
                incident.status = "OPEN"; incident.opened_at = received_at
                await _enqueue(db, incident, "OPEN", snapshot)
        changed.append(incident.id)
    return changed


async def evaluate_actuator_threshold_incident(
    db: AsyncSession, *, device: Device, actuator: Actuator, metric_type: str,
    value: float | None, recorded_at: datetime, received_at: datetime,
) -> OperationalIncident | None:
    """Evaluate one direct Actuator electrical metric from its canonical config."""
    config = await get_actuator_threshold_alert_config(db, actuator.id, metric_type)
    if config is None or not config.enabled:
        return None
    evaluation = evaluate_threshold(value, config)
    direction = evaluation.state if evaluation.state in {"BELOW", "ABOVE"} else None
    prefix = f"actuator:{actuator.id}:{metric_type}:threshold:"
    active = list((await db.scalars(select(OperationalIncident).where(
        OperationalIncident.project_id == device.project_id,
        OperationalIncident.rule_id.is_(None), OperationalIncident.context_key.like(f"{prefix}%"),
        OperationalIncident.status.in_(ACTIVE_INCIDENT_STATUSES),
    ).with_for_update())).all())
    if direction is None:
        for item in active:
            item.status, item.normalized_at, item.resolved_at = "RESOLVED", received_at, received_at
            await _enqueue(db, item, "RESOLVED", item.trigger_snapshot)
        return active[0] if active else None
    if evaluation.risk_level is None:
        return None
    context_key = f"{prefix}{direction}"
    incident = next((item for item in active if item.context_key == context_key), None)
    for item in active:
        if item is not incident:
            item.status, item.normalized_at, item.resolved_at = "RESOLVED", received_at, received_at
            await _enqueue(db, item, "RESOLVED", item.trigger_snapshot)
    snapshot = {
        "incident_type": "ACTUATOR_THRESHOLD", "resource_type": "ACTUATOR",
        "resource_name": actuator.name, "metric_type": metric_type,
        "threshold_direction": direction, "message": evaluation.message,
        "project_name": (await db.get(Project, device.project_id)).name,
        "device_name": device.name, "device_code": device.code,
        "actuator_name": actuator.name, "actuator_code": actuator.code,
        "value": value, "threshold": evaluation.threshold,
        "unit": "V" if metric_type == "VOLTAGE" else "A", "quality": "VALID",
        "freshness": "FRESH", "recorded_at": recorded_at.isoformat(),
        "received_at": received_at.isoformat(), "business_risk_level": evaluation.risk_level,
    }
    if incident is None:
        incident = OperationalIncident(project_id=device.project_id, rule_id=None, rule_revision_id=None,
            device_id=device.id, sensor_id=None, actuator_id=actuator.id, context_key=context_key,
            status="OPEN", technical_severity="WARNING", business_risk_level_snapshot=evaluation.risk_level,
            started_at=received_at, opened_at=received_at, last_triggered_at=received_at,
            occurrence_count=1, trigger_snapshot=snapshot)
        db.add(incident)
        await db.flush()
        await _enqueue(db, incident, "OPEN", snapshot)
    else:
        incident.last_triggered_at, incident.occurrence_count, incident.trigger_snapshot = received_at, incident.occurrence_count + 1, snapshot
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
    """Evaluate optional Sensor model profiles; actuator electrical alerts use Actuator readings."""
    changed = await _evaluate_sensor_profiles(
        db,
        sensor=sensor,
        value=value,
        quality=quality,
        recorded_at=recorded_at,
        received_at=received_at,
        model_code=model_code,
    )
    changed.extend(await _evaluate_sensor_scenarios(
        db, sensor=sensor, value=value, quality=quality,
        recorded_at=recorded_at, received_at=received_at,
    ))
    return changed


async def _evaluate_sensor_scenarios(
    db: AsyncSession, *, sensor: Sensor, value: float, quality: str,
    recorded_at: datetime, received_at: datetime,
) -> list[int]:
    rows = (await db.execute(select(Device, Project, AlertRule, AlertRuleRevision)
        .join(Project, Project.id == Device.project_id)
        .join(AlertRuleSensorOverride, AlertRuleSensorOverride.sensor_id == sensor.id)
        .join(AlertRule, AlertRule.id == AlertRuleSensorOverride.rule_id)
        .join(AlertRuleRevision, AlertRuleRevision.id == AlertRule.current_revision_id)
        .where(Device.id == sensor.device_id, AlertRule.target_type == "SENSOR",
               AlertRule.retired_at.is_(None), AlertRuleSensorOverride.is_enabled.is_(True)))).all()
    changed: list[int] = []
    for device, project, rule, revision in rows:
        config = revision.condition_config
        result = EVALUATOR_REGISTRY[rule.evaluator_type].evaluate(
            config, {"value": value, "quality": quality, "freshness": "FRESH"})
        incident = await _transition_sensor_incident(db, project=project, device=device, sensor=sensor,
            rule=rule, revision=revision, config=config, active=rule.is_enabled and result.active,
            severity=result.severity or "WARNING", observed_at=received_at,
            snapshot={"incident_type": "ALERT_SCENARIO", "resource_type": "SENSOR",
                "scenario_id": str(rule.public_id), "scenario_name": rule.name, "rule_code": rule.code,
                "message": revision.message_template, "consequence": revision.consequence,
                "recommended_action": revision.recommended_action, "business_risk_level": revision.business_risk_level,
                "project_name": project.name, "device_name": device.name, "device_code": device.code,
                "sensor_name": sensor.name, "sensor_code": sensor.code, "value": value,
                "quality": quality, "recorded_at": recorded_at.isoformat(), "received_at": received_at.isoformat(),
                **(result.evidence or {})})
        if incident is not None: changed.append(incident.id)
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
    # Simple Sensor lower/upper meaning belongs exclusively to
    # ThresholdAlertConfig. Keep advanced rule evaluators available, but make
    # a future accidental caller unable to create a second semantic Incident.
    if rule.evaluator_type in SIMPLE_SENSOR_THRESHOLD_EVALUATORS and rule.code.startswith("CATALOG_"):
        canonical_config = await get_sensor_threshold_alert_config(db, sensor.id)
        if canonical_config is not None:
            return None
    context_key = f"sensor:{sensor.id}:rule:{rule.id}"
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
        delayed = int(config.get("duration_seconds", 0)) > 0
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
    if incident.status == "PENDING" and observed_at >= incident.started_at + timedelta(seconds=int(config.get("duration_seconds", 0))):
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
            project_id=incident.project_id,
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
