# Sensor threshold incidents and notifications

The canonical path for normal Sensor measurement alerts is:

`MQTT telemetry → TelemetryReading → Sensor threshold evaluator → OperationalIncident → NotificationOutbox → notification worker → Telegram`.

The Sensor owns the enabled flag, lower and upper thresholds, optional below/above messages, risk override and delay. A SensorModel provides defaults; a DeviceTemplate mapping may override those defaults when a Sensor is provisioned. The materialized Sensor is the runtime source and snapshots its message, threshold, observed value, risk and timestamps into the incident.

An empty message is rendered as a Vietnamese Sensor-specific default. The Telegram worker formats the channel message; Sensor configuration must not include Telegram markup.

`AlertRule` remains transitional for explicit actuator-feedback profiles. It is not evaluated for ordinary Sensor threshold monitoring. `SensorAlert` remains historical compatibility data and is no longer written by telemetry threshold ingestion. The legacy AlertRule table must not be dropped until existing Sensor profiles have been classified and migrated without ambiguity.
