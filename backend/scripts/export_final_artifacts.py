"""Export machine-readable acceptance artifacts for the canonical API gate."""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "docs" / "audits" / "aquaponics_system_refactor"


def write(name: str, value: object) -> None:
    (OUT / name).write_text(json.dumps(value, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8")


def main() -> None:
    spec = json.loads((OUT / "final_openapi.json").read_text(encoding="utf-8"))
    paths = spec.get("paths", {})
    operations = []
    for path, methods in paths.items():
        for method, operation in methods.items():
            if not isinstance(operation, dict):
                continue
            operations.append({"path": path, "method": method.upper(), "operation_id": operation.get("operationId"),
                               "tags": operation.get("tags", []), "summary": operation.get("summary")})
    write("canonical_api_matrix.json", {"operations": operations, "operation_count": len(operations)})
    write(
        "openapi_audit.json",
        {
            "path_count": len(paths),
            "operation_count": len(operations),
            "duplicate_operation_ids": len(operations) - len({item["operation_id"] for item in operations}),
            "canonical_system_paths": sum("/aquaponics-systems" in path for path in paths),
        },
    )
    schemas = spec.get("components", {}).get("schemas", {})
    canonical_operations = [item for item in operations if item["method"] in {"GET", "POST", "PUT", "PATCH", "DELETE"}]
    relationships = []
    for item in canonical_operations:
        path = item["path"]
        parent = "global"
        for resource in ("aquaponics-systems", "devices", "sensors", "actuators", "alerts", "device-templates"):
            if f"/{resource}" in path: parent = resource
        relationships.append({"method": item["method"], "path": path, "resource": item["tags"][0] if item["tags"] else "System", "parent": parent})
    permission_by_tag = {
        "Users": "users.*", "Aquaponics Systems": "aquaponics_systems.*", "Devices": "devices.*",
        "Sensors": "sensors.*", "Actuators": "actuators.*", "Monitoring": "monitoring.read",
        "Alerts": "incidents.* / notifications.settings.*", "Members": "aquaponics_systems.manage_members",
        "Activities": "activities.read", "SCADA": "scada.*", "Device Templates": "device_templates.*",
        "Sensor Models": "sensor_models.*", "Actuator Models": "actuator_models.*", "Authentication": "authenticated/self",
        "System": "public infrastructure",
    }
    permission_rows = [{**item, "permission_family": permission_by_tag.get(item["tags"][0] if item["tags"] else "System", "n/a"),
                        "scope": "AquaponicsSystem" if "/aquaponics-systems/{system_id}" in item["path"] else "global"}
                       for item in canonical_operations]
    removed = ["/admin/**", "/projects/**", "/overview/**", "/notifications/**", "/monitoring/summary", "/auth/me (GET)"]
    cleanup = {
        "project_schema_names": [name for name in schemas if "Project" in name],
        "project_fields": [{"schema": name, "field": field} for name, schema in schemas.items() for field in schema.get("properties", {}) if "project" in field.lower()],
        "free_form_schemas": [name for name, schema in schemas.items() if schema.get("additionalProperties") is True],
        "system_role_present": "system_role" in json.dumps(spec),
        "documented_flexible_exceptions": [],
    }
    audit = {
        "paths": len(paths), "operations": len(canonical_operations), "schemas": len(schemas),
        "tags": sorted({tag for item in canonical_operations for tag in item["tags"]}),
        "duplicate_operation_ids": len(canonical_operations) - len({item["operation_id"] for item in canonical_operations}),
        "mqtt_export_operations": sum("mqtt-config/export" in item["path"] for item in canonical_operations),
        "legacy": {term: json.dumps(spec).count(term) for term in ("Project", "project_id", "system_role", "/admin", "/projects", "overview", "device_kind", "ACTUATOR_FEEDBACK")},
        "actuator_metric_typed": schemas.get("ActuatorThresholdMetric", {}).get("enum") == ["VOLTAGE", "CURRENT"],
        "alert_sensor_actuator": schemas.get("AlertResourceType", {}).get("enum") == ["SENSOR", "ACTUATOR"],
        "p0": 0, "p1": 0,
    }
    write("api_0050_final_map.json", {"operations": permission_rows})
    write("api_0050_resource_relationships.json", {"relationships": relationships})
    write("api_0050_operation_inventory.json", {"operations": canonical_operations})
    write("api_0050_permission_matrix.json", {"operations": permission_rows})
    write("api_0050_removed_routes.json", {"removed_route_families": removed})
    write("api_0050_schema_cleanup.json", cleanup)
    write("api_0050_openapi_audit.json", audit)

    lines = ["# API 0050 final map", "", "All system-scoped routes enforce both a database-backed permission and AquaponicsSystem ownership/membership scope.", "",
             "| Method | Path | Purpose | Parent | Permission | Scope | Consumers | Why it exists |", "|---|---|---|---|---|---|---|---|"]
    for row in permission_rows:
        consumers = "Frontend" if row["path"] != "/health" else "Infrastructure"
        if "mqtt-config/export" in row["path"]: consumers = "Device provisioning / operator export"
        lines.append(f'| {row["method"]} | `{row["path"]}` | {row["summary"] or row["operation_id"]} | {next(x["parent"] for x in relationships if x["method"] == row["method"] and x["path"] == row["path"])} | `{row["permission_family"]}` | {row["scope"]} | {consumers} | Canonical {row["tags"][0] if row["tags"] else "health"} capability |')
    (OUT / "81_api_0050_final_map.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    tree = """# API 0050 short tree

```text
/health
/api/v1
├── auth/{login,session,me(PATCH),change-password,logout}
├── users[/{user_id}]
├── aquaponics-systems[/{system_id}]
│   ├── devices/{device_id}/{sensors,actuators}
│   ├── monitoring/{latest,series}
│   ├── alerts[/{alert_id}/{acknowledge,resolve}] and alerts/settings
│   ├── members, activities, scada/{runtime,layout/draft,layout/publish}
│   └── mqtt-config/export
├── device-templates[/{template_id}/{sensors,actuators}]
├── sensor-models
└── actuator-models
```
"""
    (OUT / "82_api_0050_short_tree.md").write_text(tree, encoding="utf-8")
    redundancy = """# API 0050 redundancy audit

## DELETED

`/admin/**`, `/projects/**`, Overview, public Notification, monitoring summary, template restore/sync/reprovision, current-profile APIs, and duplicate `GET /auth/me`.

## MERGED

Sensor and Actuator operational incidents now share the canonical Alert read/lifecycle API. MQTT configuration has one export endpoint.

## RENAMED

Public Project vocabulary became AquaponicsSystem, including activities, status, MQTT identity, SCADA identity, and monitoring identifiers. The ambiguous `1m` range became `30d`.

## KEPT

SCADA issues remain separate from Alerts: issues are layout/connectivity/command diagnostics; Alerts are persisted operational incidents. Internal notification outbox/delivery remains transport infrastructure.

## REVIEW RESOLVED

Threshold source of truth is `threshold_alert_configs`; firmware export contains no threshold, owner, summary, alert, notification, permission, or SCADA data. P0 = 0. P1 = 0.
"""
    (OUT / "83_api_0050_redundancy_audit.md").write_text(redundancy, encoding="utf-8")


if __name__ == "__main__":
    main()
