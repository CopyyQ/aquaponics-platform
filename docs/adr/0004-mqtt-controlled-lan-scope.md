# ADR 0004: MQTT controlled-LAN scope

Status: Accepted

## Context
Current Mosquitto allows anonymous TCP/1883 without TLS.
## Decision
Treat MQTT as development/controlled-LAN only and never publish it directly to the Internet.
## Consequences
Certificates/TLS/auth redesign are not blockers now; production network controls remain mandatory.
## Rejected alternatives
Unplanned PKI/mTLS and public anonymous broker.
## Follow-up work
Perform a production threat/network review before Internet exposure.
