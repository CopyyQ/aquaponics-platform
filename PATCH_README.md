# Aquaponics frontend build hotfix — 2026-09-08

Fixes TypeScript errors after the monitoring/threshold/Telegram patch:

- TS2741: legacy `MonitoringDashboard` did not provide `actuatorHistory`.
- TS7006: obsolete `renderSeries={(item) => ...}` callback had no contextual type.

Changes:
1. `CanonicalDeviceMonitoringDialog.actuatorHistory` is optional for backward compatibility. The active canonical Monitoring page still supplies real actuator history, so actuator charts remain enabled there.
2. Removes the obsolete `renderSeries` prop from legacy `MonitoringDashboard`; the dashboard's own series chart rendering is unchanged.

No backend files, migrations, environment files, routes, or source files are deleted.
