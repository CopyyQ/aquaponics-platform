export interface AdminAlert {
  id: number
  alert_type: string
  severity: "WARNING" | "CRITICAL"
  status: import("@/entities/alert/model/types").AlertStatus
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
  project: { id: number; name: string }
  customer: { id: number; full_name: string }
  device: { id: number; name: string; code: string }
  sensor: { id: number; name: string; code: string; unit: string; model_code: string }
  threshold: { lower: number | null; upper: number | null }
  current_value?: number | null
  telemetry_context?: Array<{ value: number; recorded_at: string }>
}

export interface AdminAlertList { items: AdminAlert[]; total: number; page: number; page_size: number }
