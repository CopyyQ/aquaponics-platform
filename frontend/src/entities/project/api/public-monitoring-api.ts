import type { MonitoringDevice, MonitoringRange, ProjectMonitoringSeries, ProjectMonitoringSummary } from "@/entities/telemetry/model/project-monitoring"
import { httpClient } from "@/shared/api/http-client"

export interface PublicOverview {
  project: { code: string; name: string; location: string | null }
  health: { status: string; label: string; reasons: Array<{ message: string }> }
  summary: ProjectMonitoringSummary
  devices: MonitoringDevice[]
  sensors: Array<{ id: number; code: string; name: string; device_code: string; unit: string; connection_status: string; latest: { value: number; recorded_at: string; quality: string } | null }>
  energy: null | {
    device: { code: string; name: string; connectivity: string; last_received_at: string | null }
    measurements: Record<string, { model_code: string; name: string; unit: string; display_value: number | null; freshness: string; quality: string; recorded_at: string | null }>
    energy_consumption: { last_1h_wh: number | null; last_6h_wh: number | null; last_12h_wh: number | null; last_24h_wh: number | null; month_to_date_wh: number | null }
  }
  alerts: Array<{ severity: string; status: string; message: string; started_at: string }>
  updated_at: string
}

export interface PublicPowerSeries {
  range: MonitoringRange
  points: Array<{ bucket_time: string; avg_value: number }>
}

export const publicMonitoringApi = {
  overview: async () => (await httpClient.get<PublicOverview>("/public-monitoring/overview")).data,
  telemetrySeries: async (range: MonitoringRange) => (await httpClient.get<ProjectMonitoringSeries>("/public-monitoring/telemetry-series", { params: { range } })).data,
  powerSeries: async (deviceCode: string, range: MonitoringRange) => (await httpClient.get<PublicPowerSeries>("/public-monitoring/energy/power-series", { params: { device_code: deviceCode, range } })).data,
}
