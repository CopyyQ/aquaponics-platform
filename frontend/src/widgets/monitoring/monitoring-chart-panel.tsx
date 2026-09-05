import { Download } from "lucide-react"
import type { Sensor } from "@/entities/sensor/model/types"
import type { LatestTelemetry, TelemetryPoint } from "@/entities/telemetry/model/types"
import { TelemetryChart } from "@/features/telemetry/components/telemetry-chart"
import { getTelemetryStatus, telemetryRangeLabels, type TelemetryRange } from "@/entities/telemetry/lib/telemetry-display"
import { Button } from "@/shared/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/shared/ui/card"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/shared/ui/select"
import { Skeleton } from "@/shared/ui/skeleton"

interface MonitoringChartPanelProps {
  latestItems: LatestTelemetry[]
  selected?: LatestTelemetry
  selectedSensor?: Sensor
  history?: TelemetryPoint[]
  isLoading: boolean
  range: TelemetryRange
  onRangeChange: (range: TelemetryRange) => void
  onSensorChange: (sensorId: number) => void
  onExportCsv: () => void
}

export function MonitoringChartPanel({ latestItems, selected, selectedSensor, history, isLoading, range, onRangeChange, onSensorChange, onExportCsv }: MonitoringChartPanelProps) {
  const status = getTelemetryStatus(selected?.value ?? null, selectedSensor?.lower_threshold, selectedSensor?.upper_threshold, selectedSensor?.status === "OFFLINE")

  return <Card className="overflow-hidden shadow-none">
    <CardHeader className="flex-col gap-4 border-b bg-card sm:flex-row sm:items-center sm:justify-between">
      <div>
        <CardTitle className="text-xl">{selected?.sensor_name ?? "Biểu đồ quan trắc"}</CardTitle>
        <CardDescription>{selected ? `${selected.device_name} · ${selected.unit}` : "Chọn cảm biến để xem lịch sử dữ liệu."}</CardDescription>
      </div>
      <div className="flex w-full flex-col gap-2 sm:w-auto sm:flex-row">
        <Select value={String(selected?.sensor_id ?? "")} onValueChange={(value) => onSensorChange(Number(value))}>
          <SelectTrigger className="w-full sm:w-56" aria-label="Chọn cảm biến">
            <SelectValue placeholder="Chọn cảm biến" />
          </SelectTrigger>
          <SelectContent>
            {latestItems.map((item) => <SelectItem key={item.sensor_id} value={String(item.sensor_id)}>{item.sensor_name}</SelectItem>)}
          </SelectContent>
        </Select>
        <Select value={range} onValueChange={(value) => onRangeChange(value as TelemetryRange)}>
          <SelectTrigger className="w-full sm:w-36" aria-label="Chọn khoảng thời gian">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {(Object.keys(telemetryRangeLabels) as TelemetryRange[]).map((key) => <SelectItem key={key} value={key}>{telemetryRangeLabels[key]}</SelectItem>)}
          </SelectContent>
        </Select>
        <Button variant="outline" onClick={onExportCsv} disabled={!selected}>
          <Download /> Xuất CSV
        </Button>
      </div>
    </CardHeader>
    <CardContent className="p-0">
      {isLoading ? <div className="p-5"><Skeleton className="h-96" /></div> : history?.length ? (
        <TelemetryChart
          data={history}
          unit={selected?.unit}
          title={selected?.sensor_name}
          currentValue={selected?.value ?? null}
          safeMin={selectedSensor?.lower_threshold}
          safeMax={selectedSensor?.upper_threshold}
          status={status}
          rangeLabel={telemetryRangeLabels[range]}
          lastUpdatedAt={selected?.recorded_at ?? null}
        />
      ) : <div className="grid h-96 place-items-center p-6 text-center text-sm text-muted-foreground">Chưa có dữ liệu trong khoảng đã chọn.</div>}
    </CardContent>
  </Card>
}
