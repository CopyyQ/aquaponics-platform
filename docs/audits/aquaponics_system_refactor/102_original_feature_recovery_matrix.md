# Original feature recovery matrix

| Original feature | Original purpose | Restored/adapted | Canonical API | Final route | Status |
| --- | --- | --- | --- | --- | --- |
| AppShell / theme | Desktop sidebar, mobile drawer, dark mode, profile menu | AppShell adapted to `session.permissions` | `/auth/session`, `/auth/logout` | Global | ADAPTED |
| Project layout | Identity, breadcrumb, nested tabs | AquaponicsSystemLayout | `/aquaponics-systems/{system_id}` | `/aquaponics-systems/:systemId/*` | ADAPTED |
| Overview | Health, KPI, device/sensor/alert attention | Batch view model and dashboard cards | devices + monitoring/latest + alerts | `.../:systemId/overview` | ADAPTED |
| Monitoring | Latest cards, range selection, charts | Batch latest/series dashboard | `monitoring/latest`, `monitoring/series` | `.../:systemId/monitoring` | ADAPTED |
| Device lifecycle | Mixed runtime device detail | Mixed Sensor + Actuator cards and links | `/devices`, nested Sensor/Actuator operations | `.../:systemId/devices` | ADAPTED |
| Sensor detail | Telemetry and threshold configuration | SVG series chart, null threshold state, CRUD | telemetry + threshold-alert | `.../sensors/:sensorId` | ADAPTED |
| Actuator detail | Command/history/readings/electrical threshold | POST command, history, readings, voltage/current thresholds | commands + readings + threshold-alerts | `.../actuators/:actuatorId` | ADAPTED |
| SCADA | Visual operational process scene | R3F orthographic 2.5D scene, selection, issues, fallback list | one `scada/runtime` + draft/publish | `.../:systemId/scada` | ADAPTED |
| Alerts | Lifecycle list/detail/actions | Sensor/Actuator alert list, acknowledge, resolve | system alerts endpoints | `.../:systemId/alerts` | ADAPTED |
| Members | Membership management | list/add/update/remove with current role values | system members endpoints | `.../:systemId/members` | ADAPTED |
| Activities | Audit/log presentation | Human-readable activity rows | system activities | `.../:systemId/activities` | ADAPTED |
| Settings | System alert settings | Enabled/in-app/Telegram policy toggles | system alert settings | `.../:systemId/settings` | ADAPTED |
| Device templates | Catalog and mappings | Template/model catalog presentation and creation | canonical catalog endpoints | `/catalogs` | ADAPTED |
| Users/customer directory | User presentation | Canonical users read list | `/users` | `/users` | ADAPTED |
| Login/profile/not-found | Authentication and account UX | Canonical session, profile, password confirmation, 404 | auth endpoints | `/login`, `/profile`, `*` | ADAPTED |

Accidentally lost: 0. Frontend deletions after recovery: 0.
