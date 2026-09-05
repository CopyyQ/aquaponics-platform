import type { LatestTelemetry } from "@/entities/telemetry/model/types"
import { TelemetryValueCard } from "@/features/telemetry/components/telemetry-value-card"

interface LatestTelemetryGridProps {
  items: LatestTelemetry[]
  selectedSensorId?: number
  onSelectSensor: (sensorId: number) => void
}

export function LatestTelemetryGrid({ items, selectedSensorId, onSelectSensor }: LatestTelemetryGridProps) {
  return <section className="flex flex-col gap-4">
    <div>
      <h2 className="text-lg font-semibold">Giá trị cảm biến hiện tại</h2>
      <p className="text-sm text-muted-foreground">Chọn một cảm biến để xem xu hướng theo khoảng thời gian.</p>
    </div>
    <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
      {items.map((item) => (
        <button key={item.sensor_id} type="button" className="rounded-xl text-left focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2" onClick={() => onSelectSensor(item.sensor_id)}>
          <TelemetryValueCard item={item} selected={item.sensor_id === selectedSensorId} />
        </button>
      ))}
    </div>
  </section>
}
