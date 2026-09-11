export interface TimeSeriesDatum {
  timestamp: string
  value: number
}

export interface ParsedTimeSeriesPoint {
  timestamp: number
  value: number
}

export type TimeSeriesTone = "in-range" | "out-of-range"

export interface ThresholdSegment {
  id: string
  tone: TimeSeriesTone
  points: ParsedTimeSeriesPoint[]
}

export interface MissingDataGap {
  id: string
  start: ParsedTimeSeriesPoint
  end: ParsedTimeSeriesPoint
  durationMs: number
}

export interface SegmentedTimeSeries {
  points: ParsedTimeSeriesPoint[]
  segments: ThresholdSegment[]
  gaps: MissingDataGap[]
}

export interface TimeSeriesChartProps {
  data: TimeSeriesDatum[]
  unit?: string
  title?: string
  currentValue?: number | null
  safeMin?: number | null
  safeMax?: number | null
  status?: "normal" | "warning" | "critical" | "stale" | "offline" | "no-data"
  rangeLabel?: string
  lastUpdatedAt?: string | null
  variant?: "line" | "smooth" | "step" | "area" | "state"
  expectedIntervalMs?: number | null
  gapMultiplier?: number
}
