from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func, select

from app.core.enums import DeviceStatus, MonitoringRange, SensorStatus
from app.core.config import settings
from app.core.enums import AlertSeverity, AlertStatus, ProjectStatus
from app.models.alert import SensorAlert
from app.models.operational_alert import AlertRule, OperationalIncident
from app.models.project_member import ProjectMember
from app.models.sensor import Sensor
from app.models.device import Device
from app.services.measurement_quality import classify_measurement_quality
from app.services.sensor_threshold_config import evaluate_sensor_threshold, resolve_sensor_threshold_config
from app.queries.monitoring_queries import (
    device_actuator_history_rows,
    latest_project_actuator_electrical_rows,
    latest_project_actuator_rows,
    latest_project_sensor_rows,
    project_sensor_metadata_rows,
    project_series_rows,
)

# Engineering validity is deliberately separate from configurable operational
# thresholds. These are conservative catalog fallbacks until a model-specific
def _quality(model_code: str, value: float | None) -> tuple[str, str | None, float | None, float | None]:
    return classify_measurement_quality(model_code, value)


def _actuator_sync(desired: bool | None, reported: bool | None, command: str | None) -> str:
    """Compare persisted states only; command lifecycle is a separate axis."""
    if reported is None:
        return "UNKNOWN"
    return "IN_SYNC" if desired == reported else "OUT_OF_SYNC"


def _relevant_command_status(
    *,
    desired: bool | None,
    reported: bool | None,
    command_status: str | None,
    command_requested_at: datetime | None,
    last_reported_at: datetime | None,
) -> str | None:
    if command_status not in {"FAILED", "TIMEOUT"}:
        return command_status
    if (
        desired is not None
        and desired == reported
        and last_reported_at is not None
        and command_requested_at is not None
        and last_reported_at > command_requested_at
    ):
        return None
    return command_status


def _electrical_threshold_status(*, configured: bool, value: float | None, quality: str, freshness: str, lower: float | None, upper: float | None) -> str:
    if not configured:
        return "UNCONFIGURED"
    if freshness == "NO_DATA":
        return "NO_DATA"
    if freshness == "STALE":
        return "STALE"
    if quality != "VALID" or value is None:
        return "INVALID"
    if lower is not None and value < lower:
        return "BELOW_RANGE"
    if upper is not None and value > upper:
        return "ABOVE_RANGE"
    return "IN_RANGE"


@dataclass(frozen=True)
class MonitoringRangeConfig:
    duration: timedelta
    resolution: str


MONITORING_RANGE_CONFIG = {
    MonitoringRange.ONE_HOUR: MonitoringRangeConfig(timedelta(hours=1), "raw"),
    MonitoringRange.SIX_HOURS: MonitoringRangeConfig(timedelta(hours=6), "5m"),
    MonitoringRange.TWELVE_HOURS: MonitoringRangeConfig(timedelta(hours=12), "10m"),
    MonitoringRange.TWENTY_FOUR_HOURS: MonitoringRangeConfig(timedelta(hours=24), "15m"),
    MonitoringRange.THIRTY_DAYS: MonitoringRangeConfig(timedelta(days=30), "1d"),
}


async def get_project_monitoring_summary(
    db: AsyncSession,
    project_id: int,
    *,
    project_status: ProjectStatus | str = ProjectStatus.ACTIVE,
) -> dict:
    """Build the operational dashboard read model with batched project queries."""
    now = datetime.now(timezone.utc)
    stale_seconds = settings.device_offline_seconds
    rows = await latest_project_sensor_rows(db, project_id)
    alert_rows = (
        await db.execute(
            select(SensorAlert, Sensor, Device)
            .join(Sensor, Sensor.id == SensorAlert.sensor_id)
            .join(Device, Device.id == Sensor.device_id)
            .where(
                Device.project_id == project_id,
                Device.is_enabled.is_(True),
                Device.is_deleted.is_(False),
                Sensor.is_enabled.is_(True),
                Sensor.is_deleted.is_(False),
            )
            .order_by(
                SensorAlert.status != AlertStatus.RESOLVED,
                SensorAlert.severity == AlertSeverity.CRITICAL,
                SensorAlert.started_at.desc(),
            )
            .limit(50)
        )
    ).all()
    actuator_rows = await latest_project_actuator_rows(db, project_id)
    electrical_rows = await latest_project_actuator_electrical_rows(db, project_id)
    incident_rows = (
        await db.execute(
            select(OperationalIncident, AlertRule)
            .outerjoin(AlertRule, AlertRule.id == OperationalIncident.rule_id)
            .where(
                OperationalIncident.project_id == project_id,
                OperationalIncident.status.in_(("PENDING", "OPEN", "ACKNOWLEDGED")),
            )
            .order_by(OperationalIncident.started_at.asc(), OperationalIncident.id.asc())
        )
    ).all()
    electrical_by_actuator: dict[int, list] = defaultdict(list)
    for row in electrical_rows:
        electrical_by_actuator[row[0]].append(row)
    members_total = int(
        await db.scalar(select(func.count(ProjectMember.id)).where(ProjectMember.project_id == project_id)) or 0
    )

    devices: dict[int, dict] = {}
    measurements: dict[str, dict] = {}
    sensor_details: dict[int, dict] = {}
    sensor_issues: list[dict] = []
    attention: list[dict] = []
    last_received_at: datetime | None = None
    reporting = stale = offline_sensors = 0
    for device, sensor, model, value, recorded_at, received_at in rows:
        device_item = devices.setdefault(device.id, {
            "id": device.id, "code": device.code, "name": device.name,
            "status": device.status, "is_enabled": device.is_enabled,
            "last_seen_at": device.last_seen_at, "sensor_count": 0,
            "actuator_count": 0,
            "reporting_sensor_count": 0, "stale_sensor_count": 0,
            "offline_sensor_count": 0, "open_alert_count": 0,
        })
        if sensor is None or model is None:
            continue
        threshold_config = resolve_sensor_threshold_config(sensor, model)
        threshold_evaluation = evaluate_sensor_threshold(float(value) if value is not None else None, threshold_config)
        device_item["sensor_count"] += 1
        has_latest = value is not None and recorded_at is not None
        freshness_at = received_at or recorded_at
        age = (now - freshness_at).total_seconds() if freshness_at is not None else None
        is_stale = age is not None and age > stale_seconds
        sensor_offline = device.status == "OFFLINE" or sensor.status == "OFFLINE"
        quality, quality_reason, engineering_min, engineering_max = _quality(
            model.code, float(value) if has_latest else None
        )
        freshness = "NO_DATA" if not has_latest else "STALE" if is_stale or sensor_offline else "FRESH"
        detail = {
            "id": sensor.id,
            "name": sensor.name,
            "code": sensor.code,
            "model_code": model.code,
            "unit": model.unit,
            "device_id": device.id,
            "device_name": device.name,
            "device_code": device.code,
            "value": float(value) if value is not None else None,
            "quality": quality,
            "freshness": freshness,
            "connection_lost": sensor_offline,
            "recorded_at": recorded_at,
            "received_at": received_at,
        }
        sensor_details[sensor.id] = detail
        if freshness != "FRESH":
            sensor_issues.append(detail)
        if has_latest:
            last_received_at = max(last_received_at, freshness_at) if last_received_at else freshness_at
        if has_latest and not is_stale and not sensor_offline:
            reporting += 1
            device_item["reporting_sensor_count"] += 1
        if is_stale:
            stale += 1
            device_item["stale_sensor_count"] += 1
        if sensor_offline:
            offline_sensors += 1
            device_item["offline_sensor_count"] += 1
        if sensor_offline:
            attention.append({"id": f"sensor-offline-{sensor.id}", "severity": "WARNING", "title": "Cảm biến mất kết nối", "description": sensor.name, "device_id": device.id, "sensor_id": sensor.id, "last_seen_at": recorded_at})
        elif not has_latest:
            attention.append({"id": f"sensor-no-data-{sensor.id}", "severity": "WARNING", "title": "Cảm biến chưa có dữ liệu", "description": sensor.name, "device_id": device.id, "sensor_id": sensor.id})
        elif is_stale:
            attention.append({"id": f"sensor-stale-{sensor.id}", "severity": "WARNING", "title": "Dữ liệu cảm biến đã cũ", "description": sensor.name, "device_id": device.id, "sensor_id": sensor.id, "last_seen_at": recorded_at})

        group = measurements.setdefault(model.code, {"model_code": model.code, "name": model.name, "unit": model.unit, "values": [], "latest_at": None, "sensor_id": sensor.id, "device_id": device.id, "counter": model.measurement_semantics == "COUNTER", "stale": True, "quality": quality, "quality_reason": quality_reason, "engineering_min": engineering_min, "engineering_max": engineering_max})
        if quality == "OUT_OF_RANGE":
            attention.append({"id": f"sensor-quality-{sensor.id}", "severity": "HIGH", "title": f"Dữ liệu {sensor.name} không hợp lệ", "description": f"Nhận được {value} {model.unit}; {quality_reason}", "device_id": device.id, "sensor_id": sensor.id, "last_seen_at": recorded_at})
        if has_latest and not is_stale and quality in {"VALID", "UNVALIDATED"}:
            group["values"].append(float(value))
            group["stale"] = False
            if group["latest_at"] is None or recorded_at > group["latest_at"]:
                group["latest_at"] = recorded_at
                group["latest_value"] = float(value)

    open_alerts = [row for row in alert_rows if row[0].status != AlertStatus.RESOLVED]
    for alert, sensor, device in open_alerts:
        devices.setdefault(device.id, {"id": device.id, "code": device.code, "name": device.name, "status": device.status, "is_enabled": device.is_enabled, "last_seen_at": device.last_seen_at, "sensor_count": 0, "actuator_count": 0, "reporting_sensor_count": 0, "stale_sensor_count": 0, "offline_sensor_count": 0, "open_alert_count": 0})["open_alert_count"] += 1
        if alert.severity == AlertSeverity.CRITICAL:
            attention.append({"id": f"alert-{alert.id}", "severity": "CRITICAL", "title": "Cảnh báo nghiêm trọng", "description": alert.message, "device_id": device.id, "sensor_id": sensor.id, "last_seen_at": alert.started_at})
        elif len(attention) < 20:
            attention.append({"id": f"alert-{alert.id}", "severity": "WARNING", "title": "Cảnh báo đang mở", "description": alert.message, "device_id": device.id, "sensor_id": sensor.id, "last_seen_at": alert.started_at})

    critical_open = sum(row[0].severity == AlertSeverity.CRITICAL for row in open_alerts)
    warning_open = sum(row[0].severity == AlertSeverity.WARNING for row in open_alerts)
    enabled_devices = list(devices.values())
    offline_devices = sum(item["status"] == "OFFLINE" for item in enabled_devices)
    waiting_devices = sum(item["status"] == "WAITING_CONNECTION" for item in enabled_devices)
    expected = sum(item["sensor_count"] for item in enabled_devices)
    if project_status != ProjectStatus.ACTIVE:
        health_status, health_label = "WARNING", "Dự án không hoạt động"
        reasons = [{"code": "PROJECT_INACTIVE", "severity": "WARNING", "message": "Dự án không ở trạng thái hoạt động."}]
    elif not enabled_devices or expected == 0 or reporting == 0:
        health_status, health_label = "NO_DATA", "Chưa có dữ liệu"
        reasons = [{"code": "NO_DATA", "severity": "WARNING", "message": "Dự án chưa có dữ liệu telemetry hợp lệ."}]
    elif critical_open or (enabled_devices and offline_devices == len(enabled_devices)):
        health_status, health_label = "CRITICAL", "Nghiêm trọng"
        reasons = [{"code": "CRITICAL_ALERTS", "severity": "CRITICAL", "message": f"{critical_open} cảnh báo nghiêm trọng đang mở."}] if critical_open else [{"code": "DEVICES_OFFLINE", "severity": "CRITICAL", "message": "Toàn bộ thiết bị đang ngoại tuyến."}]
    elif warning_open or offline_devices or offline_sensors or stale:
        health_status, health_label = "WARNING", "Cần chú ý"
        reasons = [{"code": "ATTENTION", "severity": "WARNING", "message": f"{len(attention)} vấn đề cần xử lý."}]
    else:
        health_status, health_label, reasons = "HEALTHY", "Ổn định", []
    attention.sort(key=lambda item: (item["severity"] != "CRITICAL", item["title"]))
    measurement_groups = []
    for group in measurements.values():
        values = group.pop("values")
        group.update({"reporting_sensors": len(values), "expected_sensors": sum(1 for row in rows if row[2] is not None and row[2].code == group["model_code"]), "latest_value": group.get("latest_value"), "minimum_value": min(values) if values and not group["counter"] else None, "maximum_value": max(values) if values and not group["counter"] else None})
        measurement_groups.append(group)
    actuator_health = []
    for device_id, actuator, command_status, requested_at in actuator_rows:
        devices[device_id]["actuator_count"] += 1
        relevant_command_status = _relevant_command_status(
            desired=actuator.desired_state,
            reported=actuator.reported_state,
            command_status=command_status,
            command_requested_at=requested_at,
            last_reported_at=actuator.last_reported_at,
        )
        sync = _actuator_sync(
            actuator.desired_state, actuator.reported_state, relevant_command_status
        )
        connection = "DISABLED" if not actuator.is_enabled else ("DISCONNECTED" if devices.get(device_id, {}).get("status") == "OFFLINE" else "CONNECTED" if actuator.last_reported_at else "UNKNOWN")
        electrical_row = electrical_by_actuator.get(actuator.id, [])
        electrical = _actuator_electrical_payload(electrical_row, now)
        conclusion = _actuator_operational_conclusion(
            actuator.desired_state,
            actuator.reported_state,
            relevant_command_status,
            electrical,
        )
        active_incident = electrical.pop("active_incident")
        actuator_item = {
            "id": actuator.id,
            "code": actuator.code,
            "device_id": device_id,
            "device_name": devices[device_id]["name"],
            "device_code": devices[device_id]["code"],
            "name": actuator.name,
            "actuator_model": actuator.actuator_model.name if actuator.actuator_model else None,
            "is_enabled": actuator.is_enabled,
            "connection_status": connection,
            "desired_state": actuator.desired_state,
            "reported_state": actuator.reported_state,
            "synchronization_status": sync,
            "command_status": command_status,
            "relevant_command_status": relevant_command_status,
            "last_command_at": actuator.last_command_at,
            "last_ack_at": None,
            "last_reported_at": actuator.last_reported_at,
            "latest_command": {"status": command_status, "requested_at": requested_at} if command_status else None,
            "electrical": electrical,
            "operational_conclusion": conclusion,
            "active_incident": active_incident,
        }
        actuator_health.append(actuator_item)
        if sync == "OUT_OF_SYNC":
            attention.append({"id": f"actuator-{actuator.id}", "severity": "HIGH", "title": f"Cơ cấu chấp hành {actuator.name} chưa đồng bộ", "description": "Trạng thái yêu cầu khác trạng thái báo về.", "device_id": device_id, "sensor_id": None, "last_seen_at": actuator.last_reported_at})
    attention.sort(key=lambda item: (item["severity"] not in {"CRITICAL"}, item["severity"] != "HIGH", not bool(item.get("actionable", True)), -(item.get("last_seen_at").timestamp() if item.get("last_seen_at") else 0), item["id"]))
    failed_actuators = [
        item
        for item in actuator_health
        if item["connection_status"] == "DISCONNECTED"
        or item["active_incident"] is not None
        or item["relevant_command_status"] in {"FAILED", "TIMEOUT"}
    ]
    waiting_actuators = [
        item
        for item in actuator_health
        if item not in failed_actuators
        and (
            item["synchronization_status"] in {"OUT_OF_SYNC", "PENDING", "UNKNOWN"}
            or item["relevant_command_status"] in {"PENDING", "PUBLISHED"}
        )
    ]
    actuator_inventory = {
        "total": len(actuator_health),
        "responding": len(actuator_health) - len(failed_actuators) - len(waiting_actuators),
        "out_of_sync": len(waiting_actuators),
        "disconnected": sum(item["connection_status"] == "DISCONNECTED" for item in actuator_health),
        "failed": len(failed_actuators),
    }
    if failed_actuators:
        health_status, health_label = "CRITICAL", "Nghiêm trọng"
    elif any(item["quality"] == "OUT_OF_RANGE" for item in measurement_groups):
        health_status, health_label = "WARNING", "Cần chú ý"
    risk_counts = {
        risk: 0
        for risk in ("EXTREME", "VERY_HIGH", "HIGH", "MEDIUM", "LOW_MEDIUM", "LOW")
    }
    active_incidents = []
    actuators_by_id = {item["id"]: item for item in actuator_health}
    for incident, rule in incident_rows:
        risk = incident.business_risk_level_snapshot
        if risk in risk_counts:
            risk_counts[risk] += 1
        evidence = incident.trigger_snapshot or {}
        sensor = sensor_details.get(incident.sensor_id) or {}
        actuator = actuators_by_id.get(incident.actuator_id) or {}
        electrical = actuator.get("electrical") or {}
        active_incidents.append({
            "id": incident.id,
            "risk": risk,
            "rule_name": evidence.get("rule_name") or (rule.name if rule else None) or "Ngưỡng cảm biến",
            "started_at": incident.started_at,
            "duration_seconds": max(0, int((now - incident.started_at).total_seconds())),
            "message": evidence.get("message") or evidence.get("content") or _incident_condition_summary(evidence),
            "condition": _incident_condition_summary(evidence),
            "value": evidence.get("value"),
            "unit": evidence.get("unit") or sensor.get("unit"),
            "device_name": evidence.get("device_name") or sensor.get("device_name") or actuator.get("device_name"),
            "device_code": evidence.get("device_code") or sensor.get("device_code") or actuator.get("device_code"),
            "sensor_name": evidence.get("sensor_name") or sensor.get("name"),
            "sensor_code": evidence.get("sensor_code") or sensor.get("code"),
            "actuator_name": evidence.get("actuator_name") or actuator.get("name"),
            "actuator_code": evidence.get("actuator_code") or actuator.get("code"),
            "desired_state": evidence.get("desired_state", actuator.get("desired_state")),
            "reported_state": evidence.get("reported_state", actuator.get("reported_state")),
            "current_a": evidence.get("current_a", electrical.get("current_a")),
            "lower": evidence.get("lower"), "upper": evidence.get("upper"),
            "threshold": evidence.get("threshold"), "operator": evidence.get("operator"),
        })
    return {"project_id": project_id, "health": {"status": health_status, "label": health_label, "reasons": reasons}, "inventory": {"devices_total": len(enabled_devices), "devices_enabled": len(enabled_devices), "devices_online": len(enabled_devices) - offline_devices - waiting_devices, "devices_offline": offline_devices, "devices_waiting": waiting_devices, "sensors_total": expected, "sensors_enabled": expected, "sensors_reporting": reporting, "sensors_stale": stale, "sensors_offline": offline_sensors, "members_total": members_total}, "alerts": {"open_total": len(open_alerts), "critical_open": critical_open, "warning_open": warning_open}, "business_alerts": {"counts": risk_counts, "items": active_incidents}, "freshness": {"last_received_at": last_received_at, "reporting_sensors": reporting, "expected_sensors": expected, "coverage_ratio": round(reporting / expected, 4) if expected else 0}, "attention": attention[:8], "sensor_issues": sensor_issues, "measurement_groups": measurement_groups, "device_health": enabled_devices, "recent_alerts": [{"id": alert.id, "sensor_id": sensor.id, "sensor_name": sensor.name, "device_id": device.id, "device_name": device.name, "severity": alert.severity, "status": alert.status, "message": alert.message, "trigger_value": alert.trigger_value, "condition_active": alert.condition_active, "normalized_at": alert.normalized_at, "resolved_by_user_id": alert.resolved_by_user_id, "started_at": alert.started_at} for alert, sensor, device in alert_rows[:8]], "actuators": actuator_health, "actuator_inventory": actuator_inventory}


def _actuator_electrical_payload(rows: list, now: datetime) -> dict:
    row = rows[0]._mapping if rows else None

    def metric(kind: str, unit: str) -> dict:
        if row is None:
            return {"configured": False, "sensor_id": None, "sensor_code": None, "sensor_name": None, "sensor_model_code": None, "source_device_id": None, "source_device_code": None, "source_device_name": None, "value_key": None, "value": None, "unit": unit, "quality": "NO_DATA", "freshness": "NO_DATA", "recorded_at": None, "received_at": None, "lower_threshold": None, "upper_threshold": None, "threshold_source": "NONE", "threshold_status": "UNCONFIGURED"}
        raw_value = row[f"{kind}_v"] if kind == "voltage" else row["current_a"]
        recorded_at, received_at = row["electrical_recorded_at"], row["electrical_received_at"]
        numeric = float(raw_value) if raw_value is not None else None
        quality = "VALID" if numeric is not None else "NO_DATA"
        freshness = "NO_DATA" if received_at is None else "STALE" if (now - received_at).total_seconds() > settings.device_offline_seconds else "FRESH"
        lower, upper = row[f"{kind}_lower_threshold"], row[f"{kind}_upper_threshold"]
        configured = numeric is not None or lower is not None or upper is not None
        threshold_status = _electrical_threshold_status(configured=configured, value=numeric, quality=quality, freshness=freshness, lower=lower, upper=upper)
        return {
            "configured": configured, "sensor_id": None, "sensor_code": None, "sensor_name": None,
            "sensor_model_code": None, "value_key": f"{kind}_v" if kind == "voltage" else "current_a",
            "source_device_id": None, "source_device_code": None, "source_device_name": None,
            "value": numeric, "unit": unit,
            "quality": quality, "freshness": freshness,
            "recorded_at": recorded_at, "received_at": received_at,
            "lower_threshold": lower, "upper_threshold": upper,
            "threshold_source": "ACTUATOR" if lower is not None or upper is not None else "NONE", "threshold_status": threshold_status,
        }

    current = metric("current", "A")
    voltage = metric("voltage", "V")
    incident_row = next((row._mapping for row in rows if row._mapping["incident_id"] is not None), None)
    incident = None
    if incident_row is not None:
        incident_id, incident_severity, incident_risk, incident_status, incident_started_at, incident_snapshot, incident_rule_name, incident_evaluator_type = (incident_row["incident_id"], incident_row["incident_severity"], incident_row["incident_risk"], incident_row["incident_status"], incident_row["incident_started_at"], incident_row["incident_trigger_snapshot"], incident_row["incident_rule_name"], incident_row["incident_evaluator_type"])
        incident = {"id": incident_id, "technical_severity": incident_severity, "business_risk_level": incident_risk, "status": incident_status, "rule_name": incident_rule_name, "evaluator_type": incident_evaluator_type, "condition_summary": _incident_condition_summary(incident_snapshot or {}), "started_at": incident_started_at, "duration_seconds": max(0, int((now - incident_started_at).total_seconds())) if incident_started_at else 0, "evidence": incident_snapshot or {}}
    return {
        "voltage": voltage, "current": current,
        # Compatibility fields retained while overview consumers migrate.
        "configured": current["configured"], "sensor_id": current["sensor_id"],
        "current_a": current["value"], "quality": current["quality"], "freshness": current["freshness"],
        "recorded_at": current["recorded_at"], "received_at": current["received_at"],
        "current_lower_threshold": current["lower_threshold"], "current_upper_threshold": current["upper_threshold"],
        "active_incident": incident,
    }


def _incident_condition_summary(snapshot: dict) -> str:
    if snapshot.get("actuator_name"):
        if snapshot.get("operator") == "GT":
            return "Cơ cấu được yêu cầu chạy nhưng dòng điện vượt ngưỡng vận hành."
        return "Cơ cấu được yêu cầu chạy nhưng dòng điện dưới ngưỡng vận hành."
    operator = {"LT": "thấp hơn", "LTE": "thấp hơn hoặc bằng", "GT": "cao hơn", "GTE": "cao hơn hoặc bằng", "OUTSIDE": "nằm ngoài"}.get(snapshot.get("operator"), "vi phạm")
    if snapshot.get("threshold") is not None:
        return f"Giá trị cảm biến {operator} ngưỡng kích hoạt."
    if snapshot.get("lower") is not None and snapshot.get("upper") is not None:
        lower = f"{float(snapshot['lower']):g}".replace(".", ",")
        upper = f"{float(snapshot['upper']):g}".replace(".", ",")
        unit = f" {snapshot['unit']}" if snapshot.get("unit") else ""
        return f"< {lower} hoặc > {upper}{unit}"
    return str(snapshot.get("message") or "Điều kiện cảnh báo đang hoạt động.")


def _actuator_operational_conclusion(desired: bool | None, reported: bool | None, command_status: str | None, electrical: dict) -> dict:
    incident = electrical.get("active_incident")
    if incident and incident.get("technical_severity") == "CRITICAL":
        return {"code": "CRITICAL_INCIDENT", "label": "Có cảnh báo vận hành nghiêm trọng", "explanation": incident.get("condition_summary") or "Cần kiểm tra cảnh báo đang mở."}
    if command_status in {"FAILED", "TIMEOUT"}:
        return {"code": f"COMMAND_{command_status}", "label": "Lệnh điều khiển thất bại" if command_status == "FAILED" else "Lệnh điều khiển hết thời gian chờ", "explanation": "Trạng thái lệnh gần nhất cần được kiểm tra."}
    abnormal = next((metric for metric in (electrical["voltage"], electrical["current"]) if metric["threshold_status"] in {"BELOW_RANGE", "ABOVE_RANGE"}), None)
    if desired and abnormal is not None:
        return {"code": f"ELECTRICAL_{abnormal['threshold_status']}", "label": "Thông số điện ngoài ngưỡng vận hành", "explanation": "Điện áp hoặc dòng điện đang vượt khoảng đã cấu hình."}
    if not electrical["configured"]:
        return {"code": "CURRENT_NOT_CONFIGURED", "label": "Chưa đủ dữ liệu điện để xác minh hoạt động", "explanation": "Hãy liên kết cảm biến dòng điện với cơ cấu chấp hành."}
    if electrical["freshness"] == "NO_DATA":
        return {"code": "CURRENT_NO_DATA", "label": "Không thể xác nhận trạng thái điện", "explanation": "Chưa nhận được dữ liệu dòng điện."}
    if electrical["freshness"] == "STALE":
        return {"code": "CURRENT_STALE", "label": "Không thể xác nhận trạng thái điện", "explanation": "Dữ liệu dòng điện đã cũ."}
    if electrical["quality"] != "VALID":
        return {"code": "CURRENT_INVALID", "label": "Không thể xác nhận trạng thái điện", "explanation": "Dữ liệu dòng điện không hợp lệ hoặc ngoài phạm vi."}
    threshold = electrical["minimum_running_current_a"]
    maximum = electrical["maximum_running_current_a"]
    if desired is False and threshold is not None and electrical["current_a"] >= threshold:
        return {"code": "CURRENT_WHILE_OFF", "label": "Có dòng điện khi yêu cầu tắt", "explanation": "Phản hồi điện cho thấy cơ cấu có thể vẫn đang chạy."}
    if desired and threshold is None:
        return {"code": "THRESHOLD_NOT_CONFIGURED", "label": "Thiếu ngưỡng vận hành", "explanation": "Chưa cấu hình dòng chạy tối thiểu cho model."}
    if desired and electrical["current_a"] < threshold:
        return {"code": "CURRENT_TOO_LOW", "label": "Không hoạt động đúng yêu cầu", "explanation": "Cơ cấu đang được yêu cầu chạy nhưng dòng điện dưới ngưỡng vận hành."}
    if desired and maximum is not None and electrical["current_a"] > maximum:
        return {"code": "CURRENT_TOO_HIGH", "label": "Dòng điện vượt ngưỡng vận hành", "explanation": "Cơ cấu đang chạy với dòng điện cao hơn giới hạn đã cấu hình."}
    if desired and reported:
        return {"code": "RUNNING_NORMALLY", "label": "Đang hoạt động bình thường", "explanation": "Trạng thái báo về và dòng điện đều phù hợp."}
    return {"code": "NOT_RUNNING", "label": "Không chạy", "explanation": "Cơ cấu hiện không được xác nhận đang chạy."}


def sensor_connection_status(
    device_status: DeviceStatus,
    sensor_status: SensorStatus,
    has_telemetry: bool,
) -> SensorStatus:
    if not has_telemetry:
        return SensorStatus.WAITING_CONNECTION
    if device_status == DeviceStatus.OFFLINE:
        return SensorStatus.OFFLINE
    if device_status == DeviceStatus.WAITING_CONNECTION:
        return SensorStatus.WAITING_CONNECTION
    return sensor_status


async def get_project_monitoring_latest(db: AsyncSession, project_id: int) -> dict:
    now = datetime.now(timezone.utc)
    rows = await latest_project_sensor_rows(db, project_id)
    devices: dict[int, dict] = {}
    for device, sensor, model, value, recorded_at, received_at in rows:
        device_payload = devices.setdefault(
            device.id,
            {
                "id": device.id,
                "code": device.code,
                "name": device.name,
                "is_enabled": device.is_enabled,
                "connection_status": device.status,
                "location": device.location,
                "last_seen_at": device.last_seen_at,
                "sensors": [],
                "actuators": [],
            },
        )
        if sensor is None or model is None:
            continue
        threshold_config = resolve_sensor_threshold_config(sensor, model)
        threshold_evaluation = evaluate_sensor_threshold(
            float(value) if value is not None else None, threshold_config
        )
        has_telemetry = value is not None and recorded_at is not None
        freshness = "NO_DATA" if not has_telemetry else "STALE" if (now - (received_at or recorded_at)).total_seconds() > settings.device_offline_seconds else "FRESH"
        device_payload["sensors"].append(
            {
                "id": sensor.id,
                "code": sensor.code,
                "name": sensor.name,
                "unit": model.unit,
                "is_enabled": sensor.is_enabled,
                "connection_status": sensor_connection_status(
                    device.status,
                    sensor.status,
                    has_telemetry,
                ),
                "data_status": sensor_connection_status(
                    device.status,
                    sensor.status,
                    has_telemetry,
                ),
                "latest": (
                    {
                        "value": value,
                        "recorded_at": recorded_at,
                        "received_at": received_at,
                        "quality": _quality(model.code, float(value))[0],
                        "quality_reason": _quality(model.code, float(value))[1],
                        "engineering_min": _quality(model.code, float(value))[2],
                        "engineering_max": _quality(model.code, float(value))[3],
                        "freshness": freshness,
                    }
                    if has_telemetry
                    else None
                ),
                "lower_threshold": threshold_config.lower_threshold,
                "upper_threshold": threshold_config.upper_threshold,
                "threshold_state": threshold_evaluation.state,
                "alerts_enabled": threshold_config.alerts_enabled,
            }
        )
    actuator_rows = await latest_project_actuator_rows(db, project_id)
    electrical_rows = await latest_project_actuator_electrical_rows(db, project_id)
    electrical_by_actuator: dict[int, list] = defaultdict(list)
    for row in electrical_rows:
        electrical_by_actuator[row[0]].append(row)
    for device_id, actuator, command_status, requested_at in actuator_rows:
        device_payload = devices.get(device_id)
        if device_payload is None:
            continue
        electrical = _actuator_electrical_payload(
            electrical_by_actuator.get(actuator.id, []), now
        )
        active_incident = electrical.pop("active_incident")
        device_payload["actuators"].append(
            {
                "id": actuator.id,
                "code": actuator.code,
                "name": actuator.name,
                "actuator_model": actuator.actuator_model.name if actuator.actuator_model else None,
                "connection_status": device_payload["connection_status"],
                "desired_state": actuator.desired_state,
                "reported_state": actuator.reported_state,
                "synchronization_status": _actuator_sync(actuator.desired_state, actuator.reported_state, command_status),
                "latest_command": (
                    {"status": command_status, "requested_at": requested_at}
                    if command_status is not None and requested_at is not None
                    else None
                ),
                "last_reported_at": actuator.last_reported_at,
                "electrical": electrical,
                "active_incident": active_incident,
            }
        )
    return {"project_id": project_id, "devices": list(devices.values())}


async def get_project_monitoring_series(
    db: AsyncSession,
    *,
    project_id: int,
    monitoring_range: MonitoringRange,
    device_id: int | None = None,
    now: datetime | None = None,
) -> dict:
    config = MONITORING_RANGE_CONFIG[monitoring_range]
    end = now or datetime.now(timezone.utc)
    start = end - config.duration
    sensor_rows = await project_sensor_metadata_rows(db, project_id, device_id)
    sensor_units = {sensor_id: unit for sensor_id, unit in sensor_rows}
    rows = await project_series_rows(
        db,
        project_id=project_id,
        sensor_ids=list(sensor_units),
        start=start,
        end=end,
        resolution=config.resolution,
    )
    points: dict[int, list[dict]] = defaultdict(list)
    for sensor_id, timestamp, value in rows:
        points[sensor_id].append({"recorded_at": timestamp, "value": value})
    gaps_by_sensor = {
        sensor_id: _sensor_data_gaps(sensor_points)
        for sensor_id, sensor_points in points.items()
    }
    return {
        "project_id": project_id,
        "range": monitoring_range,
        "resolution": config.resolution,
        "series": [
            {
                "sensor_id": sensor_id,
                "unit": unit,
                "points": points[sensor_id],
                "gaps": gaps_by_sensor.get(sensor_id, []),
            }
            for sensor_id, unit in sensor_rows
        ],
    }


def _sensor_data_gaps(points: list[dict]) -> list[dict]:
    """Expose telemetry gaps using the established device offline timeout."""

    threshold = settings.device_offline_seconds
    return [
        {
            "from": current["recorded_at"],
            "to": following["recorded_at"],
            "reason": "NO_DATA",
        }
        for current, following in zip(points, points[1:], strict=False)
        if (following["recorded_at"] - current["recorded_at"]).total_seconds()
        > threshold
    ]


def _actuator_history_payload(
    points: list[dict],
    *,
    start: datetime,
    end: datetime,
) -> tuple[list[dict], dict]:
    """
    Tính thời lượng hoạt động của actuator từ lịch sử chuyển trạng thái.

    Quy ước:
    - Một record state=True có nghĩa actuator chuyển sang ON tại recorded_at
      và tiếp tục ON cho tới transition tiếp theo.
    - Một record state=False có nghĩa actuator chuyển sang OFF tại recorded_at
      và tiếp tục OFF cho tới transition tiếp theo.
    - Khoảng cách dài giữa hai transition KHÔNG phải là mất dữ liệu.
    - Khoảng từ start tới transition đầu tiên là UNKNOWN vì hiện tại query
      chưa cung cấp trạng thái ngay trước start.
    - Transition cuối cùng được giữ hiệu lực tới end.
    """

    total_duration = max(
        0,
        int((end - start).total_seconds()),
    )

    if not points:
        return [], {
            "on_duration_seconds": 0,
            "off_duration_seconds": 0,
            "unknown_duration_seconds": total_duration,
            "on_percentage": None,
            "on_count": 0,
            "off_count": 0,
            "last_changed_at": None,
        }

    # Không phụ thuộc vào thứ tự query trả về.
    ordered_points = sorted(
        points,
        key=lambda point: point["recorded_at"],
    )

    # Chỉ giữ record nằm trong window.
    ordered_points = [
        point
        for point in ordered_points
        if start <= point["recorded_at"] <= end
    ]

    if not ordered_points:
        return [], {
            "on_duration_seconds": 0,
            "off_duration_seconds": 0,
            "unknown_duration_seconds": total_duration,
            "on_percentage": None,
            "on_count": 0,
            "off_count": 0,
            "last_changed_at": None,
        }

    on_duration = 0
    off_duration = 0

    # Vì hiện tại query bắt đầu từ `start`,
    # chúng ta không biết trạng thái actuator trước transition đầu tiên.
    first_recorded_at = ordered_points[0]["recorded_at"]

    unknown_duration = max(
        0,
        int((first_recorded_at - start).total_seconds()),
    )

    # ---------------------------------------------------------------
    # Mỗi state có hiệu lực cho tới transition tiếp theo.
    #
    # Ví dụ:
    #
    # 08:00 ON
    # 08:30 OFF
    #
    # => 08:00 -> 08:30 = 30 phút ON
    # ---------------------------------------------------------------

    for index, current in enumerate(ordered_points):
        segment_start = max(
            start,
            current["recorded_at"],
        )

        if index + 1 < len(ordered_points):
            segment_end = min(
                end,
                ordered_points[index + 1]["recorded_at"],
            )
        else:
            # Transition cuối cùng tiếp tục có hiệu lực tới cuối range.
            segment_end = end

        duration = max(
            0,
            int(
                (
                    segment_end
                    - segment_start
                ).total_seconds()
            ),
        )

        state = current["state"]

        if state is True:
            on_duration += duration
        elif state is False:
            off_duration += duration
        else:
            # Defensive fallback.
            # Schema hiện tại thường là bool,
            # nhưng nếu có dữ liệu legacy NULL thì không suy đoán.
            unknown_duration += duration

    known_duration = (
        on_duration
        + off_duration
    )

    # ---------------------------------------------------------------
    # Count transition
    # ---------------------------------------------------------------

    on_count = sum(
        1
        for point in ordered_points
        if point["state"] is True
    )

    off_count = sum(
        1
        for point in ordered_points
        if point["state"] is False
    )

    # ---------------------------------------------------------------
    # Percentage tính trên thời gian biết trạng thái.
    # UNKNOWN không đưa vào mẫu số.
    # ---------------------------------------------------------------

    on_percentage = (
        round(
            on_duration
            / known_duration
            * 100,
            2,
        )
        if known_duration > 0
        else None
    )

    return [], {
        "on_duration_seconds": on_duration,
        "off_duration_seconds": off_duration,
        "unknown_duration_seconds": unknown_duration,
        "on_percentage": on_percentage,
        "on_count": on_count,
        "off_count": off_count,
        "last_changed_at": (
            ordered_points[-1][
                "recorded_at"
            ]
            if ordered_points
            else None
        ),
    }

async def get_device_actuator_history(
    db: AsyncSession,
    *,
    project_id: int,
    device_id: int,
    monitoring_range: MonitoringRange,
    now: datetime | None = None,
) -> dict:
    config = MONITORING_RANGE_CONFIG[monitoring_range]
    end = now or datetime.now(timezone.utc)
    start = end - config.duration
    rows = await device_actuator_history_rows(
        db,
        project_id=project_id,
        device_id=device_id,
        start=start,
        end=end,
    )
    points_by_actuator: dict[int, list[dict]] = defaultdict(list)
    for actuator_id, recorded_at, state in rows:
        points_by_actuator[actuator_id].append(
            {"recorded_at": recorded_at, "state": state}
        )
    actuator_rows = await latest_project_actuator_rows(db, project_id)
    actuator_ids = [
        actuator.id
        for row_device_id, actuator, _, _ in actuator_rows
        if row_device_id == device_id
    ]
    items = []
    for actuator_id in actuator_ids:
        points = points_by_actuator[actuator_id]
        gaps, statistics = _actuator_history_payload(points, start=start, end=end)
        items.append(
            {
                "actuator_id": actuator_id,
                "points": points,
                "gaps": gaps,
                "statistics": statistics,
            }
        )
    return {
        "project_id": project_id,
        "device_id": device_id,
        "range": monitoring_range,
        "items": items,
    }
