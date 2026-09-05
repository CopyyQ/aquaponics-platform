import type { MonitoringProject, MonitoringResponse } from "@/features/admin-monitoring/model/types"

export type UserMonitoringSort = "risk_score" | "alerts" | "online_ratio" | "last_telemetry_at" | "project_name"

export interface UserMonitoringFilters {
  q: string
  health_status: string
  device_status: string
  has_offline_sensors: boolean | undefined
  has_out_of_range: boolean | undefined
  sort_by: UserMonitoringSort
  sort_order: "asc" | "desc"
  page: number
  page_size: number
}

export type UserMonitoringProject = MonitoringProject
export type UserMonitoringResponse = MonitoringResponse
