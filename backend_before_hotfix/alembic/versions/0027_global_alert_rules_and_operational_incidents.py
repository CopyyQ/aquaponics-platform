"""Add global versioned alert rules and operational notification pipeline."""

from __future__ import annotations

import json

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "0027"
down_revision = "0026"
branch_labels = None
depends_on = None


RULES = [
    ("FISH_TANK_DO_LOW", "DO nước bể cá", "SENSOR", "THRESHOLD_BANDS", "EXTREME", {"unit": "mg/L", "bands": [{"severity": "WARNING", "operator": "LT", "value": 5}, {"severity": "CRITICAL", "operator": "LT", "value": 4}]}, None, "Cá stress, giảm ăn; thấp kéo dài có thể chết.", "INCOMPLETE"),
    ("FISH_TANK_AERATOR_NO_CURRENT", "Máy sủi oxy bể cá mất hoạt động", "ACTUATOR", "ACTUATOR_FEEDBACK", "EXTREME", {"expected_state": "ON", "feedback_role": "RUNNING_CURRENT", "min_running_current_a": None, "startup_grace_seconds": None, "debounce_seconds": None, "recovery_current_a": None, "recovery_duration_seconds": None}, "Máy sục oxy đang có vấn đề, cần kiểm tra!", "DO có thể tụt nhanh, đặc biệt ban đêm.", "INCOMPLETE"),
    ("FISH_TO_RFF_PUMP_NO_CURRENT", "Bơm hút từ bể cá lên bể RFF mất hoạt động", "ACTUATOR", "ACTUATOR_FEEDBACK", "EXTREME", {"expected_state": "ON", "feedback_role": "RUNNING_CURRENT", "min_running_current_a": None, "startup_grace_seconds": None, "debounce_seconds": None, "recovery_current_a": None, "recovery_duration_seconds": None}, "Bơm hút bể cá đang có vấn đề, cần kiểm tra!", "Chất thải không được đưa vào lọc; có thể ảnh hưởng tuần hoàn.", "INCOMPLETE"),
    ("NFT_PUMP_NO_CURRENT", "Bơm nước lên giàn NFT mất hoạt động", "ACTUATOR", "ACTUATOR_FEEDBACK", "EXTREME", {"expected_state": "ON", "feedback_role": "RUNNING_CURRENT", "min_running_current_a": None, "startup_grace_seconds": None, "debounce_seconds": None, "recovery_current_a": None, "recovery_duration_seconds": None}, "Bơm nước lên giàn đang có vấn đề, cần kiểm tra!", "Cây mất nước; rễ có thể khô nếu kéo dài.", "INCOMPLETE"),
    ("BIOFILTER_WATER_LEVEL_LOW", "Mực nước bể lọc vi sinh thấp", "SENSOR", "DIGITAL_STATE", "EXTREME", {"active_state": "LOW", "active_value": None}, "Mực nước bể lọc vi sinh thấp, kiểm tra bơm hút bể cá và ống nước có bị rò rỉ không", "Có thể gây hại cho hệ vi sinh.", "INCOMPLETE"),
    ("FISH_TANK_WATER_LEVEL_LOW", "Mực nước bể cá thấp / nguy cơ chạy khô bơm", "SENSOR", "DIGITAL_STATE", "EXTREME", {"active_state": "LOW", "active_value": None}, "Mực nước bể cá thấp, hãy kiểm tra các ống nước có bị rò rỉ nước không", "Có thể phá bơm + mất tuần hoàn, cá có thể chết.", "INCOMPLETE"),
    ("FISH_TANK_WATER_LEVEL_HIGH", "Mực nước bể cá quá cao / nguy cơ tràn", "SENSOR", "DIGITAL_STATE", "EXTREME", {"active_state": "HIGH", "active_value": None}, "Mực nước bể cá cao, nguy cơ cá nhảy ra ngoài", "Tràn nước, mất nước hệ thống, nguy hiểm điện.", "INCOMPLETE"),
    ("WATER_PH_OUT_OF_RANGE", "pH nước", "SENSOR", "RANGE_BANDS", "VERY_HIGH", {"unit": "pH", "bands": [{"severity": "WARNING", "lower": 6.0, "upper": 8.0, "outside": True}, {"severity": "CRITICAL", "lower": 5.5, "upper": 8.5, "outside": True}]}, "pH bất thường, hãy kiểm tra môi trường nước", "Ảnh hưởng cá + vi khuẩn nitrification + hấp thu dinh dưỡng.", "VALIDATED"),
    ("WATER_TEMPERATURE_HIGH", "Nhiệt độ nước", "SENSOR", "THRESHOLD_BANDS", "VERY_HIGH", {"unit": "°C", "bands": [{"severity": "WARNING", "operator": "GT", "value": None}, {"severity": "CRITICAL", "operator": "GT", "value": 32}]}, "Nhiệt độ nước bể cá cao, hãy che nắng cho bể cá", "DO giảm mạnh, cá stress, vi sinh bị ảnh hưởng.", "INCOMPLETE"),
    ("BIOFILTER_AERATOR_NO_FEEDBACK", "Bơm oxy bể lọc vi sinh mất hoạt động", "ACTUATOR", "ACTUATOR_FEEDBACK", "HIGH", {"expected_state": "ON", "feedback_role": "RUNNING_CURRENT", "min_running_current_a": None, "startup_grace_seconds": None, "debounce_seconds": None, "recovery_current_a": None, "recovery_duration_seconds": None}, "Máy sục oxy đang có vấn đề, hãy kiểm tra", "Biofilter thiếu oxy, nitrification suy giảm.", "INCOMPLETE"),
    ("MAIN_PUMP_FLOW_LOW", "Flow bơm chính giảm mạnh", "SENSOR", "BASELINE_DEVIATION", "HIGH", {"minimum_baseline_ratio": None, "baseline_policy": None}, None, "Có thể báo hiệu tắc lọc, tắc ống, bơm yếu.", "INCOMPLETE"),
    ("AMMONIA_ABNORMAL", "NH₃/NH₄⁺", "SENSOR", "TREND", "HIGH", {"threshold": None, "window_seconds": None, "trend_policy": None}, None, "Độc tính với cá, đặc biệt khi pH và nhiệt độ cao.", "INCOMPLETE"),
    ("NITRITE_HIGH", "NO₂⁻", "SENSOR", "THRESHOLD_BANDS", "HIGH", {"unit": "mg/L", "bands": [{"severity": "WARNING", "operator": "GT", "value": 0.5}, {"severity": "CRITICAL", "operator": "GT", "value": 1.0}]}, None, "Độc với cá, dấu hiệu biofilter có vấn đề.", "INCOMPLETE"),
    ("TDS_LOW", "TDS", "SENSOR", "THRESHOLD", "MEDIUM", {"unit": "ppm", "operator": "LT", "value": 100, "severity": "WARNING"}, "Nồng độ dinh dưỡng quá thấp", "Báo hiệu thay đổi hóa học, bay hơi hoặc bổ sung khoáng.", "VALIDATED"),
    ("AIR_TEMPERATURE_HIGH", "Nhiệt độ không khí", "SENSOR", "THRESHOLD", "MEDIUM", {"unit": "°C", "operator": "GT", "value": 35, "severity": "WARNING"}, "Nhiệt độ không khí cao, chú ý che nắng cho giàn", "Tăng nhiệt nước, stress cây/cá gián tiếp.", "VALIDATED"),
    ("AIR_HUMIDITY_HIGH", "Độ ẩm không khí", "SENSOR", "THRESHOLD_DURATION", "MEDIUM", {"unit": "%", "operator": "GT", "value": None, "duration_seconds": None}, "Độ ẩm không khí cao, nguy cơ nấm bệnh", "Tăng nguy cơ nấm bệnh, ngưng tụ.", "INCOMPLETE"),
    ("GROW_LIGHT_NO_CURRENT", "Đèn chiếu sáng cho cây", "ACTUATOR", "SCHEDULE_FEEDBACK", "LOW_MEDIUM", {"schedule_id": None, "feedback_role": "RUNNING_CURRENT", "min_running_current_a": None, "startup_grace_seconds": None, "debounce_seconds": None, "recovery_current_a": None, "recovery_duration_seconds": None}, "Đèn chiếu sáng đang có vấn đề, cần kiểm tra!", "Ảnh hưởng sinh trưởng cây, nhưng không nguy hiểm tức thời.", "INCOMPLETE"),
    ("ENVIRONMENT_LIGHT_LOW_LONG_TERM", "Cường độ ánh sáng môi trường", "SENSOR", "WINDOW_DURATION", "LOW", {"unit": "lux", "threshold": None, "number_of_days": None, "aggregation": None}, "Cường độ ánh sáng thấp trong nhiều ngày, nguy cơ rau kém phát triển", "Chủ yếu ảnh hưởng tốc độ sinh trưởng.", "INCOMPLETE"),
    ("TDS_LOW_LONG_TERM", "TDS/EC thay đổi chậm", "SENSOR", "WINDOW_DURATION", "LOW", {"unit": "ppm", "operator": "LT", "value": 150, "number_of_days": None, "aggregation": None}, "Nồng độ dinh dưỡng thấp trong nhiều ngày", "Cần theo dõi xu hướng hơn là báo động tức thời.", "INCOMPLETE"),
]


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    # The historical 0001 baseline imports current metadata. On a truly fresh
    # database it therefore materializes newly added models before this
    # reconciliation revision runs. Validate/complete that path instead of
    # trying to create the same tables twice.
    if inspector.has_table("alert_rules"):
        expected_tables = {
            "alert_rule_revisions", "alert_rule_profiles",
            "alert_rule_actuator_model_profiles", "alert_rule_sensor_model_profiles",
            "alert_rule_project_overrides", "alert_rule_actuator_overrides", "alert_rule_sensor_overrides",
            "actuator_feedback_bindings", "operational_incidents",
            "notification_outbox", "notification_deliveries",
        }
        missing_tables = sorted(table for table in expected_tables if not inspector.has_table(table))
        if missing_tables:
            raise RuntimeError(f"Partial operational alert schema found: {missing_tables}")
        checks = {
            "alert_rules": [("alert_rule_target_type_allowed", "target_type IN ('SENSOR','ACTUATOR')"), ("alert_rule_evaluator_type_allowed", "evaluator_type IN ('THRESHOLD','THRESHOLD_BANDS','RANGE_BANDS','DIGITAL_STATE','THRESHOLD_DURATION','ACTUATOR_FEEDBACK','SCHEDULE_FEEDBACK','BASELINE_DEVIATION','WINDOW_DURATION','TREND')")],
            "alert_rule_revisions": [("alert_revision_risk_allowed", "business_risk_level IN ('EXTREME','VERY_HIGH','HIGH','MEDIUM','LOW_MEDIUM','LOW')"), ("alert_revision_status_allowed", "status IN ('DRAFT','INCOMPLETE','VALIDATED','PUBLISHED','RETIRED')")],
            "actuator_feedback_bindings": [("actuator_feedback_role_allowed", "feedback_role IN ('RUNNING_CURRENT')")],
            "operational_incidents": [("operational_incident_status_allowed", "status IN ('PENDING','OPEN','ACKNOWLEDGED','NORMALIZED','RESOLVED')"), ("operational_incident_severity_allowed", "technical_severity IN ('WARNING','CRITICAL')")],
            "project_notification_settings": [("reminder_positive", "reminder_interval_minutes IS NULL OR reminder_interval_minutes > 0"), ("risk_allowed", "minimum_business_risk_level IN ('EXTREME','VERY_HIGH','HIGH','MEDIUM','LOW_MEDIUM','LOW')")],
        }
        for table_name, definitions in checks.items():
            existing_checks = {item["name"] for item in inspector.get_check_constraints(table_name)}
            for constraint_name, condition in definitions:
                full_name = f"ck_{table_name}_{constraint_name}"
                present = any(
                    existing_name in {constraint_name, full_name}
                    or full_name.startswith(existing_name.rsplit("_", 1)[0])
                    for existing_name in existing_checks
                    if existing_name
                )
                if not present:
                    op.create_check_constraint(constraint_name, table_name, condition)
        indexes = {
            "alert_rule_revisions": [("ix_alert_rule_revisions_rule_id", ["rule_id"], False)],
            "alert_rule_profiles": [("ix_alert_rule_profiles_rule_id", ["rule_id"], False)],
            "actuator_feedback_bindings": [("ix_actuator_feedback_bindings_actuator_id", ["actuator_id"], False), ("ix_actuator_feedback_bindings_sensor_id", ["sensor_id"], False)],
            "operational_incidents": [("ix_operational_incidents_project_status", ["project_id", "status"], False), ("ix_operational_incidents_rule_status", ["rule_id", "status"], False), ("uq_active_operational_incident", ["rule_id", "context_key"], True)],
            "notification_outbox": [("ix_notification_outbox_status_available", ["status", "available_at"], False)],
            "notification_deliveries": [("ix_notification_deliveries_outbox_status", ["outbox_id", "status"], False)],
        }
        for table_name, definitions in indexes.items():
            existing_indexes = {item["name"] for item in inspector.get_indexes(table_name)}
            for index_name, columns, unique in definitions:
                if index_name not in existing_indexes:
                    kwargs = {"postgresql_where": sa.text("status IN ('PENDING','OPEN','ACKNOWLEDGED','NORMALIZED')")} if index_name == "uq_active_operational_incident" else {}
                    op.create_index(index_name, table_name, columns, unique=unique, **kwargs)
        _seed_rules(op.get_bind())
        return
    op.create_table(
        "alert_rules",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=True), primary_key=True),
        sa.Column("code", sa.String(100), nullable=False, unique=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("target_type", sa.String(30), nullable=False),
        sa.Column("evaluator_type", sa.String(50), nullable=False),
        sa.Column("is_enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("current_revision_id", sa.BigInteger(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("target_type IN ('SENSOR','ACTUATOR')", name="alert_rule_target_type_allowed"),
        sa.CheckConstraint("evaluator_type IN ('THRESHOLD','THRESHOLD_BANDS','RANGE_BANDS','DIGITAL_STATE','THRESHOLD_DURATION','ACTUATOR_FEEDBACK','SCHEDULE_FEEDBACK','BASELINE_DEVIATION','WINDOW_DURATION','TREND')", name="alert_rule_evaluator_type_allowed"),
    )
    op.create_table(
        "alert_rule_revisions",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=True), primary_key=True),
        sa.Column("rule_id", sa.BigInteger(), sa.ForeignKey("alert_rules.id", ondelete="CASCADE"), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("business_risk_level", sa.String(30), nullable=False),
        sa.Column("condition_schema_version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("condition_config", postgresql.JSONB(), nullable=False),
        sa.Column("message_template", sa.Text(), nullable=True),
        sa.Column("consequence", sa.Text(), nullable=True),
        sa.Column("recommended_action", sa.Text(), nullable=True),
        sa.Column("source_reference", sa.String(255), nullable=False, server_default="Business rules 2026-08-24"),
        sa.Column("source_order", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("created_by", sa.BigInteger(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("published_by", sa.BigInteger(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("rule_id", "revision", name="uq_alert_rule_revision"),
        sa.CheckConstraint("business_risk_level IN ('EXTREME','VERY_HIGH','HIGH','MEDIUM','LOW_MEDIUM','LOW')", name="alert_revision_risk_allowed"),
        sa.CheckConstraint("status IN ('DRAFT','INCOMPLETE','VALIDATED','PUBLISHED','RETIRED')", name="alert_revision_status_allowed"),
    )
    op.create_index("ix_alert_rule_revisions_rule_id", "alert_rule_revisions", ["rule_id"])
    op.create_foreign_key("fk_alert_rules_current_revision_id_alert_rule_revisions", "alert_rules", "alert_rule_revisions", ["current_revision_id"], ["id"], ondelete="SET NULL")
    op.create_table(
        "alert_rule_profiles",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=True), primary_key=True),
        sa.Column("rule_id", sa.BigInteger(), sa.ForeignKey("alert_rules.id", ondelete="CASCADE"), nullable=False),
        sa.Column("code", sa.String(100), nullable=False, unique=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("config", postgresql.JSONB(), nullable=False),
        sa.Column("is_enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_alert_rule_profiles_rule_id", "alert_rule_profiles", ["rule_id"])
    for table, model_table in (("alert_rule_actuator_model_profiles", "actuator_models"), ("alert_rule_sensor_model_profiles", "sensor_models")):
        model_column = "actuator_model_id" if "actuator" in table else "sensor_model_id"
        op.create_table(table, sa.Column("profile_id", sa.BigInteger(), sa.ForeignKey("alert_rule_profiles.id", ondelete="CASCADE"), primary_key=True), sa.Column(model_column, sa.BigInteger(), sa.ForeignKey(f"{model_table}.id", ondelete="CASCADE"), primary_key=True))
    for table_name, scope_table, scope_column in (
        ("alert_rule_project_overrides", "projects", "project_id"),
        ("alert_rule_actuator_overrides", "actuators", "actuator_id"),
        ("alert_rule_sensor_overrides", "sensors", "sensor_id"),
    ):
        op.create_table(
            table_name,
            sa.Column("id", sa.BigInteger(), sa.Identity(always=True), primary_key=True),
            sa.Column("rule_id", sa.BigInteger(), sa.ForeignKey("alert_rules.id", ondelete="CASCADE"), nullable=False),
            sa.Column(scope_column, sa.BigInteger(), sa.ForeignKey(f"{scope_table}.id", ondelete="CASCADE"), nullable=False),
            sa.Column("config", postgresql.JSONB(), nullable=False),
            sa.Column("is_enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.UniqueConstraint("rule_id", scope_column, name=f"uq_{table_name}_rule_scope"),
        )
        op.create_index(f"ix_{table_name}_{scope_column}", table_name, [scope_column])
    op.create_table(
        "actuator_feedback_bindings",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=True), primary_key=True),
        sa.Column("actuator_id", sa.BigInteger(), sa.ForeignKey("actuators.id", ondelete="CASCADE"), nullable=False),
        sa.Column("sensor_id", sa.BigInteger(), sa.ForeignKey("sensors.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("feedback_role", sa.String(40), nullable=False),
        sa.Column("is_enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_by", sa.BigInteger(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("updated_by", sa.BigInteger(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("actuator_id", "feedback_role", name="uq_actuator_feedback_role"),
        sa.CheckConstraint("feedback_role IN ('RUNNING_CURRENT')", name="actuator_feedback_role_allowed"),
    )
    op.create_index("ix_actuator_feedback_bindings_actuator_id", "actuator_feedback_bindings", ["actuator_id"])
    op.create_index("ix_actuator_feedback_bindings_sensor_id", "actuator_feedback_bindings", ["sensor_id"])
    op.create_table(
        "operational_incidents",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=True), primary_key=True),
        sa.Column("project_id", sa.BigInteger(), sa.ForeignKey("projects.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("rule_id", sa.BigInteger(), sa.ForeignKey("alert_rules.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("rule_revision_id", sa.BigInteger(), sa.ForeignKey("alert_rule_revisions.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("device_id", sa.BigInteger(), sa.ForeignKey("devices.id", ondelete="RESTRICT"), nullable=True),
        sa.Column("sensor_id", sa.BigInteger(), sa.ForeignKey("sensors.id", ondelete="RESTRICT"), nullable=True),
        sa.Column("actuator_id", sa.BigInteger(), sa.ForeignKey("actuators.id", ondelete="RESTRICT"), nullable=True),
        sa.Column("context_key", sa.String(160), nullable=False),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("technical_severity", sa.String(30), nullable=False),
        sa.Column("business_risk_level_snapshot", sa.String(30), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("opened_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("acknowledged_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("normalized_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_triggered_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("occurrence_count", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("trigger_snapshot", postgresql.JSONB(), nullable=False),
        sa.Column("acknowledged_by", sa.BigInteger(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("resolved_by", sa.BigInteger(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("resolution_note", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("status IN ('PENDING','OPEN','ACKNOWLEDGED','NORMALIZED','RESOLVED')", name="operational_incident_status_allowed"),
        sa.CheckConstraint("technical_severity IN ('WARNING','CRITICAL')", name="operational_incident_severity_allowed"),
    )
    op.create_index("ix_operational_incidents_project_status", "operational_incidents", ["project_id", "status"])
    op.create_index("ix_operational_incidents_rule_status", "operational_incidents", ["rule_id", "status"])
    op.create_index("uq_active_operational_incident", "operational_incidents", ["rule_id", "context_key"], unique=True, postgresql_where=sa.text("status IN ('PENDING','OPEN','ACKNOWLEDGED','NORMALIZED')"))
    op.create_table(
        "notification_outbox",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=True), primary_key=True),
        sa.Column("incident_id", sa.BigInteger(), sa.ForeignKey("operational_incidents.id", ondelete="CASCADE"), nullable=False),
        sa.Column("event_type", sa.String(30), nullable=False),
        sa.Column("idempotency_key", sa.String(200), nullable=False, unique=True),
        sa.Column("payload_snapshot", postgresql.JSONB(), nullable=False),
        sa.Column("status", sa.String(30), nullable=False, server_default="PENDING"),
        sa.Column("available_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("attempt_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_attempt_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_notification_outbox_status_available", "notification_outbox", ["status", "available_at"])
    op.create_table(
        "notification_deliveries",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=True), primary_key=True),
        sa.Column("outbox_id", sa.BigInteger(), sa.ForeignKey("notification_outbox.id", ondelete="CASCADE"), nullable=False),
        sa.Column("incident_id", sa.BigInteger(), sa.ForeignKey("operational_incidents.id", ondelete="CASCADE"), nullable=False),
        sa.Column("channel", sa.String(30), nullable=False),
        sa.Column("recipient_id", sa.BigInteger(), sa.ForeignKey("project_notification_recipients.id", ondelete="SET NULL"), nullable=True),
        sa.Column("recipient_reference", sa.String(120), nullable=False),
        sa.Column("idempotency_key", sa.String(240), nullable=False, unique=True),
        sa.Column("status", sa.String(30), nullable=False, server_default="PENDING"),
        sa.Column("attempt_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_attempt_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("next_retry_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("failed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_category", sa.String(60), nullable=True),
        sa.Column("provider_message_id", sa.String(120), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_notification_deliveries_outbox_status", "notification_deliveries", ["outbox_id", "status"])
    for name, column in (
        ("notify_alert_escalated", sa.Column("notify_alert_escalated", sa.Boolean(), nullable=False, server_default=sa.true())),
        ("notify_alert_reminder", sa.Column("notify_alert_reminder", sa.Boolean(), nullable=False, server_default=sa.false())),
        ("reminder_interval_minutes", sa.Column("reminder_interval_minutes", sa.Integer(), nullable=True)),
        ("minimum_business_risk_level", sa.Column("minimum_business_risk_level", sa.String(30), nullable=False, server_default="LOW")),
    ):
        op.add_column("project_notification_settings", column)
    op.create_check_constraint("reminder_positive", "project_notification_settings", "reminder_interval_minutes IS NULL OR reminder_interval_minutes > 0")
    op.create_check_constraint("risk_allowed", "project_notification_settings", "minimum_business_risk_level IN ('EXTREME','VERY_HIGH','HIGH','MEDIUM','LOW_MEDIUM','LOW')")

    _seed_rules(op.get_bind())


def _seed_rules(connection) -> None:
    for order, (code, name, target, evaluator, risk, config, message, consequence, status) in enumerate(RULES, 1):
        if connection.execute(sa.text("SELECT 1 FROM alert_rules WHERE code=:code"), {"code": code}).scalar_one_or_none():
            continue
        rule_id = connection.execute(sa.text("INSERT INTO alert_rules (code,name,target_type,evaluator_type,is_enabled) VALUES (:code,:name,:target,:evaluator,true) RETURNING id"), {"code": code, "name": name, "target": target, "evaluator": evaluator}).scalar_one()
        revision_id = connection.execute(sa.text("INSERT INTO alert_rule_revisions (rule_id,revision,business_risk_level,condition_schema_version,condition_config,message_template,consequence,source_reference,source_order,status) VALUES (:rule_id,1,:risk,1,CAST(:config AS jsonb),:message,:consequence,'Business rules 2026-08-24',:source_order,:status) RETURNING id"), {"rule_id": rule_id, "risk": risk, "config": json.dumps(config), "message": message, "consequence": consequence, "source_order": order, "status": status}).scalar_one()
        connection.execute(sa.text("UPDATE alert_rules SET current_revision_id=:revision_id WHERE id=:rule_id"), {"revision_id": revision_id, "rule_id": rule_id})


def downgrade() -> None:
    raise RuntimeError("0027 contains business rule history; restore from backup instead of downgrading destructively")
