import type { Actuator } from "@/entities/actuator/model/types"
import type { ElectricalFeedbackMetric } from "@/entities/project/model/types"
import { formatSensorValue } from "@/entities/sensor/lib/format-sensor-value"
import { Badge } from "@/shared/ui/badge"

const thresholdLabels = {
  BELOW_RANGE: "Thấp hơn ngưỡng",
  ABOVE_RANGE: "Cao hơn ngưỡng",
  IN_RANGE: "Trong ngưỡng",
  NO_DATA: "Không có dữ liệu",
  STALE: "Dữ liệu cũ",
  INVALID: "Không hợp lệ",
  UNCONFIGURED: "Chưa cấu hình",
} as const

export function ActuatorElectricalPanel({ electrical }: { electrical: Actuator["electrical_feedbacks"] }) {
  return <section className="grid gap-3 border-t pt-4" aria-label="Giám sát điện">
    <h3 className="text-sm font-semibold">Giám sát điện</h3>
    <div className="grid gap-3 sm:grid-cols-2">
      <ElectricalFeedbackCard label="Điện áp" unit="V" metric={electrical?.voltage} />
      <ElectricalFeedbackCard label="Dòng điện" unit="A" metric={electrical?.current} />
    </div>
  </section>
}

function ElectricalFeedbackCard({ label, unit, metric }: { label: string; unit: "V" | "A"; metric?: ElectricalFeedbackMetric }) {
  if (!metric?.configured) return <div className="rounded-md border p-3"><p className="font-medium">{label}</p><p className="mt-2 text-sm text-muted-foreground">Chưa cấu hình</p></div>
  const hasReading = metric.freshness !== "NO_DATA" && metric.value !== null
  const thresholdStatus = metric.threshold_status ?? (metric.freshness === "NO_DATA" ? "NO_DATA" : metric.freshness === "STALE" ? "STALE" : "IN_RANGE")
  return <div className="min-w-0 rounded-md border p-3">
    <div className="flex flex-wrap items-center justify-between gap-2"><p className="font-medium">{label}</p><Badge variant={thresholdStatus === "BELOW_RANGE" || thresholdStatus === "ABOVE_RANGE" || thresholdStatus === "INVALID" ? "destructive" : thresholdStatus === "IN_RANGE" ? "success" : "secondary"}>{thresholdLabels[thresholdStatus]}</Badge></div>
    <dl className="mt-3 grid grid-cols-[auto_1fr] gap-x-3 gap-y-1 text-sm">
      <dt className="text-muted-foreground">Giá trị cuối</dt><dd className="text-right font-medium tabular-nums">{hasReading ? formatSensorValue(metric.value, unit) : "Không có dữ liệu"}</dd>
      <dt className="text-muted-foreground">Ngưỡng dưới</dt><dd className="text-right tabular-nums">{metric.lower_threshold === null ? "Chưa cấu hình" : formatSensorValue(metric.lower_threshold, unit)}</dd>
      <dt className="text-muted-foreground">Ngưỡng trên</dt><dd className="text-right tabular-nums">{metric.upper_threshold === null ? "Chưa cấu hình" : formatSensorValue(metric.upper_threshold, unit)}</dd>
    </dl>
    {thresholdStatus === "STALE" ? <p className="mt-2 text-xs text-muted-foreground">Dữ liệu cuối trước khi mất kết nối.</p> : null}
  </div>
}
