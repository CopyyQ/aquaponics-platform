AQUAPONICS OVERWRITE PACKAGE - 2026-09-11

Copy the backend/ and frontend/ folders over the project root:
/home/plab/Desktop/Nguyen_Anh_Quyet_PLAB/Aquaponics/aquaponics-platform

Included runtime files only. Tests are intentionally excluded because the previous hotfix script dirtied test files.

Verified on current server source:
- python3 -m py_compile for backend hotfix files: PASS
- docker compose build backend frontend: BUILD_EXIT=0
- SHA-256 of all packaged source files matches server copies before packaging.

After overwrite:
  cd /home/plab/Desktop/Nguyen_Anh_Quyet_PLAB/Aquaponics/aquaponics-platform
  docker compose build backend frontend
  docker compose up -d --build backend mqtt_consumer scheduler frontend public-monitoring-gateway
  docker compose ps

Root cause addressed:
- NORMALIZED incidents are not active incidents.
- inline actuator incident text removed from monitoring rows.
- project-health Telegram sends on health-level transitions, not every changing fingerprint/timestamp.
