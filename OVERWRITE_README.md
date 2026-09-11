# Aquaponics repair overlay — 2026-09-08

This archive contains repaired `backend/` and `frontend/` trees intended to overwrite the corresponding directories in the existing Aquaponics project.

## Safety

Excluded intentionally:
- `backend/.env`
- `frontend/.env`
- `frontend/node_modules/`
- `frontend/dist/`
- Python/pytest caches
- Playwright build/test artifacts

Your existing `.env` files should therefore be preserved when extracting over the project root.

## Important DB change

Backend includes Alembic revision `0051_persist_in_app_alert_delivery.py`, adding persistent `in_app_enabled` to `project_notification_settings`.

After overwriting, run the project's normal dependency install/build/test workflow and:

```bash
cd backend
alembic upgrade head
alembic current
alembic heads
alembic check
```

## Validation performed in packaging environment

- Backend Python source compile: PASS.
- Frontend TypeScript/TSX parse syntax: PASS (286 source files).
- Full npm semantic typecheck/Vitest/build/Playwright: NOT PROVEN in packaging sandbox because dependency installation was unavailable.
- Full backend pytest/runtime/OpenAPI generation: NOT PROVEN in packaging sandbox because Python runtime dependencies were unavailable.

Do not interpret the archive as a full live-environment validation report. Run the normal project validation commands after overwrite.
