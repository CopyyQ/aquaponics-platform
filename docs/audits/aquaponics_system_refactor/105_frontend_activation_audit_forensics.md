# Frontend Activation Audit — Forensics Baseline

Captured: 2026-09-08 11:29:49 Asia/Ho_Chi_Minh

## Safe backup gate

- Archive: `backups/frontend/frontend_before_activation_audit_20260908_112949.tar.gz`
- Filesystem copy: `/tmp/frontend_before_activation_audit_20260908_112949`
- SHA-256: `37b513fb24e8be1b28d06b52002c79867e2fd2d32c9f0010f1dfa5f5bb939b89`
- Archive integrity (`tar -tzf`): **VERIFIED**

No frontend engineering change for this activation audit was made before this backup passed.

## Repository baseline

- HEAD: `91528d492c5905644038ae7c0810e406f03470cb`
- Staged files: 0
- Frontend modified tracked files: 5
- Frontend untracked status entries: 31
- Frontend deleted files: 0
- Backend status entries: 151
- Backend modified tracked files: 57
- Backend deleted tracked files: 65
- Backend untracked status entries: 29

The large backend diff and the existing frontend recovery work predate this activation audit. They are preserved as user-owned work. This audit will not rewrite or discard them.

## Modified tracked frontend files

- `frontend/playwright.config.ts`
- `frontend/src/app/layouts/app-shell.tsx`
- `frontend/src/app/navigation/navigation-items.ts`
- `frontend/src/app/providers/app-providers.tsx`
- `frontend/src/main.tsx`

## Untracked frontend entries

- `frontend/e2e/canonical-navigation.spec.ts`
- `frontend/scripts/`
- `frontend/src/api/`
- `frontend/src/app/auth.tsx`
- `frontend/src/app/layouts/aquaponics-system-layout.tsx`
- `frontend/src/app/router.tsx`
- `frontend/src/app/router/canonical-router.tsx`
- `frontend/src/app/shell.tsx`
- `frontend/src/pages/activities.tsx`
- `frontend/src/pages/actuator-detail.tsx`
- `frontend/src/pages/alerts.tsx`
- `frontend/src/pages/catalogs-canonical.tsx`
- `frontend/src/pages/catalogs.tsx`
- `frontend/src/pages/device-detail-canonical.tsx`
- `frontend/src/pages/device.tsx`
- `frontend/src/pages/devices.tsx`
- `frontend/src/pages/login.tsx`
- `frontend/src/pages/members.tsx`
- `frontend/src/pages/monitoring.tsx`
- `frontend/src/pages/not-found-canonical.tsx`
- `frontend/src/pages/overview.tsx`
- `frontend/src/pages/profile.tsx`
- `frontend/src/pages/scada.tsx`
- `frontend/src/pages/sensor-detail.tsx`
- `frontend/src/pages/settings.tsx`
- `frontend/src/pages/system.tsx`
- `frontend/src/pages/systems.tsx`
- `frontend/src/pages/users.tsx`
- `frontend/src/widgets/canonical-monitoring/`
- `frontend/src/widgets/canonical-overview/`
- `frontend/src/widgets/canonical-scada/`

## Live authority snapshot

- Source: `http://localhost:8000/openapi.json`
- Saved as: `106_frontend_activation_live_openapi.json`
- Paths: 45
- Operations: 82
- Component schemas: 106
- Duplicate operation IDs: 0
- Schema-name anomalies: 0
- Backend health at capture: HTTP 200

## Commands captured

The baseline was established with `git status --short`, tracked and cached diff stats, tracked and cached name-status output, `git rev-parse HEAD`, a fresh live OpenAPI fetch, structural `jq` checks, and an HTTP health request. No credential values were printed or stored in this report.
