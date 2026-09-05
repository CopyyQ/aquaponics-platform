import type { ParsedTimeSeriesPoint } from "@/shared/charts/time-series/time-series.types"

export interface TimeSeriesScale {
  width: number
  height: number
  plotLeft: number
  plotRight: number
  plotTop: number
  plotBottom: number
  min: number
  max: number
  toX: (timestamp: number) => number
  toY: (value: number) => number
}

export function createTimeSeriesScale(points: ParsedTimeSeriesPoint[], width: number, safeMin?: number | null, safeMax?: number | null): TimeSeriesScale {
  const compact = width < 520
  const height = compact ? 174 : 202
  const plotLeft = compact ? 45 : 56
  const plotRight = width - 10
  const plotTop = 12
  const plotBottom = height - 32
  const thresholds = [safeMin, safeMax].filter((value): value is number => value != null && Number.isFinite(value))
  const values = [...points.map((point) => point.value), ...thresholds]
  const rawMin = Math.min(...values)
  const rawMax = Math.max(...values)
  const margin = rawMax === rawMin ? Math.max(Math.abs(rawMin) * 0.05, 1) : (rawMax - rawMin) * 0.08
  const min = rawMin - margin
  const max = rawMax + margin
  const start = points[0].timestamp
  const end = points.at(-1)?.timestamp ?? start
  return {
    width, height, plotLeft, plotRight, plotTop, plotBottom, min, max,
    toX: (timestamp) => plotLeft + ((timestamp - start) / (end - start || 1)) * (plotRight - plotLeft),
    toY: (value) => plotTop + (1 - (value - min) / (max - min || 1)) * (plotBottom - plotTop),
  }
}
