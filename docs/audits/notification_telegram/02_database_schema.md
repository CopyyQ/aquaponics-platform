# Notification database schema

| Table | Purpose | Key integrity |
| --- | --- | --- |
| `operational_incidents` | incident snapshot and lifecycle | project, resource, context key, risk snapshot |
| `notification_outbox` | pending logical incident event | unique `idempotency_key`, status/available time index |
| `notification_deliveries` | per-recipient Telegram attempt | unique `idempotency_key`, outbox/status index |
| `project_notification_settings` | project-level Telegram/event/risk defaults | one row per project |
| `project_notification_risk_policies` | per-project/per-risk event and reminder policy | unique project/risk |
| `project_notification_recipients` | project Telegram chat recipients | unique project/chat ID |

The runtime DB read-only count audit found 115 incidents, 331 outbox records,
753 deliveries, one project settings row, six risk policies and three
recipients. Outbox statuses: 217 `PROCESSED`, 114 `SKIPPED`. Delivery statuses:
639 `SENT`, 114 `SKIPPED`.
