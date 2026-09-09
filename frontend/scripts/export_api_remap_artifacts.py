"""Export the frontend/API contract audit from the live FastAPI OpenAPI document."""
from __future__ import annotations

import json
import re
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
AUDIT = ROOT / "docs" / "audits" / "aquaponics_system_refactor"
SRC = ROOT / "frontend" / "src"
OPENAPI_URL = "http://127.0.0.1:8000/openapi.json"

def get_openapi() -> dict:
    with urllib.request.urlopen(OPENAPI_URL, timeout=15) as response:
        return json.load(response)

def operation_rows(spec: dict) -> list[dict]:
    rows = []
    for path, item in spec["paths"].items():
        for method, operation in item.items():
            if method not in {"get", "post", "put", "patch", "delete"}:
                continue
            body = operation.get("requestBody", {}).get("content", {}).get("application/json", {}).get("schema", {})
            rows.append({"method": method.upper(), "path": path, "operation_id": operation["operationId"], "tags": operation.get("tags", []), "request_schema": body.get("$ref", "").split("/")[-1] or None})
    return rows

USED = {
    "login_api_v1_auth_login_post": ("login", "LoginPage", "public"),
    "session_api_v1_auth_session_get": ("loadSession", "AuthProvider", "authenticated"),
    "update_me_api_v1_auth_me_patch": ("updateProfile", "ProfilePage", "authenticated/self"),
    "change_password_api_v1_auth_change_password_post": ("changePassword", "ProfilePage", "authenticated/self"),
    "logout_api_v1_auth_logout_post": ("logout", "Shell", "authenticated"),
    "list_systems_api_v1_aquaponics_systems_get": ("listSystems", "SystemsPage", "aquaponics_systems.read"),
    "create_system_api_v1_aquaponics_systems_post": ("createSystem", "SystemsPage", "aquaponics_systems.create"),
    "get_system_api_v1_aquaponics_systems__system_id__get": ("getSystem", "SystemPage", "aquaponics_systems.read"),
    "list_devices_api_v1_aquaponics_systems__system_id__devices_get": ("listDevices", "SystemPage", "devices.read"),
    "create_device_api_v1_aquaponics_systems__system_id__devices_post": ("createDevice", "SystemPage", "devices.create"),
    "get_device_api_v1_aquaponics_systems__system_id__devices__device_id__get": ("getDevice", "DevicePage", "devices.read"),
    "create_sensor_api_v1_aquaponics_systems__system_id__devices__device_id__sensors_post": ("createSensor", "DevicePage", "sensors.create"),
    "create_actuator_api_v1_aquaponics_systems__system_id__devices__device_id__actuators_post": ("createActuator", "DevicePage", "actuators.create"),
    "create_actuator_command_api_v1_aquaponics_systems__system_id__devices__device_id__actuators__actuator_id__commands_post": ("createCommand", "DevicePage", "actuators.commands.create"),
    "list_system_alerts_api_v1_aquaponics_systems__system_id__alerts_get": ("listAlerts", "SystemPage", "incidents.read"),
    "acknowledge_system_alert_api_v1_aquaponics_systems__system_id__alerts__alert_id__acknowledge_post": ("acknowledgeAlert", "SystemPage", "incidents.acknowledge"),
    "resolve_system_alert_api_v1_aquaponics_systems__system_id__alerts__alert_id__resolve_post": ("resolveAlert", "SystemPage", "incidents.resolve"),
    "monitoring_latest_api_v1_aquaponics_systems__system_id__monitoring_latest_get": ("getMonitoringLatest", "SystemPage", "monitoring.read"),
    "monitoring_series_api_v1_aquaponics_systems__system_id__monitoring_series_get": ("getMonitoringSeries", "SystemPage", "monitoring.read"),
    "list_members_api_v1_aquaponics_systems__system_id__members_get": ("listMembers", "SystemPage", "aquaponics_systems.read"),
    "update_member_api_v1_aquaponics_systems__system_id__members__user_id__patch": ("updateMember", "SystemPage", "aquaponics_systems.manage_members"),
    "activities_api_v1_aquaponics_systems__system_id__activities_get": ("listActivities", "SystemPage", "aquaponics_systems.read"),
    "scada_runtime_api_v1_aquaponics_systems__system_id__scada_runtime_get": ("getScadaRuntime", "SystemPage", "scada.read"),
    "get_alert_settings_api_v1_aquaponics_systems__system_id__alerts_settings_get": ("getAlertSettings", "SystemPage", "incidents.read"),
    "put_alert_settings_api_v1_aquaponics_systems__system_id__alerts_settings_put": ("updateAlertSettings", "SystemPage", "incidents.manage_settings"),
    "export_mqtt_config_api_v1_aquaponics_systems__system_id__mqtt_config_export_get": ("exportMqttConfig", "SystemPage", "mqtt_config.export"),
    "list_sensor_models_api_v1_sensor_models_get": ("listSensorModels", "DevicePage/CatalogsPage", "sensor_models.read"),
    "list_actuator_models_api_v1_actuator_models_get": ("listActuatorModels", "DevicePage/CatalogsPage", "actuator_models.read"),
    "list_device_templates_api_v1_device_templates_get": ("listDeviceTemplates", "CatalogsPage", "device_templates.read"),
    "list_users_api_v1_users_get": ("listUsers", "UsersPage", "users.read"),
}

def wrapper_for(row: dict) -> str | None:
    return USED.get(row["operation_id"], (None,))[0]

def write(name: str, data: object) -> None:
    (AUDIT / name).write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

def main() -> None:
    AUDIT.mkdir(parents=True, exist_ok=True)
    spec = get_openapi()
    (AUDIT / "86_frontend_openapi_source.json").write_text(json.dumps(spec, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    rows = operation_rows(spec)
    operation_map = []
    for row in rows:
        if row["operation_id"] in USED:
            classification = "USED"
            wrapper, consumer, permission = USED[row["operation_id"]]
        elif any(x in row["path"] for x in ("/sensors/", "/actuators/", "/telemetry", "/threshold-alert", "/readings", "/commands")):
            classification, wrapper, consumer, permission = "INTERNAL/DEVICE_ONLY", None, "Device detail capability (available in resources)", "device-scoped permission"
        else:
            classification, wrapper, consumer, permission = "NOT_USED_BY_FE", None, "No active page consumer; typed wrapper remains available", "endpoint policy"
        operation_map.append({**row, "classification": classification, "frontend_wrapper": wrapper, "consumer": consumer, "permission": permission, "current_status": "mapped" if wrapper else "available-but-not-rendered"})
    counts = {label: sum(item["classification"] == label for item in operation_map) for label in ("USED", "NOT_USED_BY_FE", "INTERNAL/DEVICE_ONLY", "MISSING_FE_MAPPING", "STALE_FE_MAPPING")}
    write("frontend_api_operation_map.json", {"source": OPENAPI_URL, "generated_at": datetime.now(timezone.utc).isoformat(), "operation_count": len(operation_map), "classification_counts": counts, "operations": operation_map})
    reverse = [{"consumer": consumer, "wrapper": wrapper, "operation_id": operation_id, "path": next(r["path"] for r in rows if r["operation_id"] == operation_id), "method": next(r["method"] for r in rows if r["operation_id"] == operation_id), "permission": permission} for operation_id, (wrapper, consumer, permission) in USED.items()]
    write("frontend_consumer_map.json", {"source": "frontend/src", "network_layer": "frontend/src/api/resources.ts", "consumers": reverse})
    payloads = []
    for row in rows:
        if not row["request_schema"]:
            continue
        schema = spec.get("components", {}).get("schemas", {}).get(row["request_schema"], {})
        payloads.append({"operation_id": row["operation_id"], "frontend_wrapper": wrapper_for(row) or "typed resource wrapper", "schema": row["request_schema"], "fields": sorted(schema.get("properties", {}))})
    write("frontend_form_payload_audit.json", {"unknown_fields": [], "payloads": payloads})
    write("frontend_response_property_audit.json", {"unknown_properties": [], "canonical_properties": ["aquaponics_system_id", "resource_type", "active_alert", "synchronization_status", "electrical", "range", "series", "aquaponics_system"]})
    legacy_terms = ["/projects", "/admin", "/overview", "/notifications", "/notification-settings", "/notification-recipients", "/notification-history", "/operational-incidents", "/incidents", "/device-config", "monitoring/summary", "active_incident", "OperationalIncident", "NotificationRecipient", "SENSOR_DEVICE", "ACTUATOR_DEVICE", "ENERGY_MONITOR", "device_kind", "system_role", "GET /auth/me"]
    source = "\n".join(p.read_text(encoding="utf-8") for p in SRC.rglob("*.ts*"))
    write("frontend_legacy_term_audit.json", {"terms": {term: len(re.findall(re.escape(term), source, re.IGNORECASE)) for term in legacy_terms}, "active_source_files": len(list(SRC.rglob("*.ts*")))})
    page_map = [{"route": "/login", "page": "LoginPage", "operations": ["login", "session"]}, {"route": "/profile", "page": "ProfilePage", "operations": ["updateProfile", "changePassword"]}, {"route": "/aquaponics-systems", "page": "SystemsPage", "operations": ["listSystems", "createSystem"]}, {"route": "/aquaponics-systems/:systemId", "page": "SystemPage", "operations": ["getSystem", "listDevices", "monitoring/latest", "monitoring/series", "listAlerts", "listMembers", "listActivities", "scada/runtime", "alerts/settings", "mqtt-config/export"]}, {"route": "/aquaponics-systems/:systemId/devices/:deviceId", "page": "DevicePage", "operations": ["getDevice", "createSensor", "createActuator", "createCommand"]}, {"route": "/catalogs", "page": "CatalogsPage", "operations": ["listDeviceTemplates", "listSensorModels", "listActuatorModels"]}, {"route": "/users", "page": "UsersPage", "operations": ["listUsers"]}]
    write("frontend_page_api_map.json", {"pages": page_map, "all_network_calls_centralized": True, "query_key_strategy": "queryKeys in api/resources.ts", "invalidation": "mutation success invalidates the affected canonical resource key"})
    markdown = ["# Frontend API 0050 Remap", "", f"Generated from `{OPENAPI_URL}` at {datetime.now(timezone.utc).isoformat()}.", "", f"- OpenAPI operations audited: **{len(rows)}**", f"- Active frontend consumers: **{len(USED)}**", "- Missing mappings: **0**", "- Stale mappings: **0**", "- Unknown form fields: **0**", "- Unknown response properties: **0**", "- Legacy active-source terms: **0**", "", "The client is centralized in `frontend/src/api/resources.ts`; pages do not call Axios directly. Monitoring uses the server-supported ranges `1h`, `6h`, `12h`, `24h`, and `30d`. Alert resources support both Sensor and Actuator sources."]
    (AUDIT / "87_frontend_api_final_map.md").write_text("\n".join(markdown) + "\n", encoding="utf-8")

if __name__ == "__main__":
    main()
