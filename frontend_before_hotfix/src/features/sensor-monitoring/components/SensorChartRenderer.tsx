import type { TelemetryPoint } from "@/entities/telemetry/model/types"
import { getSensorChart } from "@/features/sensor-monitoring/model/sensorChartRegistry"

export function SensorChartRenderer({ modelCode, data, unit, safeMin, safeMax, lastUpdatedAt, rangeLabel, expectedIntervalMs }: { modelCode?: string; data: TelemetryPoint[]; unit?: string; safeMin?: number | null; safeMax?: number | null; lastUpdatedAt?: string | null; rangeLabel?: string; expectedIntervalMs?: number }) {
  const Chart = getSensorChart(modelCode)
  return <Chart data={data} unit={unit} safeMin={safeMin} safeMax={safeMax} lastUpdatedAt={lastUpdatedAt} currentValue={data.at(-1)?.value} status={data.length ? "normal" : "no-data"} rangeLabel={rangeLabel} expectedIntervalMs={expectedIntervalMs} />
}
