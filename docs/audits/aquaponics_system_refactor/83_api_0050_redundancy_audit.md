# API 0050 redundancy audit

## DELETED

`/admin/**`, `/projects/**`, Overview, public Notification, monitoring summary, template restore/sync/reprovision, current-profile APIs, and duplicate `GET /auth/me`.

## MERGED

Sensor and Actuator operational incidents now share the canonical Alert read/lifecycle API. MQTT configuration has one export endpoint.

## RENAMED

Public Project vocabulary became AquaponicsSystem, including activities, status, MQTT identity, SCADA identity, and monitoring identifiers. The ambiguous `1m` range became `30d`.

## KEPT

SCADA issues remain separate from Alerts: issues are layout/connectivity/command diagnostics; Alerts are persisted operational incidents. Internal notification outbox/delivery remains transport infrastructure.

## REVIEW RESOLVED

Threshold source of truth is `threshold_alert_configs`; firmware export contains no threshold, owner, summary, alert, notification, permission, or SCADA data. P0 = 0. P1 = 0.
