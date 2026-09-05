import type { Device, DeviceCreateInput } from "@/entities/device/model/types"

export interface Project {
  id: number
  owner_user_id: number
  code: string
  name: string
  location: string | null
  description: string | null
  status: "ACTIVE" | "DISABLED" | "INACTIVE" | "ARCHIVED"
  disabled_at: string | null
  disabled_by_user_id: number | null
  disabled_reason: string | null
  created_at: string
  updated_at: string
}

export interface ProjectDeviceList {
  items: Device[]
  total: number
}

export interface AdminUserProject {
  id: number
  name: string
  code: string
  location: string | null
  status: Project["status"]
  device_count: number
  sensor_count: number
  open_alert_count: number
  latest_telemetry_at: string | null
}

export interface AdminUserProjectList {
  items: AdminUserProject[]
  total: number
}

export type { DeviceCreateInput }

export interface ProjectOverview {
  project: Project
  owner: { id: number; full_name: string; email: string } | null
  member_count: number
  device_count: number
  online_device_count: number
  offline_device_count: number
  sensor_count: number
  offline_sensor_count: number
  open_alert_count: number
  last_telemetry_at: string | null
  critical_issues: Array<{ message: string }>
  devices_summary: Device[]
  health: ProjectHealth
  inventory: ProjectInventory
  alerts: ProjectAlertSummary
  freshness: ProjectFreshness
  attention: ProjectAttention[]
  measurement_groups: ProjectMeasurementGroup[]
  device_health: ProjectDeviceHealth[]
  recent_alerts: ProjectRecentAlert[]
  actuators?: ProjectOverviewActuator[]
  actuator_inventory?: Record<string, number>
}

export interface ProjectOverviewActuator {
  id: number
  name: string
  device_name: string
  connection_status: string
  desired_state: boolean | null
  reported_state: boolean | null
  synchronization_status: string
  command_status: string | null
  last_reported_at: string | null
  latest_command: { status: string; requested_at: string } | null
  electrical: { voltage: ElectricalFeedbackMetric; current: ElectricalFeedbackMetric; configured: boolean; sensor_id: number | null; current_a: number | null; quality: ElectricalFeedbackMetric["quality"]; freshness: ElectricalFeedbackMetric["freshness"]; recorded_at: string | null; received_at: string | null; minimum_running_current_a: number | null; maximum_running_current_a: number | null }
  operational_conclusion: { code: string; label: string; explanation: string }
  active_incident: { id: number; technical_severity: "WARNING" | "CRITICAL"; business_risk_level: string; status: string; rule_name: string; evaluator_type: string; condition_summary: string; started_at: string; duration_seconds: number; evidence: Record<string, unknown> } | null
}

export interface ElectricalFeedbackMetric { configured: boolean; sensor_id: number | null; sensor_code?: string | null; sensor_name?: string | null; sensor_model_code?: string | null; source_device_id?: number | null; source_device_code?: string | null; source_device_name?: string | null; value_key?: string | null; value: number | null; unit: "V" | "A"; quality: "VALID" | "OUT_OF_RANGE" | "INVALID" | "UNVALIDATED" | "NO_DATA"; freshness: "FRESH" | "STALE" | "NO_DATA"; recorded_at: string | null; received_at: string | null; lower_threshold: number | null; upper_threshold: number | null; threshold_source?: "ACTUATOR_OVERRIDE" | "MODEL_DEFAULT" | "NONE"; threshold_status?: "BELOW_RANGE" | "ABOVE_RANGE" | "IN_RANGE" | "NO_DATA" | "STALE" | "INVALID" | "UNCONFIGURED" }

export type ProjectHealthStatus = "HEALTHY" | "WARNING" | "CRITICAL" | "NO_DATA" | "INACTIVE"
export interface ProjectHealth { status: ProjectHealthStatus; label: string; reasons: Array<{ code: string; severity: string; message: string }> }
export interface ProjectInventory { devices_total: number; devices_enabled: number; devices_online: number; devices_offline: number; devices_waiting: number; sensors_total: number; sensors_enabled: number; sensors_reporting: number; sensors_stale: number; sensors_offline: number; members_total: number }
export interface ProjectAlertSummary { open_total: number; critical_open: number; warning_open: number }
export interface ProjectFreshness { last_received_at: string | null; reporting_sensors: number; expected_sensors: number; coverage_ratio: number }
export interface ProjectAttention { id: string; severity: string; title: string; description: string; device_id: number | null; sensor_id: number | null; last_seen_at: string | null }
export interface ProjectMeasurementGroup { model_code: string; name: string; unit: string; reporting_sensors: number; expected_sensors: number; latest_value: number | null; minimum_value: number | null; maximum_value: number | null; latest_at: string | null; stale: boolean; counter: boolean; sensor_id: number | null; device_id: number | null; quality?: "VALID" | "OUT_OF_RANGE" | "INVALID" | "UNVALIDATED" | "NO_DATA"; quality_reason?: string | null; engineering_min?: number | null; engineering_max?: number | null }
export interface ProjectDeviceHealth { id: number; code: string; name: string; status: Device["status"]; is_enabled: boolean; last_seen_at: string | null; sensor_count: number; reporting_sensor_count: number; stale_sensor_count: number; offline_sensor_count: number; open_alert_count: number }
export interface ProjectRecentAlert { id: number; sensor_id: number; sensor_name: string; device_id: number; device_name: string; severity: string; status: string; message: string; trigger_value: number | null; condition_active: boolean; normalized_at: string | null; resolved_by_user_id: number | null; started_at: string }

export interface ProjectDeviceConfig {
  exported_at: string
  project: {
    id: number
    code: string
    name: string
    owner: { id: number; full_name: string }
  }
  mqtt: {
    host: string
    port: number
    authentication: boolean
    tls: boolean
  }
  devices: Array<{
    id: number
    code: string
    name: string
    is_enabled: boolean
    status: Device["status"]
    location: string | null
    topics: { telemetry: string; status: string }
    sensors: Array<{
      id: number
      sensor_code: string
      sensor_model_code: string
      name: string
      unit: string
      is_enabled: boolean
      status: Device["status"]
      lower_threshold: number | null
      upper_threshold: number | null
    }>
    actuators: Array<{
      id: number
      code: string
      name: string
      actuator_model_code: string | null
      is_enabled: boolean
      feedbacks: Array<{
        role: "SUPPLY_VOLTAGE" | "RUNNING_CURRENT"
        sensor_id: number
        sensor_code: string
        sensor_model_code: string
        value_key: string
        unit: string
        data_type: "FLOAT"
        lower_threshold: number | null
        upper_threshold: number | null
        mqtt: { topic: string; payload: Record<string, unknown> }
      }>
    }>
  }>
  summary: {
    device_count: number
    enabled_device_count: number
    disabled_device_count: number
    sensor_count: number
    enabled_sensor_count: number
    disabled_sensor_count: number
    actuator_count: number
    enabled_actuator_count: number
    feedback_count: number
  }
}
