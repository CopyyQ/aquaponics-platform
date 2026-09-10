import { buildMonitoringWindow, monitoringRangeLabel } from "@/entities/telemetry/lib/monitoring-range"
import type { MonitoringRange } from "@/entities/telemetry/model/project-monitoring"

export type TelemetryRange = MonitoringRange
export const telemetryRangeLabels: Record<TelemetryRange, string> = {
  "1h": monitoringRangeLabel("1h"),
  "6h": monitoringRangeLabel("6h"),
  "12h": monitoringRangeLabel("12h"),
  "24h": monitoringRangeLabel("24h"),
  "30d": monitoringRangeLabel("30d"),
}
export const buildTelemetryWindow = buildMonitoringWindow

export function getTelemetryStatus(value: number | null, lower?: number | null, upper?: number | null, offline = false) {
  if (offline) return "offline" as const
  if (value === null) return "no-data" as const
  if ((lower !== null && lower !== undefined && value < lower) || (upper !== null && upper !== undefined && value > upper)) return "warning" as const
  return "normal" as const
}

export function formatTelemetryValue(value: number | null, unit?: string, digits = 2) {
  if (value === null) return "Chưa có dữ liệu"
  const formatted = new Intl.NumberFormat("en-US", { maximumFractionDigits: digits, useGrouping: false }).format(value)
  return unit ? `${formatted} ${unit}` : formatted
}

export function getTelemetrySummary<T extends { value: number }>(points: T[]) {
  if (!points.length) return { min: null, max: null, average: null, count: 0 }
  const values = points.map((point) => point.value)
  return { min: Math.min(...values), max: Math.max(...values), average: values.reduce((sum, value) => sum + value, 0) / values.length, count: values.length }
}
