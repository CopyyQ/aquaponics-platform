# API 0050 short tree

```text
/health
/api/v1
├── auth/{login,session,me(PATCH),change-password,logout}
├── users[/{user_id}]
├── aquaponics-systems[/{system_id}]
│   ├── devices/{device_id}/{sensors,actuators}
│   ├── monitoring/{latest,series}
│   ├── alerts[/{alert_id}/{acknowledge,resolve}] and alerts/settings
│   ├── members, activities, scada/{runtime,layout/draft,layout/publish}
│   └── mqtt-config/export
├── device-templates[/{template_id}/{sensors,actuators}]
├── sensor-models
└── actuator-models
```
