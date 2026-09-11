# Notification and Telegram audit

Audit date: 2026-09-07. This audit is read-only; no notification runtime code,
database values, or migrations were changed for this audit.

Telegram delivery is implemented with the Bot HTTP API through `httpx` in
`backend/app/services/telegram_notifier.py`. The principal intended path is
`OperationalIncident -> NotificationOutbox -> NotificationDelivery -> Telegram`.
The outbox worker uses project settings, per-risk policy and enabled project
recipients.

The architecture is not yet single-path. Direct Telegram sends also exist for
recipient test, project activity, and legacy project notification functions.
`project_notification_service.py` retains a large hard-coded business alert
catalogue and legacy feedback/rule context. The outbox formatter also contains
legacy `feedback_role` and threshold presentation logic. These are material
risks for the upcoming canonical threshold cutover.

No token literal or production chat ID was found outside ignored local `.env`.
`TELEGRAM_BOT_TOKEN` is a secret setting; reports deliberately do not reproduce
its value.
