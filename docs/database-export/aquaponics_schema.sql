-- Aquaponics Platform: PostgreSQL schema-only export
-- Source: SQLAlchemy metadata; repository Alembic head: 0035
-- Empty database only. No data, catalog seeds, roles, extensions or Alembic stamp.
-- Python defaults/onupdate are not database defaults/triggers.

BEGIN;

CREATE TYPE alert_type AS ENUM ('BELOW_LOWER_THRESHOLD', 'ABOVE_UPPER_THRESHOLD', 'SENSOR_OFFLINE');

CREATE TYPE alert_severity AS ENUM ('WARNING', 'CRITICAL');

CREATE TYPE alert_status AS ENUM ('PENDING', 'OPEN', 'ACKNOWLEDGED', 'RESOLVED');

CREATE TYPE device_status AS ENUM ('WAITING_CONNECTION', 'ONLINE', 'OFFLINE', 'DISABLED');

CREATE TYPE project_status AS ENUM ('ACTIVE', 'INACTIVE', 'ARCHIVED', 'DISABLED');

CREATE TYPE sensor_purpose AS ENUM ('GENERAL', 'ACTUATOR_FEEDBACK');

CREATE TYPE sensor_status AS ENUM ('WAITING_CONNECTION', 'ONLINE', 'OFFLINE', 'DISABLED');

CREATE TYPE aggregate_period AS ENUM ('HOUR', 'DAY');

CREATE TYPE user_system_role AS ENUM ('ADMIN', 'OWNER', 'VIEWER');

CREATE TYPE user_status AS ENUM ('ACTIVE', 'DISABLED', 'LOCKED', 'SOFT_DELETED');

CREATE TABLE device_templates (
	id BIGINT GENERATED ALWAYS AS IDENTITY, 
	code VARCHAR(80) NOT NULL, 
	name VARCHAR(255) NOT NULL, 
	description TEXT, 
	notes TEXT, 
	device_kind VARCHAR(40) DEFAULT 'GENERIC' NOT NULL, 
	nominal_output_voltage_v FLOAT, 
	is_active BOOLEAN NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	is_deleted BOOLEAN NOT NULL, 
	deleted_at TIMESTAMP WITH TIME ZONE, 
	CONSTRAINT pk_device_templates PRIMARY KEY (id), 
	CONSTRAINT uq_device_templates_code UNIQUE (code), 
	CONSTRAINT ck_device_templates_nominal_voltage_positive CHECK (nominal_output_voltage_v IS NULL OR nominal_output_voltage_v > 0), 
	CONSTRAINT ck_device_templates_device_kind_allowed CHECK (device_kind IN ('GENERIC', 'ENERGY_MONITOR'))
);

CREATE INDEX ix_device_templates_is_deleted ON device_templates (is_deleted);

CREATE INDEX ix_device_templates_code ON device_templates (code);

CREATE TABLE sensor_models (
	id BIGINT GENERATED ALWAYS AS IDENTITY, 
	code VARCHAR(80) NOT NULL, 
	name VARCHAR(255) NOT NULL, 
	unit VARCHAR(50) NOT NULL, 
	value_type VARCHAR(30) NOT NULL, 
	chart_type VARCHAR(30) NOT NULL, 
	measurement_semantics VARCHAR(20) DEFAULT 'GAUGE' NOT NULL, 
	description TEXT, 
	default_lower_threshold FLOAT, 
	default_upper_threshold FLOAT, 
	default_warning_enabled BOOLEAN NOT NULL, 
	default_below_threshold_message TEXT, 
	default_above_threshold_message TEXT, 
	default_alert_risk_level VARCHAR(30), 
	is_visible BOOLEAN NOT NULL, 
	is_active BOOLEAN NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	is_deleted BOOLEAN NOT NULL, 
	deleted_at TIMESTAMP WITH TIME ZONE, 
	CONSTRAINT pk_sensor_models PRIMARY KEY (id), 
	CONSTRAINT ck_sensor_models_default_threshold_order CHECK (default_lower_threshold IS NULL OR default_upper_threshold IS NULL OR default_lower_threshold < default_upper_threshold), 
	CONSTRAINT ck_sensor_models_measurement_semantics_allowed CHECK (measurement_semantics IN ('GAUGE', 'COUNTER'))
);

CREATE UNIQUE INDEX ix_sensor_models_code ON sensor_models (code);

CREATE INDEX ix_sensor_models_is_deleted ON sensor_models (is_deleted);

CREATE TABLE actuator_models (
	id BIGINT GENERATED ALWAYS AS IDENTITY, 
	code VARCHAR(80) NOT NULL, 
	name VARCHAR(255) NOT NULL, 
	description TEXT, 
	data_type VARCHAR(30) NOT NULL, 
	default_state BOOLEAN NOT NULL, 
	is_active BOOLEAN NOT NULL, 
	sort_order INTEGER NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	is_deleted BOOLEAN NOT NULL, 
	deleted_at TIMESTAMP WITH TIME ZONE, 
	CONSTRAINT pk_actuator_models PRIMARY KEY (id), 
	CONSTRAINT uq_actuator_models_code UNIQUE (code)
);

CREATE INDEX ix_actuator_models_is_deleted ON actuator_models (is_deleted);

CREATE TABLE users (
	id BIGINT GENERATED ALWAYS AS IDENTITY, 
	username VARCHAR(100) NOT NULL, 
	password_hash VARCHAR(255) NOT NULL, 
	full_name VARCHAR(255) NOT NULL, 
	email VARCHAR(255) NOT NULL, 
	phone_number VARCHAR(30) NOT NULL, 
	address TEXT NOT NULL, 
	system_role user_system_role NOT NULL, 
	status user_status NOT NULL, 
	must_change_password BOOLEAN NOT NULL, 
	token_version INTEGER NOT NULL, 
	disabled_at TIMESTAMP WITH TIME ZONE, 
	disabled_by_user_id BIGINT, 
	disabled_reason TEXT, 
	locked_at TIMESTAMP WITH TIME ZONE, 
	locked_by_user_id BIGINT, 
	locked_reason TEXT, 
	last_login_at TIMESTAMP WITH TIME ZONE, 
	password_changed_at TIMESTAMP WITH TIME ZONE, 
	created_by BIGINT, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	is_deleted BOOLEAN NOT NULL, 
	deleted_at TIMESTAMP WITH TIME ZONE, 
	CONSTRAINT pk_users PRIMARY KEY (id), 
	CONSTRAINT fk_users_disabled_by_user_id_users FOREIGN KEY(disabled_by_user_id) REFERENCES users (id) ON DELETE SET NULL, 
	CONSTRAINT fk_users_locked_by_user_id_users FOREIGN KEY(locked_by_user_id) REFERENCES users (id) ON DELETE SET NULL, 
	CONSTRAINT fk_users_created_by_users FOREIGN KEY(created_by) REFERENCES users (id) ON DELETE SET NULL
);

CREATE UNIQUE INDEX ix_users_email ON users (email);

CREATE UNIQUE INDEX ix_users_phone_number ON users (phone_number);

CREATE UNIQUE INDEX ix_users_username ON users (username);

CREATE INDEX ix_users_is_deleted ON users (is_deleted);

CREATE TABLE alert_rules (
	id BIGINT GENERATED ALWAYS AS IDENTITY, 
	code VARCHAR(100) NOT NULL, 
	name VARCHAR(255) NOT NULL, 
	target_type VARCHAR(30) NOT NULL, 
	evaluator_type VARCHAR(50) NOT NULL, 
	is_enabled BOOLEAN DEFAULT true NOT NULL, 
	current_revision_id BIGINT, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	CONSTRAINT pk_alert_rules PRIMARY KEY (id), 
	CONSTRAINT ck_alert_rules_alert_rule_target_type_allowed CHECK (target_type IN ('SENSOR','ACTUATOR')), 
	CONSTRAINT ck_alert_rules_alert_rule_evaluator_type_allowed CHECK (evaluator_type IN ('THRESHOLD','THRESHOLD_BANDS','RANGE_BANDS','DIGITAL_STATE','THRESHOLD_DURATION','ACTUATOR_FEEDBACK','SCHEDULE_FEEDBACK','BASELINE_DEVIATION','WINDOW_DURATION','TREND')), 
	CONSTRAINT uq_alert_rules_code UNIQUE (code)
);

CREATE TABLE device_template_sensors (
	id BIGINT GENERATED ALWAYS AS IDENTITY, 
	device_template_id BIGINT NOT NULL, 
	sensor_model_id BIGINT NOT NULL, 
	display_name VARCHAR(255), 
	default_location VARCHAR(255), 
	default_lower_threshold FLOAT, 
	default_upper_threshold FLOAT, 
	default_warning_enabled BOOLEAN, 
	default_below_threshold_message TEXT, 
	default_above_threshold_message TEXT, 
	default_alert_risk_level VARCHAR(30), 
	sort_order INTEGER NOT NULL, 
	is_required BOOLEAN DEFAULT 'false' NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	CONSTRAINT pk_device_template_sensors PRIMARY KEY (id), 
	CONSTRAINT uq_device_template_sensor_model UNIQUE (device_template_id, sensor_model_id), 
	CONSTRAINT fk_device_template_sensors_device_template_id_device_templates FOREIGN KEY(device_template_id) REFERENCES device_templates (id) ON DELETE CASCADE, 
	CONSTRAINT fk_device_template_sensors_sensor_model_id_sensor_models FOREIGN KEY(sensor_model_id) REFERENCES sensor_models (id) ON DELETE RESTRICT
);

CREATE INDEX ix_device_template_sensors_device_template_id ON device_template_sensors (device_template_id);

CREATE INDEX ix_device_template_sensors_sensor_model_id ON device_template_sensors (sensor_model_id);

CREATE TABLE projects (
	id BIGINT GENERATED ALWAYS AS IDENTITY, 
	owner_user_id BIGINT NOT NULL, 
	code VARCHAR(80) NOT NULL, 
	name VARCHAR(255) NOT NULL, 
	location VARCHAR(255), 
	description TEXT, 
	status project_status NOT NULL, 
	disabled_at TIMESTAMP WITH TIME ZONE, 
	disabled_by_user_id BIGINT, 
	disabled_reason TEXT, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	is_deleted BOOLEAN NOT NULL, 
	deleted_at TIMESTAMP WITH TIME ZONE, 
	CONSTRAINT pk_projects PRIMARY KEY (id), 
	CONSTRAINT fk_projects_owner_user_id_users FOREIGN KEY(owner_user_id) REFERENCES users (id) ON DELETE RESTRICT, 
	CONSTRAINT fk_projects_disabled_by_user_id_users FOREIGN KEY(disabled_by_user_id) REFERENCES users (id) ON DELETE SET NULL
);

CREATE INDEX ix_projects_status ON projects (status);

CREATE INDEX ix_projects_is_deleted ON projects (is_deleted);

CREATE INDEX ix_projects_owner_user_id ON projects (owner_user_id);

CREATE INDEX ix_projects_disabled_by_user_id ON projects (disabled_by_user_id);

CREATE UNIQUE INDEX ix_projects_code ON projects (code);

CREATE TABLE actuator_model_feedback_definitions (
	id BIGINT GENERATED ALWAYS AS IDENTITY, 
	actuator_model_id BIGINT NOT NULL, 
	feedback_role VARCHAR(40) NOT NULL, 
	sensor_model_id BIGINT NOT NULL, 
	value_key VARCHAR(80) NOT NULL, 
	unit VARCHAR(50) NOT NULL, 
	data_type VARCHAR(30) NOT NULL, 
	default_lower_threshold FLOAT, 
	default_upper_threshold FLOAT, 
	is_required BOOLEAN DEFAULT true NOT NULL, 
	is_enabled BOOLEAN DEFAULT true NOT NULL, 
	display_order INTEGER DEFAULT '0' NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	CONSTRAINT pk_actuator_model_feedback_definitions PRIMARY KEY (id), 
	CONSTRAINT uq_actuator_model_feedback_role UNIQUE (actuator_model_id, feedback_role), 
	CONSTRAINT ck_actuator_model_feedback_definitions_role_allowed CHECK (feedback_role IN ('SUPPLY_VOLTAGE','RUNNING_CURRENT')), 
	CONSTRAINT ck_actuator_model_feedback_definitions_data_type_allowed CHECK (data_type IN ('FLOAT')), 
	CONSTRAINT ck_actuator_model_feedback_definitions_order_nonnegative CHECK (display_order >= 0), 
	CONSTRAINT ck_actuator_model_feedback_definitions_threshold_order CHECK (default_lower_threshold IS NULL OR default_upper_threshold IS NULL OR default_lower_threshold < default_upper_threshold), 
	CONSTRAINT fk_actuator_model_feedback_definitions_actuator_model_i_83b6 FOREIGN KEY(actuator_model_id) REFERENCES actuator_models (id) ON DELETE CASCADE, 
	CONSTRAINT fk_actuator_model_feedback_definitions_sensor_model_id__8258 FOREIGN KEY(sensor_model_id) REFERENCES sensor_models (id) ON DELETE RESTRICT
);

CREATE INDEX ix_actuator_model_feedback_definitions_actuator_model_id ON actuator_model_feedback_definitions (actuator_model_id);

CREATE INDEX ix_actuator_model_feedback_definitions_sensor_model_id ON actuator_model_feedback_definitions (sensor_model_id);

CREATE TABLE alert_rule_revisions (
	id BIGINT GENERATED ALWAYS AS IDENTITY, 
	rule_id BIGINT NOT NULL, 
	revision INTEGER NOT NULL, 
	business_risk_level VARCHAR(30) NOT NULL, 
	condition_schema_version INTEGER DEFAULT '1' NOT NULL, 
	condition_config JSONB NOT NULL, 
	message_template TEXT, 
	consequence TEXT, 
	recommended_action TEXT, 
	source_reference VARCHAR(255) DEFAULT 'Business rules 2026-08-24' NOT NULL, 
	source_order INTEGER NOT NULL, 
	status VARCHAR(30) NOT NULL, 
	created_by BIGINT, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	published_by BIGINT, 
	published_at TIMESTAMP WITH TIME ZONE, 
	CONSTRAINT pk_alert_rule_revisions PRIMARY KEY (id), 
	CONSTRAINT uq_alert_rule_revision UNIQUE (rule_id, revision), 
	CONSTRAINT ck_alert_rule_revisions_alert_revision_risk_allowed CHECK (business_risk_level IN ('EXTREME','VERY_HIGH','HIGH','MEDIUM','LOW_MEDIUM','LOW')), 
	CONSTRAINT ck_alert_rule_revisions_alert_revision_status_allowed CHECK (status IN ('DRAFT','INCOMPLETE','VALIDATED','PUBLISHED','RETIRED')), 
	CONSTRAINT fk_alert_rule_revisions_rule_id_alert_rules FOREIGN KEY(rule_id) REFERENCES alert_rules (id) ON DELETE CASCADE, 
	CONSTRAINT fk_alert_rule_revisions_created_by_users FOREIGN KEY(created_by) REFERENCES users (id) ON DELETE SET NULL, 
	CONSTRAINT fk_alert_rule_revisions_published_by_users FOREIGN KEY(published_by) REFERENCES users (id) ON DELETE SET NULL
);

CREATE INDEX ix_alert_rule_revisions_rule_id ON alert_rule_revisions (rule_id);

CREATE TABLE alert_rule_profiles (
	id BIGINT GENERATED ALWAYS AS IDENTITY, 
	rule_id BIGINT NOT NULL, 
	code VARCHAR(100) NOT NULL, 
	name VARCHAR(255) NOT NULL, 
	config JSONB NOT NULL, 
	is_enabled BOOLEAN DEFAULT true NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	CONSTRAINT pk_alert_rule_profiles PRIMARY KEY (id), 
	CONSTRAINT fk_alert_rule_profiles_rule_id_alert_rules FOREIGN KEY(rule_id) REFERENCES alert_rules (id) ON DELETE CASCADE, 
	CONSTRAINT uq_alert_rule_profiles_code UNIQUE (code)
);

CREATE INDEX ix_alert_rule_profiles_rule_id ON alert_rule_profiles (rule_id);

CREATE TABLE alert_rule_actuator_models (
	rule_id BIGINT NOT NULL, 
	actuator_model_id BIGINT NOT NULL, 
	CONSTRAINT pk_alert_rule_actuator_models PRIMARY KEY (rule_id, actuator_model_id), 
	CONSTRAINT fk_alert_rule_actuator_models_rule_id_alert_rules FOREIGN KEY(rule_id) REFERENCES alert_rules (id) ON DELETE CASCADE, 
	CONSTRAINT fk_alert_rule_actuator_models_actuator_model_id_actuator_models FOREIGN KEY(actuator_model_id) REFERENCES actuator_models (id) ON DELETE CASCADE
);

CREATE INDEX ix_alert_rule_actuator_models_actuator_model_id ON alert_rule_actuator_models (actuator_model_id);

CREATE TABLE alert_rule_sensor_models (
	rule_id BIGINT NOT NULL, 
	sensor_model_id BIGINT NOT NULL, 
	CONSTRAINT pk_alert_rule_sensor_models PRIMARY KEY (rule_id, sensor_model_id), 
	CONSTRAINT fk_alert_rule_sensor_models_rule_id_alert_rules FOREIGN KEY(rule_id) REFERENCES alert_rules (id) ON DELETE CASCADE, 
	CONSTRAINT fk_alert_rule_sensor_models_sensor_model_id_sensor_models FOREIGN KEY(sensor_model_id) REFERENCES sensor_models (id) ON DELETE CASCADE
);

CREATE INDEX ix_alert_rule_sensor_models_sensor_model_id ON alert_rule_sensor_models (sensor_model_id);

CREATE TABLE audit_logs (
	id BIGINT GENERATED ALWAYS AS IDENTITY, 
	user_id BIGINT NOT NULL, 
	project_id BIGINT, 
	action VARCHAR(120) NOT NULL, 
	entity_type VARCHAR(120) NOT NULL, 
	entity_id BIGINT, 
	description TEXT, 
	old_data JSONB, 
	new_data JSONB, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	CONSTRAINT pk_audit_logs PRIMARY KEY (id), 
	CONSTRAINT fk_audit_logs_user_id_users FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE RESTRICT, 
	CONSTRAINT fk_audit_logs_project_id_projects FOREIGN KEY(project_id) REFERENCES projects (id) ON DELETE CASCADE
);

CREATE INDEX ix_audit_logs_created_at ON audit_logs (created_at);

CREATE INDEX ix_audit_logs_project_id_created_at ON audit_logs (project_id, created_at);

CREATE TABLE devices (
	id BIGINT GENERATED ALWAYS AS IDENTITY, 
	project_id BIGINT NOT NULL, 
	device_template_id BIGINT, 
	code VARCHAR(80) NOT NULL, 
	name VARCHAR(255) NOT NULL, 
	description TEXT, 
	location VARCHAR(255), 
	status device_status NOT NULL, 
	last_seen_at TIMESTAMP WITH TIME ZONE, 
	disconnected_at TIMESTAMP WITH TIME ZONE, 
	is_enabled BOOLEAN NOT NULL, 
	disabled_at TIMESTAMP WITH TIME ZONE, 
	disabled_by_user_id BIGINT, 
	disabled_reason TEXT, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	is_deleted BOOLEAN NOT NULL, 
	deleted_at TIMESTAMP WITH TIME ZONE, 
	CONSTRAINT pk_devices PRIMARY KEY (id), 
	CONSTRAINT fk_devices_project_id_projects FOREIGN KEY(project_id) REFERENCES projects (id) ON DELETE RESTRICT, 
	CONSTRAINT fk_devices_device_template_id_device_templates FOREIGN KEY(device_template_id) REFERENCES device_templates (id) ON DELETE SET NULL, 
	CONSTRAINT fk_devices_disabled_by_user_id_users FOREIGN KEY(disabled_by_user_id) REFERENCES users (id) ON DELETE SET NULL
);

CREATE INDEX ix_devices_project_id ON devices (project_id);

CREATE UNIQUE INDEX ix_devices_code ON devices (code);

CREATE INDEX ix_devices_device_template_id ON devices (device_template_id);

CREATE INDEX ix_devices_is_deleted ON devices (is_deleted);

CREATE TABLE device_template_actuators (
	id BIGINT GENERATED ALWAYS AS IDENTITY, 
	device_template_id BIGINT NOT NULL, 
	actuator_model_id BIGINT NOT NULL, 
	code VARCHAR(80) NOT NULL, 
	default_name VARCHAR(255), 
	default_location VARCHAR(255), 
	default_notes TEXT, 
	actuator_type VARCHAR(40) DEFAULT 'SWITCH' NOT NULL, 
	default_state BOOLEAN, 
	command_capability VARCHAR(30) DEFAULT 'ON_OFF' NOT NULL, 
	monitor_current BOOLEAN DEFAULT false NOT NULL, 
	electrical_profile_id BIGINT, 
	sort_order INTEGER NOT NULL, 
	is_required BOOLEAN NOT NULL, 
	is_enabled BOOLEAN DEFAULT true NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	CONSTRAINT pk_device_template_actuators PRIMARY KEY (id), 
	CONSTRAINT uq_device_template_actuator_code UNIQUE (device_template_id, code), 
	CONSTRAINT fk_device_template_actuators_device_template_id_device__ba20 FOREIGN KEY(device_template_id) REFERENCES device_templates (id) ON DELETE CASCADE, 
	CONSTRAINT fk_device_template_actuators_actuator_model_id_actuator_models FOREIGN KEY(actuator_model_id) REFERENCES actuator_models (id) ON DELETE RESTRICT, 
	CONSTRAINT fk_device_template_actuators_electrical_profile_id_aler_c662 FOREIGN KEY(electrical_profile_id) REFERENCES alert_rule_profiles (id) ON DELETE RESTRICT
);

CREATE INDEX ix_device_template_actuators_electrical_profile_id ON device_template_actuators (electrical_profile_id);

CREATE INDEX ix_device_template_actuators_actuator_model_id ON device_template_actuators (actuator_model_id);

CREATE INDEX ix_device_template_actuators_template_id ON device_template_actuators (device_template_id);

CREATE TABLE project_members (
	id BIGINT GENERATED ALWAYS AS IDENTITY, 
	project_id BIGINT NOT NULL, 
	user_id BIGINT NOT NULL, 
	role VARCHAR(20) DEFAULT 'VIEWER' NOT NULL, 
	created_by BIGINT, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	CONSTRAINT pk_project_members PRIMARY KEY (id), 
	CONSTRAINT uq_project_members_project_user UNIQUE (project_id, user_id), 
	CONSTRAINT fk_project_members_project_id_projects FOREIGN KEY(project_id) REFERENCES projects (id) ON DELETE CASCADE, 
	CONSTRAINT fk_project_members_user_id_users FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE, 
	CONSTRAINT fk_project_members_created_by_users FOREIGN KEY(created_by) REFERENCES users (id) ON DELETE SET NULL
);

CREATE INDEX ix_project_members_project_id ON project_members (project_id);

CREATE INDEX ix_project_members_user_id ON project_members (user_id);

CREATE TABLE scada_dashboards (
	id BIGINT GENERATED ALWAYS AS IDENTITY, 
	project_id BIGINT NOT NULL, 
	status VARCHAR(20) NOT NULL, 
	version INTEGER NOT NULL, 
	schema_version INTEGER NOT NULL, 
	layout JSONB NOT NULL, 
	created_by_user_id BIGINT NOT NULL, 
	published_at TIMESTAMP WITH TIME ZONE, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	CONSTRAINT pk_scada_dashboards PRIMARY KEY (id), 
	CONSTRAINT ck_scada_dashboards_status_allowed CHECK (status IN ('DRAFT', 'PUBLISHED')), 
	CONSTRAINT fk_scada_dashboards_project_id_projects FOREIGN KEY(project_id) REFERENCES projects (id) ON DELETE CASCADE, 
	CONSTRAINT fk_scada_dashboards_created_by_user_id_users FOREIGN KEY(created_by_user_id) REFERENCES users (id) ON DELETE RESTRICT
);

CREATE INDEX ix_scada_dashboards_project_status_version ON scada_dashboards (project_id, status, version);

CREATE TABLE project_public_settings (
	id BIGINT GENERATED ALWAYS AS IDENTITY, 
	project_id BIGINT NOT NULL, 
	enabled BOOLEAN DEFAULT false NOT NULL, 
	public_slug VARCHAR(120) NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	CONSTRAINT pk_project_public_settings PRIMARY KEY (id), 
	CONSTRAINT uq_project_public_settings_project_id UNIQUE (project_id), 
	CONSTRAINT uq_project_public_settings_public_slug UNIQUE (public_slug), 
	CONSTRAINT fk_project_public_settings_project_id_projects FOREIGN KEY(project_id) REFERENCES projects (id) ON DELETE CASCADE
);

CREATE INDEX ix_project_public_settings_project_id ON project_public_settings (project_id);

CREATE TABLE project_notification_settings (
	id BIGINT GENERATED ALWAYS AS IDENTITY, 
	project_id BIGINT NOT NULL, 
	telegram_enabled BOOLEAN DEFAULT false NOT NULL, 
	notify_alert_opened BOOLEAN DEFAULT true NOT NULL, 
	notify_alert_resolved BOOLEAN DEFAULT true NOT NULL, 
	notify_alert_recovered BOOLEAN DEFAULT true NOT NULL, 
	notify_alert_escalated BOOLEAN DEFAULT true NOT NULL, 
	notify_alert_reminder BOOLEAN DEFAULT false NOT NULL, 
	reminder_interval_minutes INTEGER, 
	minimum_business_risk_level VARCHAR(30) DEFAULT 'LOW' NOT NULL, 
	risk_extreme_enabled BOOLEAN DEFAULT true NOT NULL, 
	risk_very_high_enabled BOOLEAN DEFAULT true NOT NULL, 
	risk_high_enabled BOOLEAN DEFAULT true NOT NULL, 
	risk_medium_enabled BOOLEAN DEFAULT true NOT NULL, 
	risk_low_medium_enabled BOOLEAN DEFAULT true NOT NULL, 
	risk_low_enabled BOOLEAN DEFAULT true NOT NULL, 
	last_health_status VARCHAR(30), 
	last_health_fingerprint VARCHAR(64), 
	last_health_snapshot JSONB, 
	last_health_evaluated_at TIMESTAMP WITH TIME ZONE, 
	last_health_notified_at TIMESTAMP WITH TIME ZONE, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	CONSTRAINT pk_project_notification_settings PRIMARY KEY (id), 
	CONSTRAINT uq_project_notification_settings_project_id UNIQUE (project_id), 
	CONSTRAINT ck_project_notification_settings_reminder_positive CHECK (reminder_interval_minutes IS NULL OR reminder_interval_minutes > 0), 
	CONSTRAINT ck_project_notification_settings_risk_allowed CHECK (minimum_business_risk_level IN ('EXTREME','VERY_HIGH','HIGH','MEDIUM','LOW_MEDIUM','LOW')), 
	CONSTRAINT fk_project_notification_settings_project_id_projects FOREIGN KEY(project_id) REFERENCES projects (id) ON DELETE CASCADE
);

CREATE INDEX ix_project_notification_settings_project_id ON project_notification_settings (project_id);

CREATE TABLE project_notification_risk_policies (
	id BIGINT GENERATED ALWAYS AS IDENTITY, 
	project_id BIGINT NOT NULL, 
	risk_level VARCHAR(30) NOT NULL, 
	telegram_enabled BOOLEAN NOT NULL, 
	notify_on_open BOOLEAN DEFAULT true NOT NULL, 
	notify_on_escalation BOOLEAN DEFAULT true NOT NULL, 
	notify_on_recovery BOOLEAN DEFAULT true NOT NULL, 
	notify_on_resolved BOOLEAN DEFAULT true NOT NULL, 
	reminder_enabled BOOLEAN DEFAULT false NOT NULL, 
	initial_reminder_seconds INTEGER DEFAULT '0' NOT NULL, 
	repeat_interval_seconds INTEGER DEFAULT '0' NOT NULL, 
	max_reminders INTEGER DEFAULT '0' NOT NULL, 
	stop_reminders_on_ack BOOLEAN DEFAULT true NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	CONSTRAINT pk_project_notification_risk_policies PRIMARY KEY (id), 
	CONSTRAINT uq_project_notification_risk_policy UNIQUE (project_id, risk_level), 
	CONSTRAINT ck_project_notification_risk_policies_risk_level_allowed CHECK (risk_level IN ('EXTREME','VERY_HIGH','HIGH','MEDIUM','LOW_MEDIUM','LOW')), 
	CONSTRAINT ck_project_notification_risk_policies_initial_nonnegative CHECK (initial_reminder_seconds >= 0), 
	CONSTRAINT ck_project_notification_risk_policies_repeat_nonnegative CHECK (repeat_interval_seconds >= 0), 
	CONSTRAINT ck_project_notification_risk_policies_max_reminders_nonnegative CHECK (max_reminders >= 0), 
	CONSTRAINT fk_project_notification_risk_policies_project_id_projects FOREIGN KEY(project_id) REFERENCES projects (id) ON DELETE CASCADE
);

CREATE INDEX ix_project_notification_risk_policies_project_id ON project_notification_risk_policies (project_id);

CREATE TABLE project_notification_recipients (
	id BIGINT GENERATED ALWAYS AS IDENTITY, 
	project_id BIGINT NOT NULL, 
	name VARCHAR(120) NOT NULL, 
	telegram_chat_id VARCHAR(64) NOT NULL, 
	enabled BOOLEAN DEFAULT true NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	CONSTRAINT pk_project_notification_recipients PRIMARY KEY (id), 
	CONSTRAINT uq_project_notification_recipient_chat UNIQUE (project_id, telegram_chat_id), 
	CONSTRAINT fk_project_notification_recipients_project_id_projects FOREIGN KEY(project_id) REFERENCES projects (id) ON DELETE CASCADE
);

CREATE INDEX ix_project_notification_recipients_project_id ON project_notification_recipients (project_id);

CREATE TABLE alert_rule_actuator_model_profiles (
	profile_id BIGINT NOT NULL, 
	actuator_model_id BIGINT NOT NULL, 
	CONSTRAINT pk_alert_rule_actuator_model_profiles PRIMARY KEY (profile_id, actuator_model_id), 
	CONSTRAINT fk_alert_rule_actuator_model_profiles_profile_id_alert__211b FOREIGN KEY(profile_id) REFERENCES alert_rule_profiles (id) ON DELETE CASCADE, 
	CONSTRAINT fk_alert_rule_actuator_model_profiles_actuator_model_id_5c97 FOREIGN KEY(actuator_model_id) REFERENCES actuator_models (id) ON DELETE CASCADE
);

CREATE TABLE alert_rule_sensor_model_profiles (
	profile_id BIGINT NOT NULL, 
	sensor_model_id BIGINT NOT NULL, 
	CONSTRAINT pk_alert_rule_sensor_model_profiles PRIMARY KEY (profile_id, sensor_model_id), 
	CONSTRAINT fk_alert_rule_sensor_model_profiles_profile_id_alert_ru_cb7c FOREIGN KEY(profile_id) REFERENCES alert_rule_profiles (id) ON DELETE CASCADE, 
	CONSTRAINT fk_alert_rule_sensor_model_profiles_sensor_model_id_sen_8580 FOREIGN KEY(sensor_model_id) REFERENCES sensor_models (id) ON DELETE CASCADE
);

CREATE TABLE alert_rule_project_overrides (
	id BIGINT GENERATED ALWAYS AS IDENTITY, 
	rule_id BIGINT NOT NULL, 
	project_id BIGINT NOT NULL, 
	config JSONB NOT NULL, 
	is_enabled BOOLEAN DEFAULT true NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	CONSTRAINT pk_alert_rule_project_overrides PRIMARY KEY (id), 
	CONSTRAINT uq_alert_rule_project_overrides_rule_scope UNIQUE (rule_id, project_id), 
	CONSTRAINT fk_alert_rule_project_overrides_rule_id_alert_rules FOREIGN KEY(rule_id) REFERENCES alert_rules (id) ON DELETE CASCADE, 
	CONSTRAINT fk_alert_rule_project_overrides_project_id_projects FOREIGN KEY(project_id) REFERENCES projects (id) ON DELETE CASCADE
);

CREATE INDEX ix_alert_rule_project_overrides_project_id ON alert_rule_project_overrides (project_id);

CREATE TABLE device_credentials (
	id BIGINT GENERATED ALWAYS AS IDENTITY, 
	device_id BIGINT NOT NULL, 
	version INTEGER NOT NULL, 
	secret_encrypted TEXT NOT NULL, 
	issued_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	expires_at TIMESTAMP WITH TIME ZONE, 
	last_used_at TIMESTAMP WITH TIME ZONE, 
	revoked_at TIMESTAMP WITH TIME ZONE, 
	created_by BIGINT NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	CONSTRAINT pk_device_credentials PRIMARY KEY (id), 
	CONSTRAINT fk_device_credentials_device_id_devices FOREIGN KEY(device_id) REFERENCES devices (id) ON DELETE CASCADE, 
	CONSTRAINT fk_device_credentials_created_by_users FOREIGN KEY(created_by) REFERENCES users (id) ON DELETE RESTRICT
);

CREATE UNIQUE INDEX uq_active_device_credential ON device_credentials (device_id) WHERE revoked_at IS NULL;

CREATE UNIQUE INDEX uq_device_credential_version ON device_credentials (device_id, version);

CREATE TABLE sensors (
	id BIGINT GENERATED ALWAYS AS IDENTITY, 
	device_id BIGINT NOT NULL, 
	sensor_model_id BIGINT NOT NULL, 
	code VARCHAR(80) NOT NULL, 
	name VARCHAR(255) NOT NULL, 
	purpose sensor_purpose DEFAULT 'GENERAL' NOT NULL, 
	installation_location VARCHAR(255), 
	description TEXT, 
	status sensor_status NOT NULL, 
	last_seen_at TIMESTAMP WITH TIME ZONE, 
	warning_enabled BOOLEAN NOT NULL, 
	lower_threshold FLOAT, 
	upper_threshold FLOAT, 
	below_threshold_message TEXT, 
	above_threshold_message TEXT, 
	alert_risk_level VARCHAR(30), 
	alert_delay_seconds INTEGER NOT NULL, 
	is_enabled BOOLEAN NOT NULL, 
	disabled_at TIMESTAMP WITH TIME ZONE, 
	disabled_by_user_id BIGINT, 
	disabled_reason TEXT, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	is_deleted BOOLEAN NOT NULL, 
	deleted_at TIMESTAMP WITH TIME ZONE, 
	CONSTRAINT pk_sensors PRIMARY KEY (id), 
	CONSTRAINT ck_sensors_alert_delay_non_negative CHECK (alert_delay_seconds >= 0), 
	CONSTRAINT ck_sensors_threshold_order CHECK (lower_threshold IS NULL OR upper_threshold IS NULL OR lower_threshold < upper_threshold), 
	CONSTRAINT fk_sensors_device_id_devices FOREIGN KEY(device_id) REFERENCES devices (id) ON DELETE RESTRICT, 
	CONSTRAINT fk_sensors_sensor_model_id_sensor_models FOREIGN KEY(sensor_model_id) REFERENCES sensor_models (id) ON DELETE RESTRICT, 
	CONSTRAINT fk_sensors_disabled_by_user_id_users FOREIGN KEY(disabled_by_user_id) REFERENCES users (id) ON DELETE SET NULL
);

CREATE UNIQUE INDEX uq_sensor_device_code ON sensors (device_id, code);

CREATE INDEX ix_sensors_is_deleted ON sensors (is_deleted);

CREATE INDEX ix_sensors_purpose ON sensors (purpose);

CREATE INDEX ix_sensors_device_id ON sensors (device_id);

CREATE TABLE actuators (
	id BIGINT GENERATED ALWAYS AS IDENTITY, 
	device_id BIGINT NOT NULL, 
	actuator_model_id BIGINT, 
	sequence_number INTEGER NOT NULL, 
	code VARCHAR(80) NOT NULL, 
	name VARCHAR(255) NOT NULL, 
	location VARCHAR(255), 
	notes TEXT, 
	is_enabled BOOLEAN NOT NULL, 
	desired_state BOOLEAN, 
	reported_state BOOLEAN, 
	last_command_at TIMESTAMP WITH TIME ZONE, 
	reported_state_at TIMESTAMP WITH TIME ZONE, 
	last_reported_at TIMESTAMP WITH TIME ZONE, 
	disabled_at TIMESTAMP WITH TIME ZONE, 
	disabled_by_user_id BIGINT, 
	disabled_reason TEXT, 
	removed_at TIMESTAMP WITH TIME ZONE, 
	removed_by_user_id BIGINT, 
	removed_reason TEXT, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	is_deleted BOOLEAN NOT NULL, 
	deleted_at TIMESTAMP WITH TIME ZONE, 
	CONSTRAINT pk_actuators PRIMARY KEY (id), 
	CONSTRAINT uq_actuator_device_code UNIQUE (device_id, code), 
	CONSTRAINT fk_actuators_device_id_devices FOREIGN KEY(device_id) REFERENCES devices (id) ON DELETE RESTRICT, 
	CONSTRAINT fk_actuators_actuator_model_id_actuator_models FOREIGN KEY(actuator_model_id) REFERENCES actuator_models (id) ON DELETE SET NULL, 
	CONSTRAINT fk_actuators_disabled_by_user_id_users FOREIGN KEY(disabled_by_user_id) REFERENCES users (id) ON DELETE SET NULL, 
	CONSTRAINT fk_actuators_removed_by_user_id_users FOREIGN KEY(removed_by_user_id) REFERENCES users (id) ON DELETE SET NULL
);

CREATE INDEX ix_actuators_device_id ON actuators (device_id);

CREATE INDEX ix_actuators_is_deleted ON actuators (is_deleted);

CREATE TABLE sensor_alerts (
	id BIGINT GENERATED ALWAYS AS IDENTITY, 
	sensor_id BIGINT NOT NULL, 
	alert_type alert_type NOT NULL, 
	severity alert_severity NOT NULL, 
	status alert_status NOT NULL, 
	message TEXT NOT NULL, 
	trigger_value FLOAT, 
	started_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	last_triggered_at TIMESTAMP WITH TIME ZONE, 
	occurrence_count INTEGER NOT NULL, 
	acknowledged_at TIMESTAMP WITH TIME ZONE, 
	acknowledged_by BIGINT, 
	condition_active BOOLEAN NOT NULL, 
	normalized_at TIMESTAMP WITH TIME ZONE, 
	resolved_at TIMESTAMP WITH TIME ZONE, 
	resolved_by_user_id BIGINT, 
	resolution_note TEXT, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	CONSTRAINT pk_sensor_alerts PRIMARY KEY (id), 
	CONSTRAINT fk_sensor_alerts_sensor_id_sensors FOREIGN KEY(sensor_id) REFERENCES sensors (id) ON DELETE RESTRICT, 
	CONSTRAINT fk_sensor_alerts_acknowledged_by_users FOREIGN KEY(acknowledged_by) REFERENCES users (id) ON DELETE SET NULL, 
	CONSTRAINT fk_sensor_alerts_resolved_by_user_id_users FOREIGN KEY(resolved_by_user_id) REFERENCES users (id) ON DELETE SET NULL
);

CREATE UNIQUE INDEX uq_active_sensor_alert ON sensor_alerts (sensor_id, alert_type) WHERE status IN ('PENDING', 'OPEN', 'ACKNOWLEDGED');

CREATE TABLE actuator_commands (
	id BIGINT GENERATED ALWAYS AS IDENTITY, 
	actuator_id BIGINT NOT NULL, 
	desired_state BOOLEAN NOT NULL, 
	reported_state BOOLEAN, 
	status VARCHAR(30) NOT NULL, 
	requested_by_user_id BIGINT NOT NULL, 
	requested_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	acknowledged_at TIMESTAMP WITH TIME ZONE, 
	published_at TIMESTAMP WITH TIME ZONE, 
	failed_at TIMESTAMP WITH TIME ZONE, 
	timed_out_at TIMESTAMP WITH TIME ZONE, 
	failure_reason TEXT, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	CONSTRAINT pk_actuator_commands PRIMARY KEY (id), 
	CONSTRAINT fk_actuator_commands_actuator_id_actuators FOREIGN KEY(actuator_id) REFERENCES actuators (id) ON DELETE RESTRICT, 
	CONSTRAINT fk_actuator_commands_requested_by_user_id_users FOREIGN KEY(requested_by_user_id) REFERENCES users (id) ON DELETE RESTRICT
);

CREATE INDEX ix_actuator_commands_actuator_id ON actuator_commands (actuator_id);

CREATE TABLE telemetry_readings (
	id BIGINT GENERATED ALWAYS AS IDENTITY, 
	sensor_id BIGINT NOT NULL, 
	recorded_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	received_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	value FLOAT NOT NULL, 
	CONSTRAINT pk_telemetry_readings PRIMARY KEY (id), 
	CONSTRAINT fk_telemetry_readings_sensor_id_sensors FOREIGN KEY(sensor_id) REFERENCES sensors (id) ON DELETE RESTRICT
);

CREATE UNIQUE INDEX uq_telemetry_sensor_recorded ON telemetry_readings (sensor_id, recorded_at);

CREATE TABLE telemetry_aggregates (
	id BIGINT GENERATED ALWAYS AS IDENTITY, 
	sensor_id BIGINT NOT NULL, 
	period aggregate_period NOT NULL, 
	bucket_time TIMESTAMP WITH TIME ZONE NOT NULL, 
	min_value FLOAT NOT NULL, 
	max_value FLOAT NOT NULL, 
	avg_value FLOAT NOT NULL, 
	record_count INTEGER NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	CONSTRAINT pk_telemetry_aggregates PRIMARY KEY (id), 
	CONSTRAINT ck_telemetry_aggregates_aggregate_record_count_positive CHECK (record_count > 0), 
	CONSTRAINT ck_telemetry_aggregates_aggregate_value_order CHECK (min_value <= avg_value AND avg_value <= max_value), 
	CONSTRAINT fk_telemetry_aggregates_sensor_id_sensors FOREIGN KEY(sensor_id) REFERENCES sensors (id) ON DELETE RESTRICT
);

CREATE UNIQUE INDEX uq_aggregate_bucket ON telemetry_aggregates (sensor_id, period, bucket_time);

CREATE TABLE alert_rule_actuator_overrides (
	id BIGINT GENERATED ALWAYS AS IDENTITY, 
	rule_id BIGINT NOT NULL, 
	actuator_id BIGINT NOT NULL, 
	config JSONB NOT NULL, 
	is_enabled BOOLEAN DEFAULT true NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	CONSTRAINT pk_alert_rule_actuator_overrides PRIMARY KEY (id), 
	CONSTRAINT uq_alert_rule_actuator_overrides_rule_scope UNIQUE (rule_id, actuator_id), 
	CONSTRAINT fk_alert_rule_actuator_overrides_rule_id_alert_rules FOREIGN KEY(rule_id) REFERENCES alert_rules (id) ON DELETE CASCADE, 
	CONSTRAINT fk_alert_rule_actuator_overrides_actuator_id_actuators FOREIGN KEY(actuator_id) REFERENCES actuators (id) ON DELETE CASCADE
);

CREATE INDEX ix_alert_rule_actuator_overrides_actuator_id ON alert_rule_actuator_overrides (actuator_id);

CREATE TABLE alert_rule_sensor_overrides (
	id BIGINT GENERATED ALWAYS AS IDENTITY, 
	rule_id BIGINT NOT NULL, 
	sensor_id BIGINT NOT NULL, 
	config JSONB NOT NULL, 
	is_enabled BOOLEAN DEFAULT true NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	CONSTRAINT pk_alert_rule_sensor_overrides PRIMARY KEY (id), 
	CONSTRAINT uq_alert_rule_sensor_overrides_rule_scope UNIQUE (rule_id, sensor_id), 
	CONSTRAINT fk_alert_rule_sensor_overrides_rule_id_alert_rules FOREIGN KEY(rule_id) REFERENCES alert_rules (id) ON DELETE CASCADE, 
	CONSTRAINT fk_alert_rule_sensor_overrides_sensor_id_sensors FOREIGN KEY(sensor_id) REFERENCES sensors (id) ON DELETE CASCADE
);

CREATE INDEX ix_alert_rule_sensor_overrides_sensor_id ON alert_rule_sensor_overrides (sensor_id);

CREATE TABLE actuator_feedback_bindings (
	id BIGINT GENERATED ALWAYS AS IDENTITY, 
	actuator_id BIGINT NOT NULL, 
	sensor_id BIGINT NOT NULL, 
	feedback_role VARCHAR(40) NOT NULL, 
	model_feedback_id BIGINT, 
	value_key VARCHAR(80) DEFAULT 'current_a' NOT NULL, 
	unit VARCHAR(50) DEFAULT 'A' NOT NULL, 
	data_type VARCHAR(30) DEFAULT 'FLOAT' NOT NULL, 
	lower_threshold FLOAT, 
	upper_threshold FLOAT, 
	is_enabled BOOLEAN DEFAULT true NOT NULL, 
	created_by BIGINT, 
	updated_by BIGINT, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	CONSTRAINT pk_actuator_feedback_bindings PRIMARY KEY (id), 
	CONSTRAINT uq_actuator_feedback_role UNIQUE (actuator_id, feedback_role), 
	CONSTRAINT ck_actuator_feedback_bindings_actuator_feedback_role_allowed CHECK (feedback_role IN ('SUPPLY_VOLTAGE','RUNNING_CURRENT')), 
	CONSTRAINT ck_actuator_feedback_bindings_data_type_allowed CHECK (data_type IN ('FLOAT')), 
	CONSTRAINT ck_actuator_feedback_bindings_feedback_binding_threshold_order CHECK (lower_threshold IS NULL OR upper_threshold IS NULL OR lower_threshold < upper_threshold), 
	CONSTRAINT fk_actuator_feedback_bindings_actuator_id_actuators FOREIGN KEY(actuator_id) REFERENCES actuators (id) ON DELETE CASCADE, 
	CONSTRAINT fk_actuator_feedback_bindings_sensor_id_sensors FOREIGN KEY(sensor_id) REFERENCES sensors (id) ON DELETE RESTRICT, 
	CONSTRAINT fk_actuator_feedback_bindings_model_feedback_id_actuato_f3d6 FOREIGN KEY(model_feedback_id) REFERENCES actuator_model_feedback_definitions (id) ON DELETE SET NULL, 
	CONSTRAINT fk_actuator_feedback_bindings_created_by_users FOREIGN KEY(created_by) REFERENCES users (id) ON DELETE SET NULL, 
	CONSTRAINT fk_actuator_feedback_bindings_updated_by_users FOREIGN KEY(updated_by) REFERENCES users (id) ON DELETE SET NULL
);

CREATE INDEX ix_actuator_feedback_bindings_sensor_id ON actuator_feedback_bindings (sensor_id);

CREATE INDEX ix_actuator_feedback_bindings_actuator_id ON actuator_feedback_bindings (actuator_id);

CREATE INDEX ix_actuator_feedback_bindings_model_feedback_id ON actuator_feedback_bindings (model_feedback_id);

CREATE TABLE operational_incidents (
	id BIGINT GENERATED ALWAYS AS IDENTITY, 
	project_id BIGINT NOT NULL, 
	rule_id BIGINT, 
	rule_revision_id BIGINT, 
	device_id BIGINT, 
	sensor_id BIGINT, 
	actuator_id BIGINT, 
	context_key VARCHAR(160) NOT NULL, 
	status VARCHAR(30) NOT NULL, 
	technical_severity VARCHAR(30) NOT NULL, 
	business_risk_level_snapshot VARCHAR(30) NOT NULL, 
	started_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	opened_at TIMESTAMP WITH TIME ZONE, 
	acknowledged_at TIMESTAMP WITH TIME ZONE, 
	normalized_at TIMESTAMP WITH TIME ZONE, 
	resolved_at TIMESTAMP WITH TIME ZONE, 
	last_triggered_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	occurrence_count INTEGER DEFAULT '1' NOT NULL, 
	trigger_snapshot JSONB NOT NULL, 
	acknowledged_by BIGINT, 
	resolved_by BIGINT, 
	resolution_note TEXT, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	CONSTRAINT pk_operational_incidents PRIMARY KEY (id), 
	CONSTRAINT ck_operational_incidents_operational_incident_status_allowed CHECK (status IN ('PENDING','OPEN','ACKNOWLEDGED','NORMALIZED','RESOLVED')), 
	CONSTRAINT ck_operational_incidents_operational_incident_severity_allowed CHECK (technical_severity IN ('WARNING','CRITICAL')), 
	CONSTRAINT fk_operational_incidents_project_id_projects FOREIGN KEY(project_id) REFERENCES projects (id) ON DELETE RESTRICT, 
	CONSTRAINT fk_operational_incidents_rule_id_alert_rules FOREIGN KEY(rule_id) REFERENCES alert_rules (id) ON DELETE RESTRICT, 
	CONSTRAINT fk_operational_incidents_rule_revision_id_alert_rule_revisions FOREIGN KEY(rule_revision_id) REFERENCES alert_rule_revisions (id) ON DELETE RESTRICT, 
	CONSTRAINT fk_operational_incidents_device_id_devices FOREIGN KEY(device_id) REFERENCES devices (id) ON DELETE RESTRICT, 
	CONSTRAINT fk_operational_incidents_sensor_id_sensors FOREIGN KEY(sensor_id) REFERENCES sensors (id) ON DELETE RESTRICT, 
	CONSTRAINT fk_operational_incidents_actuator_id_actuators FOREIGN KEY(actuator_id) REFERENCES actuators (id) ON DELETE RESTRICT, 
	CONSTRAINT fk_operational_incidents_acknowledged_by_users FOREIGN KEY(acknowledged_by) REFERENCES users (id) ON DELETE SET NULL, 
	CONSTRAINT fk_operational_incidents_resolved_by_users FOREIGN KEY(resolved_by) REFERENCES users (id) ON DELETE SET NULL
);

CREATE INDEX ix_operational_incidents_rule_status ON operational_incidents (rule_id, status);

CREATE INDEX ix_operational_incidents_project_status ON operational_incidents (project_id, status);

CREATE UNIQUE INDEX uq_active_operational_incident ON operational_incidents (rule_id, context_key) WHERE status IN ('PENDING','OPEN','ACKNOWLEDGED','NORMALIZED');

CREATE TABLE actuator_state_history (
	id BIGINT GENERATED ALWAYS AS IDENTITY, 
	actuator_id BIGINT NOT NULL, 
	state BOOLEAN NOT NULL, 
	recorded_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	source VARCHAR(30) NOT NULL, 
	command_id BIGINT, 
	CONSTRAINT pk_actuator_state_history PRIMARY KEY (id), 
	CONSTRAINT fk_actuator_state_history_actuator_id_actuators FOREIGN KEY(actuator_id) REFERENCES actuators (id) ON DELETE CASCADE, 
	CONSTRAINT fk_actuator_state_history_command_id_actuator_commands FOREIGN KEY(command_id) REFERENCES actuator_commands (id) ON DELETE SET NULL
);

CREATE INDEX ix_actuator_state_history_actuator_recorded ON actuator_state_history (actuator_id, recorded_at);

CREATE INDEX ix_actuator_state_history_actuator_id ON actuator_state_history (actuator_id);

CREATE TABLE notification_outbox (
	id BIGINT GENERATED ALWAYS AS IDENTITY, 
	incident_id BIGINT NOT NULL, 
	event_type VARCHAR(30) NOT NULL, 
	idempotency_key VARCHAR(200) NOT NULL, 
	payload_snapshot JSONB NOT NULL, 
	status VARCHAR(30) DEFAULT 'PENDING' NOT NULL, 
	available_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	attempt_count INTEGER DEFAULT '0' NOT NULL, 
	last_attempt_at TIMESTAMP WITH TIME ZONE, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	processed_at TIMESTAMP WITH TIME ZONE, 
	skip_reason VARCHAR(120), 
	CONSTRAINT pk_notification_outbox PRIMARY KEY (id), 
	CONSTRAINT fk_notification_outbox_incident_id_operational_incidents FOREIGN KEY(incident_id) REFERENCES operational_incidents (id) ON DELETE CASCADE, 
	CONSTRAINT uq_notification_outbox_idempotency_key UNIQUE (idempotency_key)
);

CREATE INDEX ix_notification_outbox_status_available ON notification_outbox (status, available_at);

CREATE TABLE notification_deliveries (
	id BIGINT GENERATED ALWAYS AS IDENTITY, 
	outbox_id BIGINT NOT NULL, 
	incident_id BIGINT NOT NULL, 
	channel VARCHAR(30) NOT NULL, 
	recipient_id BIGINT, 
	recipient_reference VARCHAR(120) NOT NULL, 
	idempotency_key VARCHAR(240) NOT NULL, 
	status VARCHAR(30) DEFAULT 'PENDING' NOT NULL, 
	attempt_count INTEGER DEFAULT '0' NOT NULL, 
	last_attempt_at TIMESTAMP WITH TIME ZONE, 
	next_retry_at TIMESTAMP WITH TIME ZONE, 
	sent_at TIMESTAMP WITH TIME ZONE, 
	failed_at TIMESTAMP WITH TIME ZONE, 
	error_category VARCHAR(60), 
	provider_message_id VARCHAR(120), 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	CONSTRAINT pk_notification_deliveries PRIMARY KEY (id), 
	CONSTRAINT fk_notification_deliveries_outbox_id_notification_outbox FOREIGN KEY(outbox_id) REFERENCES notification_outbox (id) ON DELETE CASCADE, 
	CONSTRAINT fk_notification_deliveries_incident_id_operational_incidents FOREIGN KEY(incident_id) REFERENCES operational_incidents (id) ON DELETE CASCADE, 
	CONSTRAINT fk_notification_deliveries_recipient_id_project_notific_1eb3 FOREIGN KEY(recipient_id) REFERENCES project_notification_recipients (id) ON DELETE SET NULL, 
	CONSTRAINT uq_notification_deliveries_idempotency_key UNIQUE (idempotency_key)
);

CREATE INDEX ix_notification_deliveries_outbox_status ON notification_deliveries (outbox_id, status);

ALTER TABLE alert_rules ADD CONSTRAINT fk_alert_rules_current_revision_id_alert_rule_revisions FOREIGN KEY(current_revision_id) REFERENCES alert_rule_revisions (id) ON DELETE SET NULL;

COMMIT;
