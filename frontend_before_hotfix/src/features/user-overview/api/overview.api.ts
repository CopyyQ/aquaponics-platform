import { httpClient } from "@/shared/api/http-client"
import type { Device } from "@/entities/device/model/types"
import type { AdminOverview, UserOverview } from "@/features/user-overview/model/overview.types"

export const overviewApi = {
  me: async () => (await httpClient.get<UserOverview>("/me/overview")).data,
  myDevices: async () => (await httpClient.get<Device[]>("/me/devices")).data,
  admin: async () => (await httpClient.get<AdminOverview>("/admin/overview")).data,
}
