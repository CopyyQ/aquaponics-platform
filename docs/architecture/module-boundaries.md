# Module boundaries

| Module | Owns/tables | May read/call | Public interface/endpoints | Must not import | Tests |
|---|---|---|---|---|---|
| Identity | User, Auth, Role, lifecycle, token version; `users` | Projects membership summaries | auth/account services; `/auth`, `/users` | telemetry/actuation internals | login, lifecycle, password, role |
| Projects | Project, ProjectMember/access; `projects`, `project_members` | Identity status | access/member services; `/projects` | MQTT adapter | IDOR, Owner/Viewer membership |
| Devices | Device lifecycle/template instantiation/status; `devices` | Projects, Catalogs | device runtime lookup; Project Device endpoints | API routers | multiple Devices, disabled/offline |
| Catalogs | DeviceTemplate, SensorModel, ActuatorModel and mappings | none beyond identity audit actor | catalog queries/admin endpoints | runtime telemetry | seed/idempotency/mappings |
| Sensing | Sensor, thresholds/lifecycle; `sensors` | Devices, Catalogs | Device-scoped sensor lookup | telemetry API | Device scope, thresholds |
| Telemetry | Reading, aggregate, monitoring/power; `telemetry_readings`, `telemetry_aggregates` | Devices/Sensing public lookups | ingest/monitoring services; monitoring endpoints | API request objects | duplicate/out-of-order, aggregation |
| Alerts | SensorAlert lifecycle; `sensor_alerts` | Sensing/Telemetry public data | alert service/endpoints | MQTT callback SQL | threshold and Project access |
| Actuation | Actuator, command, state history; actuator tables | Devices/Catalogs public lookups | command/state services and endpoints | model-to-MQTT publishing | scoped identity, ACK/timeout |

Modules call another module only through an identified public application/query interface. Existing centralized packages are compatibility structure and must not gain duplicate implementations.
