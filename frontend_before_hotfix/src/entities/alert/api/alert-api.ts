import { httpClient } from "@/shared/api/http-client"
import type { Alert, AlertStatus, AlertType } from "@/entities/alert/model/types"

export const alertApi = {
  list: async (params?: { status?: AlertStatus; alert_type?: AlertType; sensor_id?: number }) => (await httpClient.get<Alert[]>("/alerts", { params })).data,
  projectList: async (projectId: number) => (await httpClient.get<Alert[]>(`/projects/${projectId}/alerts`)).data,
  acknowledge: async (id: number) => (await httpClient.post<Alert>(`/alerts/${id}/acknowledge`)).data,
  resolve: async ({ id, resolutionNote }: { id: number; resolutionNote: string }) =>
    (await httpClient.post<Alert>(`/alerts/${id}/resolve`, { resolution_note: resolutionNote })).data,
}
