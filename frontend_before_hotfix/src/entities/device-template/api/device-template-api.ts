import { httpClient } from "@/shared/api/http-client"
import type { ActuatorCurrentProfile, DeviceTemplate, DeviceTemplateInput, DeviceTemplateList, TemplateActuator, TemplateActuatorInput, TemplateActuatorUpdate, TemplateSensor, TemplateSensorInput, TemplateSensorUpdate } from "@/entities/device-template/model/types"

export const deviceTemplateApi = {
  list: async (q: string, active: string, page = 1) => (await httpClient.get<DeviceTemplateList>("/admin/device-templates", { params: { q, is_active: active === "ALL" ? undefined : active === "ACTIVE", page, page_size: 20 } })).data,
  create: async (payload: DeviceTemplateInput) => (await httpClient.post<DeviceTemplate>("/admin/device-templates", payload)).data,
  update: async (id: number, payload: Partial<DeviceTemplateInput>) => (await httpClient.patch<DeviceTemplate>(`/admin/device-templates/${id}`, payload)).data,
  addEnergyDefaults: async (id: number) => (await httpClient.post<DeviceTemplate>(`/admin/device-templates/${id}/energy-default-sensors`)).data,
  remove: async (id: number) => httpClient.delete(`/admin/device-templates/${id}`),
  addSensor: async (id: number, payload: TemplateSensorInput) => (await httpClient.post<TemplateSensor>(`/admin/device-templates/${id}/sensors`, payload)).data,
  updateSensor: async (id: number, mappingId: number, payload: TemplateSensorUpdate) => (await httpClient.patch<TemplateSensor>(`/admin/device-templates/${id}/sensors/${mappingId}`, payload)).data,
  removeSensor: async (id: number, mappingId: number) => httpClient.delete(`/admin/device-templates/${id}/sensors/${mappingId}`),
  listActuatorCurrentProfiles: async () => (await httpClient.get<ActuatorCurrentProfile[]>("/admin/device-templates/actuator-current-profiles")).data,
  addActuator: async (id: number, payload: TemplateActuatorInput) =>
    (await httpClient.post<TemplateActuator>(`/admin/device-templates/${id}/actuators`, payload)).data,
  updateActuator: async (id: number, mappingId: number, payload: TemplateActuatorUpdate) =>
    (await httpClient.patch<TemplateActuator>(`/admin/device-templates/${id}/actuators/${mappingId}`, payload)).data,
  removeActuator: async (id: number, mappingId: number) => httpClient.delete(`/admin/device-templates/${id}/actuators/${mappingId}`),
}
