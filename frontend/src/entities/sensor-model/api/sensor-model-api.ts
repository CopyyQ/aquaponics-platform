import { httpClient } from "@/shared/api/http-client";
import type { SensorModel } from "@/entities/sensor-model/model/types";

export interface SensorModelCreateInput {
  code: string;
  name: string;
  unit: string;
  description?: string | null;
  value_type?: string;
  chart_type?: string;
  is_active?: boolean;
  default_lower_threshold?: number | null;
  default_upper_threshold?: number | null;
}

export const sensorModelApi = {
  list: async () =>
    (await httpClient.get<SensorModel[]>("/admin/sensor-models")).data,
  create: async (payload: SensorModelCreateInput) =>
    (await httpClient.post<SensorModel>("/admin/sensor-models", payload)).data,
  update: async (id: number, payload: Partial<SensorModel>) =>
    (await httpClient.patch<SensorModel>(`/admin/sensor-models/${id}`, payload))
      .data,
  remove: async (id: number): Promise<void> => {
    await httpClient.delete(`/admin/sensor-models/${id}`);
  },
};
