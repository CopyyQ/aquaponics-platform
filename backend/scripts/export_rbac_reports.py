"""Export machine-readable RBAC catalogs used by the audit."""

import json
import importlib.util
from pathlib import Path

_path = Path(__file__).resolve().parents[1] / "alembic/versions/0047_permission_rbac.py"
_spec = importlib.util.spec_from_file_location("rbac_migration", _path)
assert _spec and _spec.loader
_0047_permission_rbac = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_0047_permission_rbac)


def main() -> None:
    out = Path(__file__).resolve().parents[2] / "docs/audits/aquaponics_system_refactor"
    permissions = [{"code": c, "resource": r, "action": a} for c, r, a in _0047_permission_rbac.PERMISSIONS]
    (out / "permissions.json").write_text(json.dumps({"permissions": permissions}, ensure_ascii=False, indent=2) + "\n")
    (out / "roles.json").write_text(json.dumps({"roles": [{"code": c} for c in ("ADMIN", "OWNER", "TECHNICIAN", "VIEWER")]}, indent=2) + "\n")


if __name__ == "__main__":
    main()
