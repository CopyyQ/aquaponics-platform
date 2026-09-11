# Frontend permission map

The active UI authorizes visibility and mutation affordances from `GET /api/v1/auth/session` → `session.permissions`. The backend remains authoritative.

| UI surface/action | Permission code from live RBAC | Backend operation |
| --- | --- | --- |
| System list/detail | `aquaponics_systems.read` | system read endpoints |
| Create system | `aquaponics_systems.create` | `POST /aquaponics-systems` |
| Device list/detail/create | `devices.read`, `devices.create` | nested device endpoints |
| Sensor create/detail/telemetry | `sensors.create`, `sensors.thresholds.read`, `sensors.telemetry.read` | nested sensor endpoints |
| Sensor threshold create/update/delete | `sensors.thresholds.create`, `sensors.thresholds.update`, `sensors.thresholds.delete` | nested `threshold-alert` |
| Actuator detail/command/history/readings | `actuators.read`, `actuators.commands.create`, `actuators.commands.read`, `actuators.readings.read` | nested actuator endpoints |
| Actuator thresholds | `actuators.thresholds.read`, `actuators.thresholds.create`, `actuators.thresholds.update`, `actuators.thresholds.delete` | nested `threshold-alerts/{metric}` |
| Monitoring | `monitoring.read` | batch latest/series |
| Alerts | `incidents.read`, `incidents.acknowledge`, `incidents.resolve` | system Alert endpoints |
| Members | `aquaponics_systems.read`, `aquaponics_systems.manage_members` | system member endpoints |
| Activities | `activities.read` | system activities |
| SCADA | `scada.read`, `scada.update` | runtime/draft/publish |
| Alert settings | `aquaponics_systems.read`, `aquaponics_systems.update` | system alert settings |
| Catalogs | `device_templates.*`, `sensor_models.*`, `actuator_models.*` | canonical catalog endpoints |
| Users | `users.read` | canonical users read endpoints |

Unknown permission codes: 0. Role-based frontend authorization: removed from the active router and AppShell.
