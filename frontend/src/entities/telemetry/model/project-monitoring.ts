import type { ConnectionStatus } from "@/entities/device/model/types"
import type { ProjectOverviewActuator } from "@/entities/project/model/types"
import type { ProjectAttention, ProjectDeviceHealth, ProjectHealth, ProjectInventory, ProjectMeasurementGroup, ProjectRecentAlert, ProjectAlertSummary, ProjectFreshness } from "@/entities/project/model/types"
import type { TelemetryPoint } from "@/entities/telemetry/model/types"

export type MonitoringRange = "1h" | "6h" | "12h" | "24h" | "1m"

export interface MonitoringLatestValue {
  value: number
  recorded_at: string
  quality?: "VALID" | "OUT_OF_RANGE" | "INVALID" | "UNVALIDATED" | "NO_DATA"
  quality_reason?: string | null
  engineering_min?: number | null
  engineering_max?: number | null
  freshness?: "FRESH" | "STALE" | "NO_DATA"
}

export interface MonitoringSensor {
  id: number
  code: string
  name: string
  unit: string
  is_enabled: boolean
  connection_status: ConnectionStatus
  data_status: ConnectionStatus
  latest: MonitoringLatestValue | null
  lower_threshold: number | null
  upper_threshold: number | null
  threshold_state: "BELOW" | "NORMAL" | "ABOVE" | "UNCONFIGURED"
  alerts_enabled: boolean
}

export interface MonitoringLatestCommand {
  status: "PENDING" | "PUBLISHED" | "ACKNOWLEDGED" | "FAILED" | "TIMEOUT" | string
  requested_at: string
}

export interface MonitoringActuator {
  id: number
  code: string
  name: string
  actuator_model: string | null
  connection_status: ConnectionStatus
  desired_state: boolean | null
  reported_state: boolean | null
  synchronization_status: "IN_SYNC" | "OUT_OF_SYNC" | "UNKNOWN" | string
  latest_command: MonitoringLatestCommand | null
  last_reported_at: string | null
  electrical: ProjectOverviewActuator["electrical"]
  active_incident: ProjectOverviewActuator["active_incident"]
}

export interface MonitoringDevice {
  id: number
  code: string
  name: string
  is_enabled: boolean
  connection_status: ConnectionStatus
  location: string | null
  last_seen_at: string | null
  sensors: MonitoringSensor[]
  actuators: MonitoringActuator[]
}

export interface ProjectMonitoringLatest {
  project_id: number
  devices: MonitoringDevice[]
}

export interface ProjectMonitoringSummary {
  project_id: number
  health: ProjectHealth
  inventory: ProjectInventory
  alerts: ProjectAlertSummary
  freshness: ProjectFreshness
  attention: ProjectAttention[]
  measurement_groups: ProjectMeasurementGroup[]
  device_health: ProjectDeviceHealth[]
  recent_alerts: ProjectRecentAlert[]
  actuators?: ProjectActuatorHealth[]
  actuator_inventory?: Record<string, number>
}

export interface ProjectActuatorHealth {
  id: number
  device_id: number
  device_name: string
  device_code: string
  code: string
  name: string
  actuator_model: string | null
  is_enabled: boolean
  connection_status: string
  desired_state: boolean | null
  reported_state: boolean | null
  synchronization_status: string
  command_status: string | null
  last_command_at: string | null
  last_ack_at: string | null
  last_reported_at: string | null
}

export interface MonitoringSeriesPoint {
  recorded_at: string
  value: number
}

export interface MonitoringSensorSeries {
  sensor_id: number
  unit: string
  points: MonitoringSeriesPoint[]
  gaps: MonitoringDataGap[]
}

export interface MonitoringDataGap {
  from: string
  to: string
  reason: "NO_DATA" | "DEVICE_OFFLINE" | string
}

export interface ProjectMonitoringSeries {
  project_id: number
  range: MonitoringRange
  resolution: "raw" | "5m" | "10m" | "15m" | "1h" | "1d"
  series: MonitoringSensorSeries[]
}

export type EnergySensorModelCode =
  | "INPUT_VOLTAGE_V"
  | "OUTPUT_VOLTAGE_V"
  | "INPUT_CURRENT_A"
  | "LOAD_CURRENT_A"
  | "POWER_W"
  | "ENERGY_TOTAL_WH"

export interface EnergyLatestValue {
  sensor_id: number
  sensor_code: string
  sensor_enabled: boolean
  value: number | null
  unit: string
  recorded_at: string | null
  measurement_semantics: "GAUGE" | "COUNTER"
}

export interface EnergyMonitoringDevice {
  id: number
  code: string
  name: string
  enabled: boolean
  status: ConnectionStatus
  last_seen_at: string | null
  location: string | null
  template: {
    id: number
    code: string
    name: string
    nominal_output_voltage_v: number | null
  }
  latest: Partial<Record<EnergySensorModelCode, EnergyLatestValue>>
}

export interface EnergyMonitoringResponse {
  project_id: number
  devices: EnergyMonitoringDevice[]
}

export interface DevicePowerSeries {
  project_id: number
  device_id: number
  range: MonitoringRange
  resolution: string
  timezone: "UTC"
  unit: "W"
  points: Array<{
    bucket_time: string
    avg_value: number
    min_value: number
    max_value: number
    reading_count: number
  }>
}

export interface MonitoringActuatorHistoryPoint {
  recorded_at: string
  state: boolean
}

export interface MonitoringActuatorHistoryGap {
  from: string
  to: string
  reason: "DEVICE_OFFLINE" | string
}

export interface MonitoringActuatorStatistics {
  on_duration_seconds: number
  off_duration_seconds: number
  unknown_duration_seconds: number
  on_percentage: number | null
  on_count: number
  off_count: number
  last_changed_at: string | null
}

export interface MonitoringActuatorHistory {
  actuator_id: number
  points: MonitoringActuatorHistoryPoint[]
  gaps: MonitoringActuatorHistoryGap[]
  statistics: MonitoringActuatorStatistics
}

export interface ProjectMonitoringActuatorHistory {
  project_id: number
  device_id: number
  range: MonitoringRange
  items: MonitoringActuatorHistory[]
}

export interface ProjectMonitoringItem {
  device: MonitoringDevice
  sensor: MonitoringSensor
  history: TelemetryPoint[]
  currentValue: number | null
  average: number | null
  min: number | null
  max: number | null
  updatedAt: string | null
}
