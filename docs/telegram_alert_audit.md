# Telegram alert pipeline audit

Audit date: 2026-09-08. Repository state audited before the Telegram/alert
remediation. The worktree already contained a large uncommitted canonical API
refactor; those files are treated as retained work and are not reverted.

## Executive finding

The canonical Sensor threshold table already exists and Alembic has one head,
`0052`. Monitoring and the new incident evaluator read that table. The reported
failure is nevertheless reproducible by inspection because threshold create and
update commit without evaluating the latest reading. In addition, telemetry
still invokes the older `AlertRule` Sensor evaluator after the canonical
evaluator, notification configuration mutations do not reconcile already-active
incidents, and actuator electrical evaluation treats voltage and current as
independent thresholds.

## Pipeline trace

1. MQTT enters `app/mqtt/consumer.py` and is dispatched by
   `app/mqtt/handlers.py::handle_telemetry`.
2. `app/services/telemetry_ingest_service.py::ingest_mqtt_telemetry` validates
   the device-owned topic context and server timestamp limits. Project, User, or
   database identifiers are not accepted from the payload.
3. `app/services/telemetry_service.py::ingest_telemetry` inserts accepted data
   into `telemetry_readings`. The latest Sensor reading is derived with a
   lateral/ordered query in `app/queries/monitoring_queries.py`; there is no
   separate mutable latest-reading record.
4. The canonical lookup is
   `threshold_alert_config_service.get_sensor_threshold_alert_config`, reading
   `threshold_alert_configs` with `metric_type = SENSOR_VALUE`.
5. `operational_incident_service.evaluate_sensor_threshold_incident` evaluates
   BELOW/NORMAL/ABOVE and creates or updates `operational_incidents`.
6. The same transaction inserts `notification_outbox` via `_enqueue`. Duplicate
   OPEN events are prevented by the incident active-key index and outbox
   `idempotency_key`.
7. `jobs/notification_outbox.py` calls
   `notification_outbox_service.process_notification_outbox`.
8. Policy is resolved from `project_notification_settings` and
   `project_notification_risk_policies`; recipients come from
   `project_notification_recipients`.
9. `telegram_notifier.TelegramNotifier` performs the Telegram HTTP request.
10. Per-recipient results are persisted to `notification_deliveries`; the
    system-scoped history endpoint joins through `notification_outbox`.

## Required audit questions

| Question | Audited answer before remediation |
|---|---|
| MQTT ingest | `mqtt/handlers.py` -> `telemetry_ingest_service.py` -> `telemetry_service.py`. |
| Latest Sensor reading | `telemetry_readings`, selected by `recorded_at DESC, id DESC`. |
| Threshold model | `app/models/threshold_alert_config.py::ThresholdAlertConfig`. |
| Sensor Detail write | Canonical POST/PATCH routes write `threshold_alert_configs`. |
| Monitoring threshold read | Batch map in `monitoring_service._sensor_threshold_map`, from `threshold_alert_configs`. |
| Evaluator threshold read | Canonical evaluator reads `threshold_alert_configs`, but telemetry also calls the legacy/advanced Sensor `AlertRule` evaluator. This is a competing runtime detection path and must be removed from Sensor telemetry. |
| SCADA threshold read | SCADA does not classify measurement quality from operational thresholds. It reads latest telemetry plus incident state. |
| Alert API source | `operational_incidents`, scoped by `aquaponics_system_id`. |
| Legacy Sensor fields | Still present for compatibility/migration. `alert_service.evaluate_threshold` reads them but has no runtime caller; `sensor_threshold_config.py` also reads them but has no caller. They must remain outside runtime and be documented. |
| NULL directional risk | `0052` backfills it and the mutation helper defaults lower to LOW and upper to HIGH. Provisioning also invokes the helper. PATCH schema, however, needs partial-update validation tests. |
| Incident OPEN | Canonical evaluator opens one direction-specific incident and enqueues one OPEN event. Persistent abnormal samples update count/snapshot only. |
| Outbox enqueue | `operational_incident_service._enqueue`, in the caller transaction. |
| Worker skip | Policy, stale/offline, and no-recipient checks are in `notification_outbox_service.process_notification_outbox`. |
| Telegram OFF -> ON | No reconcile existed. An already-open incident could remain silent forever. |
| Recipient added/enabled | No reconcile existed. |
| Risk/event enabled | No reconcile existed. |
| Threshold update | No latest-reading re-evaluation existed. |
| Outbox system scope | `aquaponics_system_id` exists and `0052` backfills it through incidents. |
| History isolation | Endpoint filters `NotificationOutbox.project_id == system_id` after membership/RBAC checks. |
| Retry | Up to five attempts, exponential backoff capped at one hour; Telegram 429 may supply `retry_after`. |
| Idempotency | Unique incident lifecycle outbox key plus per-recipient delivery key. No ACTIVE_SYNC identity existed. |
| Reminder | Scheduler-driven, active incident + risk policy + cooldown/max count; not telemetry-sample-driven. |
| Recovery/resolved | Canonical threshold normalization currently emits RESOLVED. Policy supports RECOVERED and RESOLVED, but semantics need one canonical automatic-recovery event. |
| Permissions | Fine-grained permission codes plus `require_project_access`; notification writes require manage access. |
| IDOR | Resource helper queries include system -> device -> Sensor/Actuator ownership; notification recipient lookup includes both recipient ID and system ID. No direct cross-system query was found in the audited routes. Tests are still required. |

## Root causes and severity

- P0: threshold create/PATCH does not re-evaluate the latest valid reading.
- P0: notification settings and recipient mutations do not reconcile active
  incidents.
- P0: actuator current/voltage are evaluated independently. An actuator that is
  OFF at 0 A can therefore be treated as abnormal if a direct threshold is set.
- P0: telemetry invokes both canonical Sensor thresholds and `AlertRule`
  Sensor evaluators, so a catalog rule may compete with user thresholds.
- P1: history exposes only a reduced projection and cannot consistently explain
  outbox-level skips, retry timing, or a sanitized provider failure.
- P1: missing bot configuration is handled as a retrying send failure instead of
  a deterministic `BOT_NOT_CONFIGURED` skip.
- P1: recipient Chat ID validation accepts arbitrary non-empty text.
- P1: Telegram formatting does not yet render the structured consequence and
  recommended actions required by the workbook.
- P1: `ProjectNotificationSettings.in_app_enabled` exists, but the detailed
  delivery settings contract omits it; the shorter alert settings route models
  `enabled` indirectly as `notify_alert_opened`.

## Frontend capability audit

The original Git tree and current worktree both contain the mature monitoring
capabilities: `ProjectMonitoringPage`, `ProjectMonitoringView`,
`ProjectDeviceMonitoringCard`, `DeviceMonitoringDialog`,
`ActuatorStateHistoryChart`, and `ActuatorHistoryStatistics`. The actuator dialog
supports actuator selection, range selection, state chart, gaps, desired and
reported state, synchronization status, latest command, electrical snapshot,
and duration/statistics. These are capabilities to preserve and map, not legacy
files to delete.

The current canonical pages coexist with the original feature/widget modules.
Frontend work must reuse the typed API layer and preserve the original dialog
capabilities after backend contracts pass.

## Planned canonical boundary

- Sensor threshold detection: `threshold_alert_configs` only.
- Sensor catalog: semantic content only; no runtime numeric threshold.
- Actuator fault detection: reported/desired state plus model electrical
  capability, evaluated as mutually exclusive composite conditions.
- Notification policy: determines channel, recipient, lifecycle eligibility,
  retry, reminders, and history; it never re-evaluates measurement thresholds.
- Reconciliation: backend service invoked by meaningful settings/policy/
  recipient transitions, with recipient-specific idempotency.

