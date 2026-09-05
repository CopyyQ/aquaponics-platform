import { monitoringRanges } from "@/entities/telemetry/lib/monitoring-range"
import type { MonitoringRange } from "@/entities/telemetry/model/project-monitoring"
import { ToggleGroup, ToggleGroupItem } from "@/shared/ui/toggle-group"

export function MonitoringRangeSelector({
  range,
  onRangeChange,
}: {
  range: MonitoringRange
  onRangeChange: (range: MonitoringRange) => void
}) {
  return <div className="max-w-full overflow-x-auto pb-1">
    <ToggleGroup
      type="single"
      value={range}
      variant="outline"
      aria-label="Chọn khoảng thời gian biểu đồ"
      className="w-max min-w-full"
      onValueChange={(value) => {
        const next = monitoringRanges.find((option) => option.value === value)?.value
        if (next) onRangeChange(next)
      }}
    >
      {monitoringRanges.map((option) => <ToggleGroupItem
        key={option.value}
        value={option.value}
        aria-label={`Hiển thị dữ liệu ${option.longLabel} gần nhất`}
        className="min-w-16 flex-1"
      >{option.label}</ToggleGroupItem>)}
    </ToggleGroup>
  </div>
}
