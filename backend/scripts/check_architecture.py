#!/usr/bin/env python3
"""Fail when backend modules cross a forbidden dependency boundary."""

from __future__ import annotations

import ast
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
    if errors:
        print("\n".join(errors))
        return 1
    print("Architecture boundaries: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
