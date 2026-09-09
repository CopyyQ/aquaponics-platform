#!/usr/bin/env python3
"""Fail when backend modules cross a forbidden dependency boundary."""

from __future__ import annotations

import ast
from collections import Counter
from pathlib import Path

APP_ROOT = Path(__file__).resolve().parents[1] / "app"


def layer(path: Path) -> str | None:
    relative = path.relative_to(APP_ROOT)
    return relative.parts[0] if len(relative.parts) > 1 else None


def imported_modules(tree: ast.AST) -> list[tuple[int, str]]:
    imports: list[tuple[int, str]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.extend((node.lineno, alias.name) for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.append((node.lineno, node.module))
    return imports


def violation(source_layer: str | None, module: str, path: Path) -> str | None:
    target = module.removeprefix("app.").split(".", 1)[0] if module.startswith("app.") else None
    if source_layer == "models" and target in {"api", "services", "queries", "mqtt", "jobs"}:
        return "models must only describe persistence"
    if source_layer == "queries" and target in {"api", "services"}:
        return "queries cannot own HTTP or business services"
    if source_layer == "services" and target == "api":
        return "services cannot depend on API routers"
    if source_layer in {"mqtt", "jobs"} and target == "api":
        return f"{source_layer} cannot depend on API routers"
    if source_layer == "api" and target == "api" and path.name != "router.py":
        if module.startswith("app.api.v1"):
            return "API routers cannot import other API routers"
    return None


def main() -> int:
    errors: list[str] = []
    for path in sorted(APP_ROOT.rglob("*.py")):
        source_layer = layer(path)
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for line, module in imported_modules(tree):
            reason = violation(source_layer, module, path)
            if reason:
                errors.append(f"{path.relative_to(APP_ROOT.parent)}:{line}: {module}: {reason}")
    telemetry_path = APP_ROOT / "services" / "telemetry_service.py"
    telemetry_tree = ast.parse(telemetry_path.read_text(encoding="utf-8"), filename=str(telemetry_path))
    for node in ast.walk(telemetry_tree):
        if isinstance(node, ast.Name) and node.id == "evaluate_operational_rules_for_sensor":
            errors.append(
                "app/services/telemetry_service.py: Sensor telemetry may only invoke "
                "the canonical ThresholdAlertConfig evaluator"
            )
            break
    if errors:
        print("\n".join(errors))
        return 1
    from app.main import app

    document = app.openapi()
    schemas = document.get("components", {}).get("schemas", {})
    operations = [operation for item in document["paths"].values() for method, operation in item.items()
                  if method in {"get", "post", "put", "patch", "delete"}]
    contract_errors: list[str] = []
    if any("Project" in name for name in schemas): contract_errors.append("Project public schema name")
    if any("project" in field.lower() for schema in schemas.values() for field in schema.get("properties", {})): contract_errors.append("legacy project field")
    if any(schema.get("additionalProperties") is True for schema in schemas.values()): contract_errors.append("free-form public schema")
    alert_fields = schemas.get("AlertRead", {}).get("properties", {})
    if not {"resource_type", "sensor_id", "actuator_id"} <= alert_fields.keys(): contract_errors.append("Sensor-only Alert schema")
    if schemas.get("ActuatorThresholdMetric", {}).get("enum") != ["VOLTAGE", "CURRENT"]: contract_errors.append("untyped Actuator threshold metric")
    mqtt_operations = [(path, method) for path, item in document["paths"].items() for method in item if "mqtt-config" in path]
    if len(mqtt_operations) != 1: contract_errors.append("multiple MQTT export endpoints")
    operation_counts = Counter(operation.get("operationId") for operation in operations)
    if any(count > 1 for count in operation_counts.values()): contract_errors.append("duplicate resource writer/operationId")
    serialized = str(document)
    if "system_role" in serialized: contract_errors.append("system_role authorization legacy")
    if any(term in serialized for term in ("ACTUATOR_FEEDBACK", "feedback_role", "SENSOR_DEVICE", "ACTUATOR_DEVICE")): contract_errors.append("legacy feedback/device type term")
    if contract_errors:
        print("\n".join(f"OpenAPI: {error}" for error in contract_errors))
        return 1
    print("Architecture boundaries: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
