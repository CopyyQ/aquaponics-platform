# API 0050 final map

All system-scoped routes enforce both a database-backed permission and AquaponicsSystem ownership/membership scope.

| Method | Path | Purpose | Parent | Permission | Scope | Consumers | Why it exists |
|---|---|---|---|---|---|---|---|
| POST | `/api/v1/auth/login` | Login | global | `authenticated/self` | global | Frontend | Canonical Authentication capability |
| GET | `/api/v1/auth/session` | Session | global | `authenticated/self` | global | Frontend | Canonical Authentication capability |
| PATCH | `/api/v1/auth/me` | Update Me | global | `authenticated/self` | global | Frontend | Canonical Authentication capability |
| POST | `/api/v1/auth/change-password` | Change Password | global | `authenticated/self` | global | Frontend | Canonical Authentication capability |
| POST | `/api/v1/auth/logout` | Logout | global | `authenticated/self` | global | Frontend | Canonical Authentication capability |
| GET | `/api/v1/aquaponics-systems` | List Systems | aquaponics-systems | `aquaponics_systems.*` | global | Frontend | Canonical Aquaponics Systems capability |
| POST | `/api/v1/aquaponics-systems` | Create System | aquaponics-systems | `aquaponics_systems.*` | global | Frontend | Canonical Aquaponics Systems capability |
| GET | `/api/v1/aquaponics-systems/{system_id}` | Get System | aquaponics-systems | `aquaponics_systems.*` | AquaponicsSystem | Frontend | Canonical Aquaponics Systems capability |
| PATCH | `/api/v1/aquaponics-systems/{system_id}` | Update System | aquaponics-systems | `aquaponics_systems.*` | AquaponicsSystem | Frontend | Canonical Aquaponics Systems capability |
| DELETE | `/api/v1/aquaponics-systems/{system_id}` | Delete System | aquaponics-systems | `aquaponics_systems.*` | AquaponicsSystem | Frontend | Canonical Aquaponics Systems capability |
| GET | `/api/v1/aquaponics-systems/{system_id}/devices` | List Devices | devices | `devices.*` | AquaponicsSystem | Frontend | Canonical Devices capability |
| POST | `/api/v1/aquaponics-systems/{system_id}/devices` | Create Device | devices | `devices.*` | AquaponicsSystem | Frontend | Canonical Devices capability |
| GET | `/api/v1/aquaponics-systems/{system_id}/devices/{device_id}` | Get Device | devices | `devices.*` | AquaponicsSystem | Frontend | Canonical Devices capability |
| PATCH | `/api/v1/aquaponics-systems/{system_id}/devices/{device_id}` | Update Device | devices | `devices.*` | AquaponicsSystem | Frontend | Canonical Devices capability |
| DELETE | `/api/v1/aquaponics-systems/{system_id}/devices/{device_id}` | Delete Device | devices | `devices.*` | AquaponicsSystem | Frontend | Canonical Devices capability |
| GET | `/api/v1/aquaponics-systems/{system_id}/devices/{device_id}/sensors` | List Sensors | sensors | `sensors.*` | AquaponicsSystem | Frontend | Canonical Sensors capability |
| POST | `/api/v1/aquaponics-systems/{system_id}/devices/{device_id}/sensors` | Create Sensor | sensors | `sensors.*` | AquaponicsSystem | Frontend | Canonical Sensors capability |
| GET | `/api/v1/aquaponics-systems/{system_id}/devices/{device_id}/sensors/{sensor_id}` | Get Sensor | sensors | `sensors.*` | AquaponicsSystem | Frontend | Canonical Sensors capability |
| PATCH | `/api/v1/aquaponics-systems/{system_id}/devices/{device_id}/sensors/{sensor_id}` | Update Sensor | sensors | `sensors.*` | AquaponicsSystem | Frontend | Canonical Sensors capability |
| DELETE | `/api/v1/aquaponics-systems/{system_id}/devices/{device_id}/sensors/{sensor_id}` | Delete Sensor | sensors | `sensors.*` | AquaponicsSystem | Frontend | Canonical Sensors capability |
| GET | `/api/v1/aquaponics-systems/{system_id}/devices/{device_id}/actuators` | List Actuators | actuators | `actuators.*` | AquaponicsSystem | Frontend | Canonical Actuators capability |
| POST | `/api/v1/aquaponics-systems/{system_id}/devices/{device_id}/actuators` | Create Actuator | actuators | `actuators.*` | AquaponicsSystem | Frontend | Canonical Actuators capability |
| GET | `/api/v1/aquaponics-systems/{system_id}/devices/{device_id}/actuators/{actuator_id}` | Get Actuator | actuators | `actuators.*` | AquaponicsSystem | Frontend | Canonical Actuators capability |
| PATCH | `/api/v1/aquaponics-systems/{system_id}/devices/{device_id}/actuators/{actuator_id}` | Update Actuator | actuators | `actuators.*` | AquaponicsSystem | Frontend | Canonical Actuators capability |
| DELETE | `/api/v1/aquaponics-systems/{system_id}/devices/{device_id}/actuators/{actuator_id}` | Delete Actuator | actuators | `actuators.*` | AquaponicsSystem | Frontend | Canonical Actuators capability |
| GET | `/api/v1/aquaponics-systems/{system_id}/devices/{device_id}/sensors/{sensor_id}/threshold-alert` | Get Sensor Threshold | sensors | `sensors.*` | AquaponicsSystem | Frontend | Canonical Sensors capability |
| POST | `/api/v1/aquaponics-systems/{system_id}/devices/{device_id}/sensors/{sensor_id}/threshold-alert` | Create Sensor Threshold | sensors | `sensors.*` | AquaponicsSystem | Frontend | Canonical Sensors capability |
| PATCH | `/api/v1/aquaponics-systems/{system_id}/devices/{device_id}/sensors/{sensor_id}/threshold-alert` | Update Sensor Threshold | sensors | `sensors.*` | AquaponicsSystem | Frontend | Canonical Sensors capability |
| DELETE | `/api/v1/aquaponics-systems/{system_id}/devices/{device_id}/sensors/{sensor_id}/threshold-alert` | Delete Sensor Threshold | sensors | `sensors.*` | AquaponicsSystem | Frontend | Canonical Sensors capability |
| GET | `/api/v1/aquaponics-systems/{system_id}/devices/{device_id}/sensors/{sensor_id}/telemetry` | Sensor Telemetry | sensors | `sensors.*` | AquaponicsSystem | Frontend | Canonical Sensors capability |
| GET | `/api/v1/aquaponics-systems/{system_id}/mqtt-config/export` | Export Mqtt Config | aquaponics-systems | `aquaponics_systems.*` | AquaponicsSystem | Device provisioning / operator export | Canonical Aquaponics Systems capability |
| GET | `/api/v1/aquaponics-systems/{system_id}/devices/{device_id}/actuators/{actuator_id}/readings` | Actuator Readings | actuators | `actuators.*` | AquaponicsSystem | Frontend | Canonical Actuators capability |
| GET | `/api/v1/aquaponics-systems/{system_id}/devices/{device_id}/actuators/{actuator_id}/commands` | Actuator Commands | actuators | `actuators.*` | AquaponicsSystem | Frontend | Canonical Actuators capability |
| POST | `/api/v1/aquaponics-systems/{system_id}/devices/{device_id}/actuators/{actuator_id}/commands` | Create Actuator Command | actuators | `actuators.*` | AquaponicsSystem | Frontend | Canonical Actuators capability |
| GET | `/api/v1/aquaponics-systems/{system_id}/devices/{device_id}/actuators/{actuator_id}/threshold-alerts/{metric}` | Get Actuator Threshold | actuators | `actuators.*` | AquaponicsSystem | Frontend | Canonical Actuators capability |
| POST | `/api/v1/aquaponics-systems/{system_id}/devices/{device_id}/actuators/{actuator_id}/threshold-alerts/{metric}` | Create Actuator Threshold | actuators | `actuators.*` | AquaponicsSystem | Frontend | Canonical Actuators capability |
| PATCH | `/api/v1/aquaponics-systems/{system_id}/devices/{device_id}/actuators/{actuator_id}/threshold-alerts/{metric}` | Update Actuator Threshold | actuators | `actuators.*` | AquaponicsSystem | Frontend | Canonical Actuators capability |
| DELETE | `/api/v1/aquaponics-systems/{system_id}/devices/{device_id}/actuators/{actuator_id}/threshold-alerts/{metric}` | Delete Actuator Threshold | actuators | `actuators.*` | AquaponicsSystem | Frontend | Canonical Actuators capability |
| GET | `/api/v1/aquaponics-systems/{system_id}/alerts` | List System Alerts | alerts | `incidents.* / notifications.settings.*` | AquaponicsSystem | Frontend | Canonical Alerts capability |
| GET | `/api/v1/aquaponics-systems/{system_id}/alerts/{alert_id}` | Get System Alert | alerts | `incidents.* / notifications.settings.*` | AquaponicsSystem | Frontend | Canonical Alerts capability |
| POST | `/api/v1/aquaponics-systems/{system_id}/alerts/{alert_id}/acknowledge` | Acknowledge System Alert | alerts | `incidents.* / notifications.settings.*` | AquaponicsSystem | Frontend | Canonical Alerts capability |
| POST | `/api/v1/aquaponics-systems/{system_id}/alerts/{alert_id}/resolve` | Resolve System Alert | alerts | `incidents.* / notifications.settings.*` | AquaponicsSystem | Frontend | Canonical Alerts capability |
| GET | `/api/v1/sensor-models` | List Sensor Models | global | `sensor_models.*` | global | Frontend | Canonical Sensor Models capability |
| POST | `/api/v1/sensor-models` | Create Sensor Model | global | `sensor_models.*` | global | Frontend | Canonical Sensor Models capability |
| GET | `/api/v1/sensor-models/{model_id}` | Get Sensor Model | global | `sensor_models.*` | global | Frontend | Canonical Sensor Models capability |
| PATCH | `/api/v1/sensor-models/{model_id}` | Update Sensor Model | global | `sensor_models.*` | global | Frontend | Canonical Sensor Models capability |
| DELETE | `/api/v1/sensor-models/{model_id}` | Delete Sensor Model | global | `sensor_models.*` | global | Frontend | Canonical Sensor Models capability |
| GET | `/api/v1/users` | List Users | global | `users.*` | global | Frontend | Canonical Users capability |
| GET | `/api/v1/users/{user_id}` | Get User | global | `users.*` | global | Frontend | Canonical Users capability |
| GET | `/api/v1/device-templates` | List Device Templates | device-templates | `device_templates.*` | global | Frontend | Canonical Device Templates capability |
| POST | `/api/v1/device-templates` | Create Device Template | device-templates | `device_templates.*` | global | Frontend | Canonical Device Templates capability |
| GET | `/api/v1/device-templates/{template_id}` | Get Device Template | device-templates | `device_templates.*` | global | Frontend | Canonical Device Templates capability |
| PATCH | `/api/v1/device-templates/{template_id}` | Update Device Template | device-templates | `device_templates.*` | global | Frontend | Canonical Device Templates capability |
| DELETE | `/api/v1/device-templates/{template_id}` | Delete Device Template | device-templates | `device_templates.*` | global | Frontend | Canonical Device Templates capability |
| GET | `/api/v1/device-templates/{template_id}/sensors` | List Template Sensors | device-templates | `device_templates.*` | global | Frontend | Canonical Device Templates capability |
| POST | `/api/v1/device-templates/{template_id}/sensors` | Add Template Sensor | device-templates | `device_templates.*` | global | Frontend | Canonical Device Templates capability |
| GET | `/api/v1/device-templates/{template_id}/sensors/{mapping_id}` | Get Template Sensor | device-templates | `device_templates.*` | global | Frontend | Canonical Device Templates capability |
| PATCH | `/api/v1/device-templates/{template_id}/sensors/{mapping_id}` | Update Template Sensor | device-templates | `device_templates.*` | global | Frontend | Canonical Device Templates capability |
| DELETE | `/api/v1/device-templates/{template_id}/sensors/{mapping_id}` | Delete Template Sensor | device-templates | `device_templates.*` | global | Frontend | Canonical Device Templates capability |
| GET | `/api/v1/device-templates/{template_id}/actuators` | List Template Actuators | device-templates | `device_templates.*` | global | Frontend | Canonical Device Templates capability |
| POST | `/api/v1/device-templates/{template_id}/actuators` | Add Template Actuator | device-templates | `device_templates.*` | global | Frontend | Canonical Device Templates capability |
| GET | `/api/v1/device-templates/{template_id}/actuators/{mapping_id}` | Get Template Actuator | device-templates | `device_templates.*` | global | Frontend | Canonical Device Templates capability |
| PATCH | `/api/v1/device-templates/{template_id}/actuators/{mapping_id}` | Update Template Actuator | device-templates | `device_templates.*` | global | Frontend | Canonical Device Templates capability |
| DELETE | `/api/v1/device-templates/{template_id}/actuators/{mapping_id}` | Delete Template Actuator | device-templates | `device_templates.*` | global | Frontend | Canonical Device Templates capability |
| GET | `/api/v1/actuator-models` | List Actuator Models | global | `actuator_models.*` | global | Frontend | Canonical Actuator Models capability |
| POST | `/api/v1/actuator-models` | Create Actuator Model | global | `actuator_models.*` | global | Frontend | Canonical Actuator Models capability |
| GET | `/api/v1/actuator-models/{model_id}` | Get Actuator Model | global | `actuator_models.*` | global | Frontend | Canonical Actuator Models capability |
| PATCH | `/api/v1/actuator-models/{model_id}` | Update Actuator Model | global | `actuator_models.*` | global | Frontend | Canonical Actuator Models capability |
| DELETE | `/api/v1/actuator-models/{model_id}` | Delete Actuator Model | global | `actuator_models.*` | global | Frontend | Canonical Actuator Models capability |
| GET | `/api/v1/aquaponics-systems/{system_id}/monitoring/latest` | Monitoring Latest | aquaponics-systems | `monitoring.read` | AquaponicsSystem | Frontend | Canonical Monitoring capability |
| GET | `/api/v1/aquaponics-systems/{system_id}/monitoring/series` | Monitoring Series | aquaponics-systems | `monitoring.read` | AquaponicsSystem | Frontend | Canonical Monitoring capability |
| GET | `/api/v1/aquaponics-systems/{system_id}/members` | List Members | aquaponics-systems | `aquaponics_systems.manage_members` | AquaponicsSystem | Frontend | Canonical Members capability |
| POST | `/api/v1/aquaponics-systems/{system_id}/members` | Add Member | aquaponics-systems | `aquaponics_systems.manage_members` | AquaponicsSystem | Frontend | Canonical Members capability |
| PATCH | `/api/v1/aquaponics-systems/{system_id}/members/{user_id}` | Update Member | aquaponics-systems | `aquaponics_systems.manage_members` | AquaponicsSystem | Frontend | Canonical Members capability |
| DELETE | `/api/v1/aquaponics-systems/{system_id}/members/{user_id}` | Remove Member | aquaponics-systems | `aquaponics_systems.manage_members` | AquaponicsSystem | Frontend | Canonical Members capability |
| GET | `/api/v1/aquaponics-systems/{system_id}/activities` | Activities | aquaponics-systems | `activities.read` | AquaponicsSystem | Frontend | Canonical Activities capability |
| GET | `/api/v1/aquaponics-systems/{system_id}/scada/runtime` | Scada Runtime | aquaponics-systems | `scada.*` | AquaponicsSystem | Frontend | Canonical SCADA capability |
| PUT | `/api/v1/aquaponics-systems/{system_id}/scada/layout/draft` | Scada Draft | aquaponics-systems | `scada.*` | AquaponicsSystem | Frontend | Canonical SCADA capability |
| POST | `/api/v1/aquaponics-systems/{system_id}/scada/layout/publish` | Scada Publish | aquaponics-systems | `scada.*` | AquaponicsSystem | Frontend | Canonical SCADA capability |
| GET | `/api/v1/aquaponics-systems/{system_id}/alerts/settings` | Get Alert Settings | alerts | `incidents.* / notifications.settings.*` | AquaponicsSystem | Frontend | Canonical Alerts capability |
| PUT | `/api/v1/aquaponics-systems/{system_id}/alerts/settings` | Put Alert Settings | alerts | `incidents.* / notifications.settings.*` | AquaponicsSystem | Frontend | Canonical Alerts capability |
| GET | `/health` | Health | global | `public infrastructure` | global | Infrastructure | Canonical System capability |
