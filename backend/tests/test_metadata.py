from sqlalchemy import BigInteger

from app.db.base import Base
from app import models  # noqa: F401


def test_database_has_expected_platform_tables() -> None:
    assert sorted(Base.metadata.tables) == [
        "actuator_commands",
        "actuator_feedback_bindings",
        "actuator_model_feedback_definitions",
        "actuator_models",
        "actuator_state_history",
        "actuators",
        "alert_rule_actuator_model_profiles",
        "alert_rule_actuator_models",
        "alert_rule_actuator_overrides",
        "alert_rule_profiles",
        "alert_rule_project_overrides",
        "alert_rule_revisions",
        "alert_rule_sensor_model_profiles",
        "alert_rule_sensor_models",
        "alert_rule_sensor_overrides",
        "alert_rules",
        "audit_logs",
        "device_credentials",
        "device_template_actuators",
        "device_template_sensors",
        "device_templates",
        "devices",
        "notification_deliveries",
        "notification_outbox",
        "operational_incidents",
        "project_members",
        "project_notification_recipients",
        "project_notification_risk_policies",
        "project_notification_settings",
        "project_public_settings",
        "projects",
        "scada_dashboards",
        "sensor_alerts",
        "sensor_models",
        "sensors",
        "telemetry_aggregates",
        "telemetry_readings",
        "users",
    ]


def test_device_project_foreign_key_is_indexed_and_not_unique() -> None:
    devices = Base.metadata.tables["devices"]
    project_column = devices.c.project_id
    assert project_column.nullable is False
    assert any(fk.column.table.name == "projects" for fk in project_column.foreign_keys)
    project_indexes = [index for index in devices.indexes if "project_id" in index.columns.keys()]
    assert project_indexes
    assert all(not index.unique for index in project_indexes)


def test_project_and_sensor_metadata_support_current_business_model() -> None:
    projects = Base.metadata.tables["projects"]
    sensors = Base.metadata.tables["sensors"]
    users = Base.metadata.tables["users"]
    assert {"location", "status"}.issubset(projects.c.keys())
    assert "installation_location" in sensors.c
    assert "password_changed_at" in users.c
    assert {"value_type", "chart_type", "is_active"}.issubset(
        Base.metadata.tables["sensor_models"].c.keys()
    )


def test_template_catalog_is_separate_from_runtime_devices() -> None:
    templates = Base.metadata.tables["device_templates"]
    devices = Base.metadata.tables["devices"]
    assert not {"project_id", "last_seen_at", "status", "mqtt_topic"}.intersection(
        templates.c.keys()
    )
    assert devices.c.project_id.nullable is False
    assert devices.c.device_template_id.nullable is True
    assert any(fk.column.table.name == "device_templates" for fk in devices.c.device_template_id.foreign_keys)


def test_template_can_contain_many_sensor_models() -> None:
    mappings = Base.metadata.tables["device_template_sensors"]
    assert {"device_template_id", "sensor_model_id", "sort_order", "is_required"}.issubset(mappings.c.keys())
    assert any(constraint.name == "uq_device_template_sensor_model" for constraint in mappings.constraints)


def test_template_actuator_configuration_and_notification_risk_policy_are_persisted() -> None:
    actuators = Base.metadata.tables["device_template_actuators"]
    assert {"code", "actuator_type", "default_state", "command_capability", "monitor_current", "electrical_profile_id", "sort_order", "is_enabled"}.issubset(actuators.c.keys())
    assert "current_a" not in actuators.c.keys()
    assert any(constraint.name == "uq_device_template_actuator_code" for constraint in actuators.constraints)
    feedbacks = Base.metadata.tables["actuator_model_feedback_definitions"]
    assert {"actuator_model_id", "feedback_role", "sensor_model_id", "value_key", "unit", "data_type", "default_lower_threshold", "default_upper_threshold", "is_required", "is_enabled"}.issubset(feedbacks.c.keys())
    assert any(constraint.name == "uq_actuator_model_feedback_role" for constraint in feedbacks.constraints)
    notifications = Base.metadata.tables["project_notification_settings"]
    assert {"risk_extreme_enabled", "risk_very_high_enabled", "risk_high_enabled", "risk_medium_enabled", "risk_low_medium_enabled", "risk_low_enabled", "notify_alert_recovered"}.issubset(notifications.c.keys())
    policies = Base.metadata.tables["project_notification_risk_policies"]
    assert {"project_id", "risk_level", "telegram_enabled", "notify_on_open", "notify_on_escalation", "notify_on_recovery", "notify_on_resolved", "reminder_enabled", "initial_reminder_seconds", "repeat_interval_seconds", "max_reminders", "stop_reminders_on_ack"}.issubset(policies.c.keys())
    assert any(constraint.name == "uq_project_notification_risk_policy" for constraint in policies.constraints)
    assert "skip_reason" in Base.metadata.tables["notification_outbox"].c.keys()


def test_all_primary_keys_are_bigint_identity() -> None:
    for table in Base.metadata.tables.values():
        if table.name in {"alert_rule_actuator_model_profiles", "alert_rule_sensor_model_profiles", "alert_rule_actuator_models", "alert_rule_sensor_models"}:
            assert len(table.primary_key.columns) == 2
            assert all(isinstance(column.type, BigInteger) for column in table.primary_key.columns)
            continue
        column = table.c.id
        assert isinstance(column.type, BigInteger)
        assert column.identity is not None
        assert column.identity.always is True
