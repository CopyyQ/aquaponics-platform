# Incident to outbox flow

`operational_incident_service` writes incident snapshots and uses idempotency
keys when it enqueues lifecycle events. The threshold refactor must ensure its
snapshot contains canonical metric, direction, value, threshold, configured
risk and message; Telegram should consume that snapshot only.
