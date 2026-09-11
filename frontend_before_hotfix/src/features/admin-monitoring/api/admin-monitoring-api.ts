import { httpClient } from "@/shared/api/http-client"
import type { MonitoringFilters, MonitoringResponse } from "@/features/admin-monitoring/model/types"

export const adminMonitoringApi = {
  projects: async (filters: MonitoringFilters) => (await httpClient.get<MonitoringResponse>("/admin/monitoring/projects", { params: { ...filters, health_status: filters.health_status === "ALL" ? undefined : filters.health_status, device_status: filters.device_status === "ALL" ? undefined : filters.device_status } })).data,
}
