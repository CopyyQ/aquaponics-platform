export type AlertStatus = "PENDING" | "OPEN" | "ACKNOWLEDGED" | "RESOLVED"
export type AlertType = "BELOW_LOWER_THRESHOLD" | "ABOVE_UPPER_THRESHOLD" | "SENSOR_OFFLINE"

export interface Alert {
  id: number
  sensor_id: number
  alert_type: AlertType
  severity: "WARNING" | "CRITICAL"
  status: AlertStatus
  message: string
  trigger_value: number | null
  started_at: string
  acknowledged_at: string | null
  acknowledged_by: number | null
  condition_active: boolean
  normalized_at: string | null
  resolved_at: string | null
  resolved_by_user_id: number | null
  resolved_by_name: string | null
  resolution_note: string | null
  created_at: string
  updated_at: string
}
