import { monitoringRanges } from "@/entities/telemetry/lib/monitoring-range"
import type { MonitoringRange } from "@/entities/telemetry/model/project-monitoring"
import { ToggleGroup, ToggleGroupItem } from "@/shared/ui/toggle-group"

export function MonitoringRangeSelector({ range, onRangeChange }: {
  range: MonitoringRange
  onRangeChange: (range: MonitoringRange) => void
}) {
  return <ToggleGroup
    type="single"
    value={range}
    variant="outline"
    aria-label="Chọn khoảng thời gian biểu đồ"
    className="grid w-full grid-cols-5 sm:w-auto"
    onValueChange={(value) => {
      const nextRange = monitoringRanges.find((option) => option.value === value)?.value
      if (nextRange) onRangeChange(nextRange)
    }}
  >
    {monitoringRanges.map((option) => <ToggleGroupItem
      key={option.value}
      value={option.value}
      aria-label={`Hiển thị dữ liệu ${option.longLabel} gần nhất`}
      aria-pressed={range === option.value}
      className="w-full px-2 sm:w-auto sm:px-3"
    >{option.label}</ToggleGroupItem>)}
  </ToggleGroup>
}
