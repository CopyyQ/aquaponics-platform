# Frontend recovery forensics

Recorded 2026-09-08 before frontend recovery changes.

## Repository state

- HEAD: `91528d492c5905644038ae7c0810e406f03470cb` (`Dự án Aquaponics`)
- The current worktree contains unrelated backend changes and a frontend cleanup.
- Frontend status inventory: 225 status lines, including 214 deleted paths, 4 modified tracked files, and 7 untracked frontend entries (some entries are directories containing multiple files).
- Staged frontend deletions: 72 paths.
- Unstaged frontend deletions: 142 paths.
- No frontend changes are committed after `HEAD`; `git reflog` contains only the initial commit for this checkout.

## Deleted frontend files

The complete deletion inventory is the output of the following commands, captured from the pre-recovery index/worktree state:

```sh
git diff HEAD --name-only --diff-filter=D -- frontend
git diff HEAD --name-status -- frontend
```

The deleted paths cover the original `entities/`, `features/`, `pages/`, `shared/api/`, `shared/charts/time-series/`, `widgets/`, router/layout infrastructure, and the original frontend E2E suite. Key deleted UI surfaces include:

- `frontend/src/app/layouts/project-layout.tsx`
- `frontend/src/app/router/AppRouter.tsx`
- `frontend/src/app/router/protected-route.tsx`
- `frontend/src/pages/project-overview/ProjectOverviewPage.tsx`
- `frontend/src/pages/project-monitoring/ProjectMonitoringPage.tsx`
- `frontend/src/pages/project-scada/ProjectScadaPage.tsx`
- `frontend/src/pages/device-detail/DeviceDetailPage.tsx`
- `frontend/src/pages/sensor-detail/SensorDetailPage.tsx`
- `frontend/src/pages/alerts/AlertsPage.tsx`
- `frontend/src/pages/project-members/ProjectMembersPage.tsx`
- `frontend/src/pages/project-settings/ProjectSettingsPage.tsx`
- `frontend/src/shared/api/query-client.ts`
- `frontend/src/shared/api/query-keys.ts`
- `frontend/src/shared/api/query-invalidation.ts`
- `frontend/src/shared/charts/time-series/TimeSeriesChart.tsx`
- `frontend/src/widgets/monitoring/monitoring-dashboard.tsx`
- `frontend/src/widgets/project-monitoring/ProjectMonitoringView.tsx`
- `frontend/src/widgets/project-scada/ScadaScene.tsx`

The path-level Git inventory above is authoritative and intentionally retained as a reproducible command record rather than hand-maintained prose.

## Current simplified/new frontend files

Untracked or newly introduced frontend work includes:

- `frontend/src/api/` (`client.ts`, `contracts.ts`, `resources.ts`, and tests)
- `frontend/src/app/auth.tsx`, `frontend/src/app/router.tsx`, `frontend/src/app/shell.tsx`
- `frontend/src/pages/` flat simplified pages
- `frontend/e2e/canonical-navigation.spec.ts`
- `frontend/scripts/`

Modified tracked frontend files are `frontend/playwright.config.ts`, `frontend/src/app/navigation/navigation-items.ts`, `frontend/src/app/providers/app-providers.tsx`, and `frontend/src/main.tsx`.

## Recovery source evidence

- `HEAD` contains the original architecture (`git cat-file -e HEAD:frontend/src/app/router/AppRouter.tsx` and `HEAD:frontend/src/pages/project-overview/ProjectOverviewPage.tsx` both succeed).
- `/tmp/aquaponics-original-reference` was cloned read-only from GitHub and resolves to `91528d492c5905644038ae7c0810e406f03470cb`.
- Therefore local Git `HEAD` is the primary restore source; the matching original reference is a cross-check.

## Backups

- Full current frontend: `backups/frontend/frontend_current_before_recovery_20260908_104742.tar.gz`
- Full current frontend SHA-256: `c0c7703e05040cf964b0fec07526d588d33e6debced64fb2832672b5654ab94b`
- Current canonical API layer: `backups/frontend/frontend_canonical_api_before_recovery_20260908_104807.tar.gz`
- Canonical API layer SHA-256: `82749026848f7048bf618e8a29b88767423ddc092a233966a0d73581a153c7e6`
- A filesystem copy is available at `/tmp/aquaponics_frontend_current_20260908_104807`.

Both archives were listed with `tar -tzf` after creation.
