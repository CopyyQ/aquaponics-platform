import { describe, expect, it } from "vitest"
import { normalizeMonitoringSearchParams, parseMonitoringRange } from "@/pages/project-monitoring/project-monitoring.types"
import { queryKeys } from "@/shared/api/query-keys"

describe("Project Monitoring range", () => {
  it.each(["1h", "6h", "12h", "24h", "30d"] as const)("chấp nhận range %s", (range) => {
    expect(parseMonitoringRange(range)).toBe(range)
  })

  it("fallback về 24h khi range thiếu hoặc không hợp lệ", () => {
    expect(parseMonitoringRange(null)).toBe("24h")
    expect(parseMonitoringRange("7d")).toBe("24h")
  })

  it("tách cache Device history theo Device và range", () => {
    const scope = ["ADMIN", 1] as const
    expect(queryKeys.projects.deviceSensorSeries(scope, 8, 86, "1h")).not.toEqual(
      queryKeys.projects.deviceSensorSeries(scope, 8, 86, "24h"),
    )
    expect(queryKeys.projects.deviceActuatorHistory(scope, 8, 86, "24h")).not.toEqual(
      queryKeys.projects.deviceActuatorHistory(scope, 8, 87, "24h"),
    )
    expect(queryKeys.projects.summary(scope, 8)).toEqual(queryKeys.projects.summary(scope, 8))
  })

  it("chuẩn hóa URL energy cũ mà không ảnh hưởng range/history state", () => {
    const normalized = normalizeMonitoringSearchParams(new URLSearchParams("tab=energy&device=727&range=24h"))
    expect(normalized.toString()).toBe("range=24h")
  })
})
