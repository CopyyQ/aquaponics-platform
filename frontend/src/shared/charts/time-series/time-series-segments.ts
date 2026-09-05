import type { MissingDataGap, ParsedTimeSeriesPoint, SegmentedTimeSeries, ThresholdSegment, TimeSeriesDatum, TimeSeriesTone } from "@/shared/charts/time-series/time-series.types"

function median(values: number[]): number | null {
  if (!values.length) return null
  const sorted = [...values].sort((left, right) => left - right)
  const middle = Math.floor(sorted.length / 2)
  return sorted.length % 2 ? sorted[middle] : (sorted[middle - 1] + sorted[middle]) / 2
}

export function isValueInRange(value: number, safeMin?: number | null, safeMax?: number | null) {
  return (safeMin == null || value >= safeMin) && (safeMax == null || value <= safeMax)
}

function intersection(left: ParsedTimeSeriesPoint, right: ParsedTimeSeriesPoint, threshold: number) {
  const ratio = (threshold - left.value) / (right.value - left.value)
  return { timestamp: left.timestamp + (right.timestamp - left.timestamp) * ratio, value: threshold }
}

function splitPair(left: ParsedTimeSeriesPoint, right: ParsedTimeSeriesPoint, safeMin?: number | null, safeMax?: number | null) {
  const cuts = [left]
  for (const threshold of [safeMin, safeMax]) {
    if (threshold == null || left.value === right.value) continue
    if (threshold > Math.min(left.value, right.value) && threshold < Math.max(left.value, right.value)) cuts.push(intersection(left, right, threshold))
  }
  cuts.push(right)
  const sortedCuts = [...cuts].sort((first, second) => first.timestamp - second.timestamp)
  return sortedCuts.slice(0, -1).map((start, index) => {
    const end = sortedCuts[index + 1]
    const midpoint = (start.value + end.value) / 2
    const tone: TimeSeriesTone = isValueInRange(midpoint, safeMin, safeMax) ? "in-range" : "out-of-range"
    return { tone, points: [start, end] }
  })
}

export function buildThresholdSegments(data: TimeSeriesDatum[], options: { safeMin?: number | null; safeMax?: number | null; expectedIntervalMs?: number | null; gapMultiplier?: number } = {}): SegmentedTimeSeries {
  const points = data.map((item) => ({ timestamp: new Date(item.timestamp).getTime(), value: Number(item.value) })).filter((point) => Number.isFinite(point.timestamp) && Number.isFinite(point.value)).sort((left, right) => left.timestamp - right.timestamp)
  if (!points.length) return { points, segments: [], gaps: [] }
  if (points.length === 1) return { points, gaps: [], segments: [{ id: `point-${points[0].timestamp}`, tone: isValueInRange(points[0].value, options.safeMin, options.safeMax) ? "in-range" : "out-of-range", points }] }

  const intervals = points.slice(1).map((point, index) => point.timestamp - points[index].timestamp).filter((value) => value > 0)
  const expected = options.expectedIntervalMs && options.expectedIntervalMs > 0 ? options.expectedIntervalMs : median(intervals)
  const gapThreshold = expected === null ? null : expected * Math.max(1.1, options.gapMultiplier ?? 2.5)
  const segments: ThresholdSegment[] = []
  const gaps: MissingDataGap[] = []

  for (let index = 1; index < points.length; index += 1) {
    const left = points[index - 1]
    const right = points[index]
    const durationMs = right.timestamp - left.timestamp
    if (gapThreshold !== null && durationMs > gapThreshold) {
      gaps.push({ id: `${left.timestamp}-${right.timestamp}`, start: left, end: right, durationMs })
      continue
    }
    splitPair(left, right, options.safeMin, options.safeMax).forEach((segment, segmentIndex) => segments.push({ ...segment, id: `${index}-${segmentIndex}-${segment.tone}` }))
  }
  return { points, segments, gaps }
}
