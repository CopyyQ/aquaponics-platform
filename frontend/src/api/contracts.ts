export type Id = number
export type PublicId = string
export type DateTime = string
export type AquaponicsSystemStatus = "ACTIVE" | "INACTIVE" | "ARCHIVED" | "DISABLED"
export type AlertResourceType = "SENSOR" | "ACTUATOR"
export type AlertDirection = "BELOW" | "ABOVE"
export type AlertLifecycleStatus = "PENDING" | "OPEN" | "ACKNOWLEDGED" | "NORMALIZED" | "RESOLVED"
export type AlertSeverity = "WARNING" | "CRITICAL"
export type MonitoringRange = "1h" | "6h" | "12h" | "24h" | "30d"
export type MemberRole = "VIEWER" | "TECHNICIAN" | "OWNER"
export type ThresholdMetricType = "SENSOR_VALUE" | "VOLTAGE" | "CURRENT"
export type DeviceStatus = "WAITING_CONNECTION" | "ONLINE" | "OFFLINE" | "DISABLED"
export type SensorStatus = DeviceStatus

export interface TokenResponse { access_token: string; token_type: string; must_change_password: boolean }
export type UserStatus = "ACTIVE" | "DISABLED" | "LOCKED" | "SOFT_DELETED"
export type RiskLevel = "EXTREME" | "VERY_HIGH" | "HIGH" | "MEDIUM" | "LOW_MEDIUM" | "LOW"
export type ActuatorThresholdMetric = "VOLTAGE" | "CURRENT"

export interface SessionUser {
  id: PublicId; username: string; full_name: string; email: string; phone_number: string; address?: string
  role_id: Id | null; status: UserStatus; must_change_password: boolean; last_login_at: DateTime | null
  created_at: DateTime; updated_at: DateTime; token_version: number; is_deleted: boolean; deleted_at: DateTime | null
  disabled_at: DateTime | null; disabled_reason: string | null
  locked_at: DateTime | null; locked_reason: string | null
}
export interface Session { user: SessionUser; permissions: string[] }
export interface UserSummary { id: PublicId; username: string; full_name: string; email: string; phone_number: string; role_id: Id | null; role_code: string | null; role_name: string | null; status: UserStatus; last_login_at: DateTime | null; created_at: DateTime; updated_at: DateTime }
export interface UserAquaponicsSystem { id: PublicId; code: string; name: string; owner_user_id: PublicId; location: string | null; status: string; role: "OWNER"; relationship: "OWNER" }
export interface UserSelfUpdate { full_name?: string | null; email?: string | null; phone_number?: string | null; address?: string | null }
export interface ChangePasswordRequest { current_password: string; new_password: string; confirm_password: string }

export interface AquaponicsSystem { id: PublicId; code: string; name: string; location: string | null; description: string | null; owner_user_id: PublicId; status: AquaponicsSystemStatus; disabled_at?: DateTime | null; disabled_reason?: string | null }
export interface AquaponicsSystemCreate { name: string; owner_user_id: PublicId }
export interface AquaponicsSystemUpdate { name?: string | null; location?: string | null; description?: string | null }
export interface Sensor { id: PublicId; device_id: PublicId; sensor_model_id: Id; code: string; name: string; installation_location: string | null; description: string | null; status: string; is_enabled: boolean }
export interface SensorInput { sensor_model_id: Id; code: string; name: string; installation_location?: string | null; description?: string | null }
export interface SensorUpdate { sensor_model_id?: Id | null; code?: string | null; name?: string | null; installation_location?: string | null; description?: string | null; is_enabled?: boolean | null }
export interface Actuator { id: PublicId; device_id: PublicId; actuator_model_id: Id | null; code: string; name: string; location: string | null; notes: string | null; is_enabled: boolean; desired_state: boolean | null; reported_state: boolean | null; voltage_v: number | null; current_a: number | null }
export interface ActuatorInput { actuator_model_id: Id; code: string; name: string; location?: string | null; notes?: string | null }
export interface ActuatorUpdate { actuator_model_id?: Id | null; code?: string | null; name?: string | null; location?: string | null; notes?: string | null; is_enabled?: boolean | null }
export interface Device { id: PublicId; aquaponics_system_id: PublicId; code: string; name: string; description: string | null; location: string | null; device_template_id: Id | null; status: DeviceStatus; is_enabled: boolean; sensors: Sensor[]; actuators: Actuator[] }
export interface DeviceInput { code: string; name: string; description?: string | null; location?: string | null; device_template_id?: Id | null }
export interface DeviceUpdate { code?: string | null; name?: string | null; description?: string | null; location?: string | null; device_template_id?: Id | null; is_enabled?: boolean | null }

export interface TelemetryReading { id: Id; sensor_id: PublicId; recorded_at: DateTime; received_at: DateTime; value: number }
export interface ActuatorReading { id: Id; actuator_id: PublicId; voltage_v: number | null; current_a: number | null; recorded_at: DateTime; received_at: DateTime; quality: string | null }
export interface ActuatorCommand { command_id: Id; actuator_id: PublicId; desired_state: boolean; reported_state: boolean | null; status: string; requested_at: DateTime }
export interface ActuatorCommandCreate { desired_state: boolean }
export interface ThresholdAlertConfig { enabled: boolean; lower_threshold: number | null; upper_threshold: number | null; below_risk_level: RiskLevel | null; above_risk_level: RiskLevel | null; below_message: string | null; above_message: string | null; below_consequence: string | null; above_consequence: string | null; below_recommended_actions: string | null; above_recommended_actions: string | null; delay_seconds: number; id: Id; sensor_id: PublicId | null; actuator_id: PublicId | null; metric_type: ThresholdMetricType; created_at: DateTime; updated_at: DateTime }
export interface ThresholdAlertConfigInput { enabled?: boolean; lower_threshold?: number | null; upper_threshold?: number | null; below_risk_level?: RiskLevel | null; above_risk_level?: RiskLevel | null; below_message?: string | null; above_message?: string | null; below_consequence?: string | null; above_consequence?: string | null; below_recommended_actions?: string | null; above_recommended_actions?: string | null; delay_seconds?: number }

export interface Alert { id: Id; resource_type: AlertResourceType; device_id: PublicId | null; sensor_id: PublicId | null; actuator_id: PublicId | null; metric: string; direction: AlertDirection | null; alert_type: string; severity: AlertSeverity; risk_level: string; status: AlertLifecycleStatus; message: string; actual_value: number | null; threshold_value: number | null; started_at: DateTime; last_triggered_at: DateTime; occurrence_count: number; acknowledged_at: DateTime | null; acknowledged_by: PublicId | null; condition_active: boolean; normalized_at: DateTime | null; resolved_at: DateTime | null; resolved_by_user_id: PublicId | null; resolved_by_name: string | null; resolution_note: string | null; created_at: DateTime; updated_at: DateTime }
export interface AlertResolutionRequest { resolution_note: string }

export interface MonitoringLatestValue { value: number | null; recorded_at: DateTime | null; quality?: string | null; quality_reason?: string | null; engineering_min?: number | null; engineering_max?: number | null; freshness?: string | null }
export interface MonitoringSensor { id: PublicId; code: string; name: string; unit: string; is_enabled: boolean; connection_status: string; data_status: string; latest: MonitoringLatestValue | null; lower_threshold: number | null; upper_threshold: number | null; threshold_state?: string | null; alerts_enabled?: boolean }
export interface MonitoringElectricalMetric { configured: boolean; sensor_id: Id | null; sensor_code?: string | null; sensor_name?: string | null; sensor_model_code?: string | null; source_device_id?: Id | null; source_device_code?: string | null; source_device_name?: string | null; value_key?: string | null; value: number | null; unit: "V" | "A"; quality: "VALID" | "OUT_OF_RANGE" | "INVALID" | "NO_DATA" | "UNVALIDATED"; freshness: "FRESH" | "STALE" | "NO_DATA"; recorded_at: DateTime | null; received_at: DateTime | null; lower_threshold: number | null; upper_threshold: number | null; threshold_source: "ACTUATOR_OVERRIDE" | "MODEL_DEFAULT" | "NONE"; threshold_status: "BELOW_RANGE" | "ABOVE_RANGE" | "IN_RANGE" | "NO_DATA" | "STALE" | "INVALID" | "UNCONFIGURED" }
export interface MonitoringElectrical { voltage: MonitoringElectricalMetric; current: MonitoringElectricalMetric; configured: boolean; sensor_id: Id | null; current_a: number | null; quality: "VALID" | "OUT_OF_RANGE" | "INVALID" | "NO_DATA" | "UNVALIDATED"; freshness: "FRESH" | "STALE" | "NO_DATA"; recorded_at: DateTime | null; received_at: DateTime | null; minimum_running_current_a: number | null; maximum_running_current_a: number | null }
export interface MonitoringActiveAlert { id: Id; technical_severity: string; business_risk_level: string; status: string; rule_name: string; evaluator_type: string; condition_summary: string; started_at: DateTime; duration_seconds: number; evidence: JsonObject }
export interface MonitoringActuator { id: PublicId; code: string; name: string; actuator_model: string | null; connection_status: DeviceStatus; desired_state: boolean | null; reported_state: boolean | null; synchronization_status: string; latest_command: { status: string; requested_at: DateTime } | null; last_reported_at: DateTime | null; electrical: MonitoringElectrical; active_alert: MonitoringActiveAlert | null }
export interface MonitoringDevice { id: PublicId; code: string; name: string; is_enabled: boolean; connection_status: string; location: string | null; last_seen_at: DateTime | null; sensors: MonitoringSensor[]; actuators: MonitoringActuator[] }
export interface MonitoringLatest { aquaponics_system_id: PublicId; devices: MonitoringDevice[] }
export interface MonitoringSeriesPoint { recorded_at: DateTime; value: number }
export interface MonitoringSeries { sensor_id: PublicId; unit: string; points: MonitoringSeriesPoint[]; gaps: { from: DateTime; to: DateTime; reason: string }[] }
export interface MonitoringSeriesRead { aquaponics_system_id: PublicId; range: MonitoringRange; resolution: string; series: MonitoringSeries[] }
export interface MonitoringActuatorHistoryPoint { recorded_at: DateTime; state: boolean }
export interface MonitoringActuatorHistoryGap { from: DateTime; to: DateTime; reason: string }
export interface MonitoringActuatorStatistics { on_duration_seconds: number; off_duration_seconds: number; unknown_duration_seconds: number; on_percentage: number | null; on_count: number; off_count: number; last_changed_at: DateTime | null }
export interface MonitoringActuatorHistory { actuator_id: PublicId; points: MonitoringActuatorHistoryPoint[]; gaps: MonitoringActuatorHistoryGap[]; statistics: MonitoringActuatorStatistics }
export interface MonitoringActuatorHistoryRead { aquaponics_system_id: PublicId; device_id: PublicId; range: MonitoringRange; items: MonitoringActuatorHistory[] }

export interface Member { id: Id; user_id: PublicId; name: string; role: string; joined_at: DateTime }
export interface MemberCreate { user_id: PublicId; role?: MemberRole }
export interface MemberUpdate { role: MemberRole }
export interface Activity { id: Id; action: string; actor: { id: PublicId; name: string }; entity: { type: string; id: PublicId | Id | null; name: string }; summary: string; created_at: DateTime }
export interface ActivityList { items: Activity[]; total: number; page: number; page_size: number }
export interface AlertSettings { enabled: boolean; in_app_enabled: boolean; telegram_enabled: boolean }
export interface AlertSettingsUpdate { enabled?: boolean; in_app_enabled?: boolean; telegram_enabled?: boolean }

export interface DeviceTemplate { id: Id; code: string; name: string; description: string | null; is_active: boolean; sensors: TemplateSensorSlot[]; actuators: TemplateActuatorSlot[] }
export interface DeviceTemplateInput { code: string; name: string; description?: string | null }
export interface DeviceTemplateUpdate { name?: string | null; description?: string | null; is_active?: boolean | null }
export interface TemplateSensorSlot { id: Id; template_id: Id; code: string; sensor_model_id: Id; sensor_model_name: string; sort_order: number; is_required: boolean }
export interface TemplateSensorSlotInput { sensor_model_id: Id; code: string; sort_order?: number; is_required?: boolean }
export interface TemplateSensorSlotUpdate { sensor_model_id?: Id | null; code?: string | null; sort_order?: number | null; is_required?: boolean | null }
export interface TemplateActuatorSlot { id: Id; template_id: Id; code: string; actuator_model_id: Id; actuator_model_name: string; sort_order: number; is_required: boolean }
export interface TemplateActuatorSlotInput { actuator_model_id: Id; code: string; sort_order?: number; is_required?: boolean }
export interface TemplateActuatorSlotUpdate { actuator_model_id?: Id | null; code?: string | null; sort_order?: number | null; is_required?: boolean | null }
export interface SensorModel { id: Id; code: string; name: string; unit: string; description: string | null; value_type: string; chart_type: string; measurement_semantics: string; is_active: boolean; is_visible: boolean; created_at: DateTime; updated_at: DateTime }
export interface SensorModelInput { code: string; name: string; unit: string; description?: string | null; value_type?: string; chart_type?: string; measurement_semantics?: string; is_active?: boolean }
export interface SensorModelUpdate { name?: string | null; unit?: string | null; description?: string | null; value_type?: string | null; chart_type?: string | null; measurement_semantics?: string | null; is_active?: boolean | null }
export interface ActuatorModel { id: Id; code: string; name: string; description: string | null; data_type: string; default_state: boolean; sort_order: number; is_active: boolean; nominal_voltage_v: number | null; voltage_tolerance_v: number | null; zero_voltage_max_v: number | null; minimum_running_current_a: number | null; maximum_running_current_a: number | null; created_at: DateTime; updated_at: DateTime }
export interface ActuatorModelInput { code: string; name: string; description?: string | null; data_type?: string; default_state?: boolean; sort_order?: number; nominal_voltage_v?: number | null; voltage_tolerance_v?: number | null; zero_voltage_max_v?: number | null; minimum_running_current_a?: number | null; maximum_running_current_a?: number | null }
export interface ActuatorModelUpdate { name?: string | null; description?: string | null; data_type?: string | null; default_state?: boolean | null; sort_order?: number | null; is_active?: boolean | null; nominal_voltage_v?: number | null; voltage_tolerance_v?: number | null; zero_voltage_max_v?: number | null; minimum_running_current_a?: number | null; maximum_running_current_a?: number | null }

export type ScadaEntityType = "DEVICE" | "SENSOR" | "ACTUATOR"
export type ScadaConnectionType = "WATER_PIPE" | "AIR_PIPE"
export type ScadaDashboardStatus = "GENERATED" | "DRAFT" | "PUBLISHED"
export type ScadaFreshness = "FRESH" | "STALE" | "NO_DATA"
export type ScadaQuality = "VALID" | "OUT_OF_RANGE" | "INVALID" | "UNVALIDATED"
export type ScadaSynchronization = "IN_SYNC" | "OUT_OF_SYNC" | "UNKNOWN"
export type JsonValue = string | number | boolean | null | JsonValue[] | { [key: string]: JsonValue }
export type JsonObject = { [key: string]: JsonValue }

export interface ScadaBinding { entity_type: ScadaEntityType; entity_id: PublicId }
export interface ScadaSymbol { id: string; type: string; label: string; position: [number, number, number]; binding?: ScadaBinding | null }
export interface ScadaConnection { id: string; type: ScadaConnectionType; source_symbol_id: string; target_symbol_id: string; flow_direction: "SOURCE_TO_TARGET"; active: boolean }
export interface ScadaLayout { schema_version: number; camera: JsonObject; symbols: ScadaSymbol[]; connections: ScadaConnection[] }
export interface ScadaDashboardInfo { id: Id | null; status: ScadaDashboardStatus; version: number; schema_version: number }
export interface ScadaInventoryDevice { id: PublicId; code: string; name: string; device_template_id: Id | null; template_code: string | null; enabled: boolean; connectivity: string; last_seen_at: DateTime | null }
export interface ScadaInventorySensor { id: PublicId; code: string; name: string; sensor_model_code: string; unit: string; device_id: PublicId; enabled: boolean }
export interface ScadaInventoryActuator { id: PublicId; code: string; name: string; actuator_model_code: string | null; device_id: PublicId; enabled: boolean }
export interface ScadaInventory { devices: ScadaInventoryDevice[]; sensors: ScadaInventorySensor[]; actuators: ScadaInventoryActuator[] }
export interface ScadaRuntimeDevice { id: PublicId; connectivity: string; last_seen_at: DateTime | null }
export interface ScadaRuntimeSensor { id: PublicId; value: number | null; recorded_at: DateTime | null; received_at: DateTime | null; freshness: ScadaFreshness; quality: ScadaQuality; quality_reason: string | null }
export interface ScadaRuntimeActuator { id: PublicId; desired_state: boolean | null; reported_state: boolean | null; synchronization: ScadaSynchronization; command_status: string | null; command_time: DateTime | null; last_ack_at: DateTime | null; failure_reason: string | null }
export interface ScadaRuntimeAlert { id: Id; resource_type: AlertResourceType; sensor_id: PublicId | null; actuator_id: PublicId | null; device_id: PublicId | null; severity: string; status: string; title: string; value: number | null; timestamp: DateTime }
export interface ScadaRuntimeState { devices: ScadaRuntimeDevice[]; sensors: ScadaRuntimeSensor[]; actuators: ScadaRuntimeActuator[]; alerts: ScadaRuntimeAlert[] }
export interface ScadaIssue { id: string; severity: "CRITICAL" | "HIGH" | "WARNING" | "INFO"; title: string; root_cause: string; affected_entities: string[]; current_state: string; timestamp: DateTime | null; suggested_action: string; device_id: PublicId | null; sensor_id: PublicId | null; actuator_id: PublicId | null }
export interface ScadaUnplacedEntity { entity_type: ScadaEntityType; entity_id: PublicId; name: string; code: string; parent_device_id?: PublicId | null; suggested_symbol_type: string; reason: string }
export interface ScadaSummary { active_devices_total: number; connected_devices: number; waiting_devices: number; disconnected_devices: number; unknown_connectivity_devices: number; disabled_devices: number; active_sensors_total: number; fresh_sensors: number; fresh_valid_sensors: number; fresh_invalid_sensors: number; stale_sensors: number; no_data_sensors: number; disabled_sensors: number; active_actuators_total: number; actuators_on: number; actuators_off: number; actuators_out_of_sync: number; commands_pending: number; commands_failed: number; commands_timeout: number; disabled_actuators: number; open_alerts: number; critical_alerts: number; warning_alerts: number; unplaced_entities: number }
export interface ScadaRuntimeResponse { aquaponics_system: { id: PublicId; code: string; name: string; status: string }; dashboard: ScadaDashboardInfo; layout: ScadaLayout; inventory: ScadaInventory; runtime: ScadaRuntimeState; summary: ScadaSummary; issues: ScadaIssue[]; unplaced_entities: ScadaUnplacedEntity[]; updated_at: DateTime }
export interface ScadaLayoutMutationResponse { dashboard: ScadaDashboardInfo; layout: ScadaLayout; warnings: string[] }
export interface MqttDeviceTopics { telemetry: string; status: string; command: string }
export interface MqttDeviceSensor { id: PublicId; sensor_code: string; sensor_model_code: string; name: string; unit: string; is_enabled: boolean; status: SensorStatus }
export interface MqttDeviceActuator { id: PublicId; code: string; name: string; actuator_model_code: string | null; is_enabled: boolean }
export interface MqttDevice { id: PublicId; code: string; name: string; is_enabled: boolean; status: DeviceStatus; location: string | null; topics: MqttDeviceTopics; sensors: MqttDeviceSensor[]; actuators: MqttDeviceActuator[] }
export interface MqttExport { exported_at: DateTime; aquaponics_system: { id: PublicId; code: string; name: string }; mqtt: { host: string; port: number; authentication: boolean; tls: boolean }; devices: MqttDevice[] }
export interface MessageResponse { message: string }


export interface RoleSummary { id: Id; code: string; name: string; description: string | null; is_system: boolean; enabled: boolean }
export interface ManagedUserCreate { username: string; full_name: string; email: string; phone_number: string; address?: string; role_id?: Id | null; password: string; confirm_password: string; must_change_password?: boolean }
export interface ManagedUserUpdate { full_name?: string | null; email?: string | null; phone_number?: string | null; address?: string | null; role_id?: Id | null }
export interface ManagedPasswordUpdate { new_password: string; confirm_password: string; invalidate_sessions?: boolean; must_change_password?: boolean }
export interface AccountLifecycleRequest { reason?: string | null }
export interface SystemLifecycleRequest { reason?: string | null }
export interface NotificationRiskPolicy { risk_level: RiskLevel; telegram_enabled: boolean; notify_on_open: boolean; notify_on_escalation: boolean; notify_on_recovery: boolean; notify_on_resolved: boolean; reminder_enabled: boolean; initial_reminder_seconds: number; repeat_interval_seconds: number; max_reminders: number; stop_reminders_on_ack: boolean }
export interface AlertDeliveryRecipient { id: Id; system_id: PublicId; name: string; telegram_chat_id: string; enabled: boolean; created_at: DateTime; updated_at: DateTime }
export interface AlertDeliverySettings { enabled: boolean; in_app_enabled: boolean; telegram_enabled: boolean; notify_alert_opened: boolean; notify_alert_resolved: boolean; notify_alert_recovered: boolean; notify_alert_escalated: boolean; notify_alert_reminder: boolean; reminder_interval_minutes: number | null; minimum_business_risk_level: RiskLevel; risk_extreme_enabled: boolean; risk_very_high_enabled: boolean; risk_high_enabled: boolean; risk_medium_enabled: boolean; risk_low_medium_enabled: boolean; risk_low_enabled: boolean; risk_policies: NotificationRiskPolicy[]; telegram_bot_configured: boolean; notification_generation: number; recipients: AlertDeliveryRecipient[] }
export interface AlertDeliveryRecipientInput { name: string; telegram_chat_id: string; enabled?: boolean }
export interface AlertDeliveryRecipientUpdate { name?: string | null; telegram_chat_id?: string | null; enabled?: boolean | null }
export interface AlertDeliveryTestResult { sent: boolean; detail: string }
export interface AlertDeliveryHistoryItem { id: Id; system_id: PublicId; incident_id: Id | null; alert_id: Id | null; event_type: string; risk: RiskLevel | null; channel: string; recipient_id: Id | null; recipient_name: string; status: string; attempt_count: number; skip_reason: string | null; error_code: string | null; error_message: string | null; attempted_at: DateTime | null; sent_at: DateTime | null; created_at: DateTime; reason: string | null }
export interface PublicMonitoringSettings { enabled: boolean; remote_monitoring_available: boolean; public_slug: string | null }
