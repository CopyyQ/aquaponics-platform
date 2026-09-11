# Alembic autogenerate exclusion policy

Canonical ORM metadata remains authoritative for every active runtime table. Alembic continues to compare normal tables, columns, indexes, foreign keys, unique constraints, types, and defaults. `compare_type` remains enabled.

Only five tables are excluded: `legacy_actuator_feedback_bindings`, `legacy_actuator_model_feedback_definitions`, `legacy_alert_rule_evaluator_classifications`, `legacy_device_template_classifications`, and `legacy_sensor_classifications`. Migrations 0048 and 0049 retain them as historical evidence; active business code does not use them as runtime authority. Their archive indexes are excluded through their excluded table.

The remaining exact names in `COMPATIBILITY_NAMES` are pre-canonical `project` index/unique names and their equivalent canonical metadata names. Each pair was verified as semantically identical, so filtering prevents a rename-only drop/recreate proposal. The filter is intentionally an explicit allow-list. A future archive artifact requires a migration, proof that current runtime code does not own it, archive row-count verification, and an explicit review/update to both the code and JSON policy. Never broaden this filter by prefix or disable an entire comparison category.
