import type { MonitoringRange } from "@/entities/telemetry/model/project-monitoring"
import {
  monitoringRangeLabel,
  monitoringRanges,
  parseMonitoringRange,
} from "@/entities/telemetry/lib/monitoring-range"

export type { MonitoringRange }
export { monitoringRangeLabel, monitoringRanges, parseMonitoringRange }

export function normalizeMonitoringSearchParams(params: URLSearchParams) {
  const next = new URLSearchParams(params)
  if (next.get("tab") === "energy") {
    next.delete("tab")
    next.delete("device")
  }
  return next
}
