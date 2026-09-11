# Data migration map

| Legacy source | Canonical destination | Transformation |
|---|---|---|
| Feedback voltage/current Sensor telemetry | `actuator_readings` | Backfilled only where actuator relationship was unambiguous; timestamps and values retained. |
| Sensor threshold fields | `threshold_alert_configs` (`SENSOR_VALUE`) | Directional thresholds, messages, enabled state, and risk copied. |
| Actuator electrical thresholds | `threshold_alert_configs` (`VOLTAGE`/`CURRENT`) | Direct actuator target and metric identity. |
| Mixed Device Sensors | Original Device changed to `SENSOR_DEVICE` | Sensor identity and telemetry retained. |
| Mixed Device Actuators | Deterministic `-ACTUATORS` Device clone | Actuator foreign keys remapped to `ACTUATOR_DEVICE`. |
