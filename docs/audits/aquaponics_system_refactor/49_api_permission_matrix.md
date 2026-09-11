# API permission matrix

Canonical routes use one stable permission per operation: systems (`aquaponics_systems.*`), devices (`devices.*`), sensors (`sensors.*`), sensor telemetry/thresholds, actuators (`actuators.*`), and sensor-model catalog operations (`sensor_models.*`). Every mutation has a create/update/delete permission dependency and then performs an ownership scope check.
