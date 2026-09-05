import type { TelemetryPoint } from "@/entities/telemetry/model/types"
import { TimeSeriesChart, type TimeSeriesChartProps } from "@/shared/charts/time-series"

export type SensorTelemetryChartProps = Omit<TimeSeriesChartProps, "data"> & { data: TelemetryPoint[] }

export function SensorTelemetryChart(props: SensorTelemetryChartProps) {
  return <TimeSeriesChart {...props} />
}
