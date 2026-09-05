# Project SCADA

## Product purpose

`Sơ đồ vận hành` is a Project-scoped operational view of the aquaponics process. It is separate from Overview (priorities), Monitoring (sensor history), and Device detail (configuration and Energy Monitor dashboard).

## Route and navigation

The route is `/admin/projects/{projectId}/scada` for administrators and `/projects/{projectId}/scada` for Project users. Project navigation exposes `Sơ đồ vận hành` beside Overview, Monitoring, Devices, Alerts, and Members.

## Rendering decision

The initial scene uses React Three Fiber, procedural geometry, an orthographic camera, limited pan/zoom, and no loaders, textures, shaders, post-processing, physics, or free-flight camera. HTML remains responsible for controls, details, issues, and the accessibility fallback.

## Runtime read model

`GET /api/v1/projects/{project_id}/scada/runtime` is one Project-scoped batch read. It returns layout, devices, sensors, actuators, issues, summary counters, and server `updated_at`. The current vertical slice derives the initial layout from the Project's existing runtime entities; a persisted draft/published dashboard table is intentionally not introduced until its migration and editor contract are reviewed.

## State semantics

Lifecycle (`ENABLED`/`DISABLED`), connectivity, freshness, quality, and actuator desired/reported state are separate. Missing telemetry is `NO_DATA` and renders `—`; it is never converted to zero. `resolveScadaVisualState` centralizes visual precedence.

## Safety and limitations

The current slice is read-only. No actuator command endpoint or optimistic reported-state update is added. Energy Monitor recognition continues to use `DeviceTemplate.device_kind`, and the SCADA scene only shows its runtime summary. Layout editing, persisted versions, binding mutation validation, audit events, and command/ACK flow remain follow-up work.

## Accessibility and performance

The page exposes a semantic HTML status/issue region and a list/detail fallback around the WebGL scene. Geometry/materials are reused, pixel ratio is capped, and runtime polling is page-level at 15 seconds. Browser FPS, WebGL context-loss behavior, and production container deployment require an environment with the application services installed and running.
