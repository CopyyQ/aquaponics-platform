import { httpClient } from "@/shared/api/http-client";
import type {
  Device,
  DeviceOverview,
  MqttDeviceConfig,
} from "@/entities/device/model/types";

export const deviceApi = {
  list: async () => (await httpClient.get<Device[]>("/devices")).data,
  get: async (id: number) =>
    (await httpClient.get<Device>(`/devices/${id}`)).data,
  overview: async (id: number) =>
    (await httpClient.get<DeviceOverview>(`/devices/${id}/overview`)).data,
  update: async (id: number, payload: Partial<Device>) =>
    (await httpClient.patch<Device>(`/devices/${id}`, payload)).data,
  updateInProject: async (
    projectId: number,
    id: number,
    payload: Partial<Device>,
  ) =>
    (
      await httpClient.patch<Device>(
        `/projects/${projectId}/devices/${id}`,
        payload,
      )
    ).data,
  remove: async (id: number) => httpClient.delete(`/devices/${id}`),
  mqttConfig: async (projectId: number, id: number) =>
    (
      await httpClient.get<MqttDeviceConfig>(
        `/projects/${projectId}/devices/${id}/mqtt-connection-config`,
      )
    ).data,
  downloadMqttConfig: async (projectId: number, id: number) => {
    const response = await httpClient.get<Blob>(
      `/projects/${projectId}/devices/${id}/mqtt-connection-config`,
      { responseType: "blob" },
    );
    const contentDisposition = String(
      response.headers["content-disposition"] ?? "",
    );
    const filename =
      contentDisposition.match(/filename="?([^";]+)"?/i)?.[1] ??
      "mqtt-config.json";
    return { blob: response.data, filename };
  },
};
