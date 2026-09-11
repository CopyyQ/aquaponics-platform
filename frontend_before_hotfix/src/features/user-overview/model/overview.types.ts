import type { UserRole } from "@/entities/user/model/types"
import type { MonitoringProject } from "@/features/admin-monitoring/model/types"

export interface UserOverview {
  summary: {
    total_projects: number
    active_projects: number
    attention_projects: number
    online_devices: number
    offline_devices: number
    online_sensors: number
    offline_sensors: number
    open_alerts: number
    latest_received_at: string | null
  }
  projects: MonitoringProject[]
}

export interface AdminOverview {
  summary: {
    total_customers: number
    total_devices: number
    assigned_devices: number
    unassigned_devices: number
    online_devices: number
    offline_devices: number
    waiting_devices: number
    disabled_devices: number
    total_sensors: number
    online_sensors: number
    offline_sensors: number
    open_alerts: number
    latest_received_at: string | null
  }
  alert_distribution: Record<string, number>
  critical_issues: Array<{ alert_id: number; device_id: number; owner_user_id: number | null; sensor_id: number; message: string; severity: string; started_at: string }>
  customers: Array<{ user_id: number; full_name: string; role: UserRole; device_count: number; sensor_count: number; online_devices: number; online_ratio: number; open_alerts: number; last_received_at: string | null; health_status: string }>
}
