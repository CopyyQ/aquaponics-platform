import { httpClient } from "@/shared/api/http-client"
import type {
  MonitoringRange,
  ProjectMonitoringActuatorHistory,
  ProjectMonitoringLatest,
  ProjectMonitoringSeries,
  ProjectMonitoringSummary,
  DevicePowerSeries,
} from "@/entities/telemetry/model/project-monitoring"
import type { LatestTelemetry, OverviewData, TelemetryPoint } from "@/entities/telemetry/model/types"

export const telemetryApi = {
  overview: async () => (await httpClient.get<OverviewData>("/overview")).data,
  latest: async () => (await httpClient.get<LatestTelemetry[]>("/telemetry/latest")).data,
  projectMonitoringLatest: async (projectId: number) => (
    await httpClient.get<ProjectMonitoringLatest>(`/projects/${projectId}/monitoring/inventory`)
  ).data,
  projectMonitoringSummary: async (projectId: number) => (
    await httpClient.get<ProjectMonitoringSummary>(`/projects/${projectId}/monitoring/summary`)
  ).data,
  projectMonitoringSeries: async (projectId: number, range: MonitoringRange) => (
    await httpClient.get<ProjectMonitoringSeries>(`/projects/${projectId}/monitoring/series`, {
      params: { range },
    })
  ).data,
  devicePowerSeries: async (projectId: number, deviceId: number, range: MonitoringRange) => (
    await httpClient.get<DevicePowerSeries>(
      `/projects/${projectId}/devices/${deviceId}/monitoring/power-series`,
      { params: { range } },
    )
  ).data,
  deviceMonitoringSensorSeries: async (
    projectId: number,
    deviceId: number,
    range: MonitoringRange,
  ) => (
    await httpClient.get<ProjectMonitoringSeries>(
      `/projects/${projectId}/devices/${deviceId}/monitoring/sensor-series`,
      { params: { range } },
    )
  ).data,
  deviceMonitoringActuatorHistory: async (
    projectId: number,
    deviceId: number,
    range: MonitoringRange,
  ) => (
    await httpClient.get<ProjectMonitoringActuatorHistory>(
      `/projects/${projectId}/devices/${deviceId}/monitoring/actuator-history`,
      { params: { range } },
    )
  ).data,
  history: async (sensorId: number, start: string, end: string, resolution = "AUTO") => (await httpClient.get<TelemetryPoint[]>(`/telemetry/sensors/${sensorId}/history`, { params: { start, end, resolution } })).data,
  projectHistory: async (projectId: number, sensorId: number, start: string, end: string, resolution = "RAW") => (
    await httpClient.get<{ items: TelemetryPoint[] }>(`/projects/${projectId}/sensors/${sensorId}/telemetry`, { params: { start, end, resolution } })
  ).data.items,
  exportUrl: (sensorId: number, start: string, end: string) => `/telemetry/export?sensor_id=${sensorId}&start=${encodeURIComponent(start)}&end=${encodeURIComponent(end)}`,
}
