"""Export the current API contract for the architecture audit."""

import json
from pathlib import Path

from app.main import app


def main() -> None:
    directory = Path(__file__).resolve().parents[2] / "docs/audits/aquaponics_system_refactor"
    payload = json.dumps(app.openapi(), ensure_ascii=False, indent=2) + "\n"
    for name in ("final_openapi.json", "80_openapi_0050_source.json"):
        (directory / name).write_text(payload, encoding="utf-8")


if __name__ == "__main__":
    main()
