# Frontend API 0050 Remap

Generated from `http://127.0.0.1:8000/openapi.json` at 2026-09-08T02:59:32.643680+00:00.

- OpenAPI operations audited: **82**
- Active frontend consumers: **30**
- Missing mappings: **0**
- Stale mappings: **0**
- Unknown form fields: **0**
- Unknown response properties: **0**
- Legacy active-source terms: **0**

The client is centralized in `frontend/src/api/resources.ts`; pages do not call Axios directly. Monitoring uses the server-supported ranges `1h`, `6h`, `12h`, `24h`, and `30d`. Alert resources support both Sensor and Actuator sources.
