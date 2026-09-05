# ADR 0003: Power values as Sensors

Status: Accepted

## Context
Existing Sensor/Telemetry machinery already models measurements and aggregation.
## Decision
Represent voltage/current/power/energy as SensorModels and Sensors; chart only POWER_W initially.
## Consequences
No new reading tables; energy is raw COUNTER; no V×I inference.
## Rejected alternatives
Power microservice, device_components and power-specific tables.
## Follow-up work
Confirm chipset, AC/DC, sampling and counter reset/wrap behavior.
