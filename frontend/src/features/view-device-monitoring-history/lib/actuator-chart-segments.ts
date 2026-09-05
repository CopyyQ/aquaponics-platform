import type {
  MonitoringActuatorHistoryGap,
  MonitoringActuatorHistoryPoint,
} from "@/entities/telemetry/model/project-monitoring"

export interface ActuatorChartSegment {
  from: MonitoringActuatorHistoryPoint
  to: MonitoringActuatorHistoryPoint
}

export function buildActuatorChartSegments(
  points: MonitoringActuatorHistoryPoint[],
  gaps: MonitoringActuatorHistoryGap[],
): ActuatorChartSegment[] {
  const ordered = [...points].sort(
    (left, right) => Date.parse(left.recorded_at) - Date.parse(right.recorded_at),
  )
  return ordered.slice(0, -1).flatMap((point, index) => {
    const following = ordered[index + 1]
    const start = Date.parse(point.recorded_at)
    const end = Date.parse(following.recorded_at)
    const crossesGap = gaps.some(
      (gap) => Date.parse(gap.from) < end && Date.parse(gap.to) > start,
    )
    return crossesGap ? [] : [{ from: point, to: following }]
  })
}
