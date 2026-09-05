import { httpClient } from "@/shared/api/http-client";
import type { MonitoringRange } from "@/entities/telemetry/model/project-monitoring";
import type { EnergyOverview, EnergyPowerSeries } from "@/entities/energy-monitor/model/types";

export const energyMonitorApi = {
  overview: async (projectId: number, deviceId: number) =>
    (await httpClient.get<EnergyOverview>(`/projects/${projectId}/devices/${deviceId}/energy-overview`)).data,
  powerSeries: async (projectId: number, deviceId: number, range: MonitoringRange) =>
    (await httpClient.get<EnergyPowerSeries>(`/projects/${projectId}/devices/${deviceId}/energy-power-series`, { params: { range } })).data,
};
