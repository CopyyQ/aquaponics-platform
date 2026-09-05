export type HealthStatus = "CRITICAL" | "WARNING" | "ATTENTION" | "HEALTHY"
export type MonitoringSort = "risk_score" | "alerts" | "online_ratio" | "last_telemetry_at" | "project_name" | "customer_name" | "last_event_at"

export interface MonitoringProject {
  id: number
  rank: number
  code: string
  name: string
  location: string | null
  project_status: string
  owner_user_id: number
  customer_name: string
  access_role: "ADMIN" | "OWNER" | "VIEWER"
  risk_score: number
  health_status: HealthStatus
  critical_alert_count: number
  warning_alert_count: number
  offline_device_count: number
  online_device_count: number
  device_count: number
  abnormal_sensor_count: number
  offline_sensor_count: number
  online_sensor_count: number
  out_of_range_sensor_count: number
  open_alert_count: number
  sensor_count: number
  last_telemetry_at: string | null
  last_event_at: string
  stale: boolean
}

export interface MonitoringResponse {
  items: MonitoringProject[]
  total: number
  page: number
  page_size: number
  updated_at: string
}

export interface MonitoringFilters {
  q: string
  health_status: string
  device_status: string
  stale_only: boolean
  sort_by: MonitoringSort
  sort_order: "asc" | "desc"
  page: number
  page_size: number
}
