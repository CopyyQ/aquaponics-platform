export interface LatestTelemetry {
  sensor_id: number
  sensor_code: string
  sensor_name: string
  device_id: number
  device_name: string
  unit: string
  value: number | null
  recorded_at: string | null
}

export interface TelemetryPoint {
  timestamp: string
  value: number
  min_value?: number
  max_value?: number
  record_count?: number
  resolution?: "RAW" | "HOUR" | "DAY"
}

export interface StatusCount {
  total: number
  online: number
  offline: number
  waiting: number
  disabled: number
}

export interface OverviewData {
  devices: StatusCount
  sensors: StatusCount
  open_alerts: number
  latest_received_at: string | null
  latest_telemetry: LatestTelemetry[]
  recent_alerts: import("@/entities/alert/model/types").Alert[]
}
