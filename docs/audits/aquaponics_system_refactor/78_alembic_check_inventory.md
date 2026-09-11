# Alembic 0050 check inventory

The unfiltered development check reported no real canonical drift. It reported five reflected archive tables: `legacy_actuator_feedback_bindings`, `legacy_actuator_model_feedback_definitions`, `legacy_alert_rule_evaluator_classifications`, `legacy_device_template_classifications`, and `legacy_sensor_classifications`. The two feedback archive tables have five reflected secondary indexes in total.

All other operations were paired remove/add differences where a pre-0046 index or unique-constraint name retained `project` while the canonical metadata name uses `aquaponics_system`. The relation, indexed columns and order, uniqueness, expression, and partial predicate are identical. There are no type, foreign-key, column, default, or canonical-table differences in the inventory.

Classification: `REAL_CANONICAL_DRIFT=0`, `ARCHIVE_TABLE=5`, `ARCHIVE_INDEX=5`, `COMPATIBILITY_INDEX=14`, and `INDEX_NAME_ONLY_DIFFERENCE=7` unique-constraint names. The explicit filter in `backend/alembic/env.py` is applied by both `alembic check` and `alembic revision --autogenerate`.
