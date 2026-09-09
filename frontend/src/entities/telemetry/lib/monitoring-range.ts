import type { MonitoringRange } from "@/entities/telemetry/model/project-monitoring"

export const monitoringRanges: ReadonlyArray<{
  value: MonitoringRange
  label: string
  longLabel: string
}> = [
  { value: "1h", label: "1H", longLabel: "1 giờ" },
  { value: "6h", label: "6H", longLabel: "6 giờ" },
  { value: "12h", label: "12H", longLabel: "12 giờ" },
  { value: "24h", label: "24H", longLabel: "24 giờ" },
  { value: "30d", label: "30 ngày", longLabel: "30 ngày" },
]

export function parseMonitoringRange(value: string | null): MonitoringRange {
  return monitoringRanges.some((option) => option.value === value)
    ? (value as MonitoringRange)
    : "24h"
}

export function monitoringRangeLabel(range: MonitoringRange) {
  return monitoringRanges.find((option) => option.value === range)?.longLabel ?? "24 giờ"
}

export function monitoringExpectedInterval(range: MonitoringRange) {
  if (range === "1h") return 60_000
  if (range === "6h") return 5 * 60_000
  if (range === "12h") return 10 * 60_000
  if (range === "24h") return 15 * 60_000
  return 60 * 60_000
}

export function buildMonitoringWindow(range: MonitoringRange) {
  const end = new Date()
  const durationMs: Record<MonitoringRange, number> = {
    "1h": 60 * 60_000,
    "6h": 6 * 60 * 60_000,
    "12h": 12 * 60 * 60_000,
    "24h": 24 * 60 * 60_000,
    "30d": 30 * 24 * 60 * 60_000,
  }
  return { start: new Date(end.getTime() - durationMs[range]), end }
}
