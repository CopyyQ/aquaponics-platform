import { httpClient } from "@/shared/api/http-client"

import type { Device } from "@/entities/device/model/types"
import type {
  DeviceCreateInput,
  AdminUserProjectList,
  Project,
  ProjectDeviceList,
  ProjectOverview,
  ProjectDeviceConfig,
} from "@/entities/project/model/types"

export const projectApi = {
  list: async () =>
    (await httpClient.get<Project[]>("/projects")).data,

  listForUser: async (userId: number) =>
    (
      await httpClient.get<AdminUserProjectList>(
        `/admin/users/${userId}/projects`,
      )
    ).data,

  get: async (projectId: number) =>
    (
      await httpClient.get<Project>(
        `/projects/${projectId}`,
      )
    ).data,

  overview: async (projectId: number) =>
    (
      await httpClient.get<ProjectOverview>(
        `/projects/${projectId}/overview`,
      )
    ).data,

  createForUser: async (
    userId: number,
    payload: {
      code: string
      name: string
      location?: string
      description?: string
    },
  ) =>
    (
      await httpClient.post<Project>(
        `/admin/users/${userId}/projects`,
        payload,
      )
    ).data,

  devices: async (projectId: number, includeDisabled = false) =>
    (
      await httpClient.get<ProjectDeviceList>(
        `/projects/${projectId}/devices`,
        { params: { include_disabled: includeDisabled } },
      )
    ).data,

  exportDeviceConfig: async (projectId: number) =>
    (
      await httpClient.get<ProjectDeviceConfig>(
        `/projects/${projectId}/device-config`,
      )
    ).data,

  createDevice: async (
    projectId: number,
    payload: DeviceCreateInput,
  ) =>
    (
      await httpClient.post<Device>(
        `/projects/${projectId}/devices`,
        payload,
      )
    ).data,

  createDeviceFromTemplate: async (
    projectId: number,
    deviceTemplateId: number,
    details?: { code?: string; name?: string; location?: string; description?: string },
  ) =>
    (
      await httpClient.post<Device>(
        `/projects/${projectId}/devices/from-template`,
        {
          device_template_id: deviceTemplateId,
          ...details,
        },
      )
    ).data,

  /**
   * Xóa mềm thiết bị khỏi Project.
   *
   * Backend phải kiểm tra:
   * - Device thuộc đúng Project.
   * - Người thao tác là Admin đang hoạt động.
   * - Project đang ACTIVE.
   * - Không xóa Telemetry lịch sử.
   */

disableDevice: async (
  projectId: number,
  deviceId: number,
  reason: string,
): Promise<void> => {
  await httpClient.post(`/projects/${projectId}/devices/${deviceId}/disable`, { reason })
},

activateDevice: async (
  projectId: number,
  deviceId: number,
): Promise<void> => {
  await httpClient.post(`/projects/${projectId}/devices/${deviceId}/activate`)
},
  disable: async (
    projectId: number,
    reason: string,
  ) =>
    (
      await httpClient.post<Project>(
        `/projects/${projectId}/disable`,
        { reason },
      )
    ).data,

  activate: async (projectId: number) =>
    (
      await httpClient.post<Project>(
        `/projects/${projectId}/activate`,
      )
    ).data,

}
