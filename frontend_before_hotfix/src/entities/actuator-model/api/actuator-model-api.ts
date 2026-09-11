import { httpClient } from "@/shared/api/http-client"
import type { ActuatorModel, ActuatorModelInput } from "@/entities/actuator-model/model/types"

export const actuatorModelApi = {
  list: async () => (await httpClient.get<ActuatorModel[]>("/admin/actuator-models")).data,
  create: async (payload: ActuatorModelInput) => (await httpClient.post<ActuatorModel>("/admin/actuator-models", payload)).data,
  update: async (id: number, payload: Partial<ActuatorModelInput>) => (await httpClient.patch<ActuatorModel>(`/admin/actuator-models/${id}`, payload)).data,
  disable: async (id: number) => { await httpClient.post(`/admin/actuator-models/${id}/disable`) },
  activate: async (id: number) => { await httpClient.post(`/admin/actuator-models/${id}/activate`) },
}
