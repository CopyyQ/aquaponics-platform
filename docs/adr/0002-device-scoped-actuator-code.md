# ADR 0002: Device-scoped actuator code

Status: Accepted

## Context
MQTT resolves Device from topic and actuator inside that Device; live schema had both global and scoped uniqueness.
## Decision
Identity is `UNIQUE(device_id, code)` after duplicate and consumer audit.
## Consequences
Different Devices may reuse firmware-friendly actuator codes; all lookups require Device scope.
## Rejected alternatives
Global code uniqueness and database actuator ID in MQTT.
## Follow-up work
Audit external clients before removing compatibility assumptions.
