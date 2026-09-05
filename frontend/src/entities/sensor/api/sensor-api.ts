import { httpClient } from "@/shared/api/http-client"

import type {
  Sensor,
  SensorCreateInput,
  ThresholdInput,
} from "@/entities/sensor/model/types"

export const sensorApi = {
  list: async (deviceId?: number) =>
    (
      await httpClient.get<Sensor[]>("/sensors", {
        params: {
          device_id: deviceId,
        },
      })
    ).data,

  listByDevice: async (deviceId: number, includeDisabled = false) =>
    (
      await httpClient.get<Sensor[]>(
        `/devices/${deviceId}/sensors`,
        { params: { include_disabled: includeDisabled } },
      )
    ).data,

  get: async (id: number) =>
    (
      await httpClient.get<Sensor>(
        `/sensors/${id}`,
      )
    ).data,

  getInProject: async (projectId: number, deviceId: number, sensorId: number) =>
    (
      await httpClient.get<Sensor>(
        `/projects/${projectId}/devices/${deviceId}/sensors/${sensorId}`,
      )
    ).data,

  create: async (
    deviceId: number,
    payload: SensorCreateInput,
  ) =>
    (
      await httpClient.post<Sensor>(
        `/devices/${deviceId}/sensors`,
        payload,
      )
    ).data,

  createFromModel: async (
    deviceId: number,
    sensorModelId: number,
  ) =>
    (
      await httpClient.post<Sensor>(
        `/devices/${deviceId}/sensors/from-model`,
        {
          sensor_model_id: sensorModelId,
        },
      )
    ).data,

  update: async (
    id: number,
    payload: Partial<Sensor>,
  ) =>
    (
      await httpClient.patch<Sensor>(
        `/sensors/${id}`,
        payload,
      )
    ).data,
  updateInProject: async (projectId: number, deviceId: number, sensorId: number, payload: Partial<Sensor>) =>
    (await httpClient.patch<Sensor>(`/projects/${projectId}/devices/${deviceId}/sensors/${sensorId}`, payload)).data,

  updateThresholds: async (
    id: number,
    payload: ThresholdInput,
  ) =>
    (
      await httpClient.patch<Sensor>(
        `/sensors/${id}/thresholds`,
        payload,
      )
    ).data,

  /**
   * Xóa cảm biến theo endpoint chung.
   * Giữ lại nếu các màn hình khác vẫn đang sử dụng.
   */
  remove: async (id: number): Promise<void> => {
    await httpClient.delete(`/sensors/${id}`)
  },

  /**
   * Xóa cảm biến khỏi đúng thiết bị.
   *
   * Backend phải kiểm tra:
   * - Sensor tồn tại.
   * - Sensor thuộc đúng Device.
   * - Device thuộc Project mà Admin được quản lý.
   * - Thực hiện soft-delete, không xóa Telemetry lịch sử.
   */
disableFromDevice: async (
  deviceId: number,
  sensorId: number,
  reason: string,
): Promise<void> => {
  await httpClient.post(`/devices/${deviceId}/sensors/${sensorId}/disable`, { reason })
},

activateToDevice: async (
  deviceId: number,
  sensorId: number,
): Promise<void> => {
  await httpClient.post(`/devices/${deviceId}/sensors/${sensorId}/activate`)
},

}
