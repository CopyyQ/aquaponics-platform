import type { UserMonitoringFilters, UserMonitoringResponse } from "@/features/user-monitoring/model/types"
import { httpClient } from "@/shared/api/http-client"

export const userMonitoringApi = {
  projects: async (filters: UserMonitoringFilters) => (
    await httpClient.get<UserMonitoringResponse>("/monitoring/projects", {
      params: {
        ...filters,
        health_status: filters.health_status === "ALL" ? undefined : filters.health_status,
        device_status: filters.device_status === "ALL" ? undefined : filters.device_status,
      },
    })
  ).data,
}
