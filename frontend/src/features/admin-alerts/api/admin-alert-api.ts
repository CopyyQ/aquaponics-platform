import { httpClient } from "@/shared/api/http-client"
import type { AdminAlert, AdminAlertList } from "@/features/admin-alerts/model/types"

export const adminAlertApi = {
  list: async (severity: string, status: string, unacknowledged: boolean) => (await httpClient.get<AdminAlertList>("/admin/alerts", { params: { severity: severity === "ALL" ? undefined : severity, status: status === "ALL" ? undefined : status, unacknowledged, page: 1, page_size: 50 } })).data,
  get: async (id: number) => (await httpClient.get<AdminAlert>(`/admin/alerts/${id}`)).data,
  acknowledge: async (id: number) => (await httpClient.patch<AdminAlert>(`/admin/alerts/${id}/acknowledge`)).data,
  resolve: async ({ id, resolutionNote }: { id: number; resolutionNote: string }) =>
    (await httpClient.patch<AdminAlert>(`/admin/alerts/${id}/resolve`, { resolution_note: resolutionNote })).data,
}
