import { electricalQualityLabel } from "@/entities/actuator/lib/actuator-electrical"
import type { MonitoringActuator, MonitoringActuatorStatistics } from "@/entities/telemetry/model/project-monitoring"
import { formatSensorValue } from "@/entities/sensor/lib/format-sensor-value"
import { formatDateTime } from "@/shared/lib/date"

function formatDuration(seconds: number | null | undefined) {
  if (seconds == null || Number.isNaN(seconds)) return "—"
  const hours = Math.floor(seconds / 3600)
  const minutes = Math.floor((seconds % 3600) / 60)
  return hours ? `${hours} giờ ${minutes} phút` : `${minutes} phút`
}

function electricalValue(metric: MonitoringActuator["electrical"]["voltage"]) {
  if (!metric.configured) return { value: "Chưa cấu hình", note: null }
  if (metric.value == null || metric.freshness === "NO_DATA") return { value: "Không có dữ liệu", note: null }
  if (metric.freshness === "STALE") return { value: formatSensorValue(metric.value, metric.unit), note: "Dữ liệu cũ" }
  if (metric.quality !== "VALID") return { value: formatSensorValue(metric.value, metric.unit), note: electricalQualityLabel(metric.quality) }
  if (metric.threshold_status === "BELOW_RANGE" || metric.threshold_status === "ABOVE_RANGE") return { value: formatSensorValue(metric.value, metric.unit), note: "Ngoài ngưỡng" }
  return { value: formatSensorValue(metric.value, metric.unit), note: "Mới" }
}

export function ActuatorHistoryStatistics({ statistics, electrical }: { statistics: MonitoringActuatorStatistics | null | undefined; electrical: MonitoringActuator["electrical"] }) {
  const voltage = electricalValue(electrical.voltage)
  const current = electricalValue(electrical.current)
  const items = [
    ["Tổng thời gian bật", formatDuration(statistics?.on_duration_seconds)],
    ["Tổng thời gian tắt", formatDuration(statistics?.off_duration_seconds)],
    ["Thời gian không xác định", formatDuration(statistics?.unknown_duration_seconds)],
    ["Tỷ lệ hoạt động", statistics?.on_percentage == null ? "—" : `${statistics.on_percentage.toLocaleString("vi-VN", { maximumFractionDigits: 1 })}%`],
    ["Số lần bật", statistics?.on_count?.toLocaleString("vi-VN") ?? "—"],
    ["Số lần tắt", statistics?.off_count?.toLocaleString("vi-VN") ?? "—"],
    ["Điện áp hiện tại", voltage.value, voltage.note],
    ["Dòng điện hiện tại", current.value, current.note],
    ["Thay đổi gần nhất", statistics?.last_changed_at ? formatDateTime(statistics.last_changed_at) : "—"],
  ] as const
  return <section className="space-y-3" aria-labelledby="actuator-statistics-title">
    <h3 id="actuator-statistics-title" className="text-sm font-semibold text-foreground">Thống kê hoạt động</h3>
    <dl className="grid overflow-hidden rounded-lg border bg-card sm:grid-cols-2 xl:grid-cols-3">
      {items.map(([label, value, note]) => <div key={label} className="border-b p-4 last:border-b-0 sm:[&:nth-last-child(-n+2)]:border-b-0 xl:[&:nth-last-child(-n+3)]:border-b-0"><dt className="text-xs font-medium text-muted-foreground">{label}</dt><dd className="mt-2 text-lg font-bold tabular-nums">{value}</dd>{note ? <p className="mt-1 text-xs text-muted-foreground">{note}</p> : null}</div>)}
    </dl>
  </section>
}
