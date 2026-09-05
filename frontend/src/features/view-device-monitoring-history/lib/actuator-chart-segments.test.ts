import { describe, expect, it } from "vitest"
import { buildActuatorChartSegments } from "@/features/view-device-monitoring-history/lib/actuator-chart-segments"

const point = (minute: number, state: boolean) => ({
  recorded_at: new Date(Date.UTC(2026, 6, 28, 10, minute)).toISOString(),
  state,
})

describe("buildActuatorChartSegments", () => {
  it("giữ transition xác nhận và ngắt qua khoảng mất dữ liệu", () => {
    const points = [point(0, false), point(5, true), point(30, false)]
    const gaps = [{
      from: point(5, true).recorded_at,
      to: point(30, false).recorded_at,
      reason: "DEVICE_OFFLINE",
    }]
    const segments = buildActuatorChartSegments(points, gaps)
    expect(segments).toHaveLength(1)
    expect(segments[0].from.state).toBe(false)
    expect(segments[0].to.state).toBe(true)
  })
})
