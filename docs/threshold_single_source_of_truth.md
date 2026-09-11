# Threshold single source of truth

`threshold_alert_configs = only runtime authority`

## Canonical consumers

- Sensor Detail GET/POST/PATCH.
- Project Monitoring batch latest read.
- Sensor threshold incident evaluator.
- Sensor provisioning from SensorModel/DeviceTemplate defaults.
- Incident threshold/risk/message snapshot at transition time.

Notification settings, recipients, risk policies, delivery history, Telegram
formatting, and the message catalog do not own or evaluate Sensor thresholds.
SCADA measurement quality uses engineering validity ranges, not operational
alert thresholds; SCADA gets active fault state from incidents.

## Retained compatibility fields

Legacy threshold columns on `sensors`, model/template default fields, historical
`SensorAlert`, and older `AlertRule` records are retained. Model/template values
may seed a canonical row during provisioning. Legacy Sensor values may be
materialized by migration only when no canonical row exists. None is allowed to
compete with an existing canonical row.

`app/services/alert_service.py::evaluate_threshold` and
`app/services/sensor_threshold_config.py` are compatibility code with no runtime
caller. They are not deleted in this task. The telemetry runtime must not invoke
the Sensor `AlertRule` threshold/profile evaluator alongside the canonical
evaluator.

