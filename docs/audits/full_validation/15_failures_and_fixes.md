# Failures and fixes

1. Fresh migration initially failed at `0037` because the current-metadata bootstrap had already created the device type constraint. Migration now checks it first.
2. Fresh migration initially failed at `0043` because current metadata had already created `threshold_alert_configs`. Migration now performs its data backfill and returns in that bootstrap path.
3. PostgreSQL-backed notification tests initially failed because legacy fixture construction omitted the new required Device type. The ORM now defaults transitional construction to `SENSOR_DEVICE`; focused suite passes.
