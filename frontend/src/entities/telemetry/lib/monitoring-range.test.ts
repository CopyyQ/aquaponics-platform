import { describe, expect, it } from "vitest"
import { buildMonitoringWindow, monitoringExpectedInterval, monitoringRanges, parseMonitoringRange } from "@/entities/telemetry/lib/monitoring-range"

describe("shared monitoring range contract", () => {
  it("có canonical ranges theo đúng thứ tự và 30d nghĩa là 30 ngày", () => {
    expect(monitoringRanges.map((item) => item.value)).toEqual(["1h", "6h", "12h", "24h", "30d"])
    expect(monitoringRanges.at(-1)?.longLabel).toBe("30 ngày")
  })

  it("12h dùng cửa sổ 12 giờ và bucket kỳ vọng 10 phút", () => {
    const { start, end } = buildMonitoringWindow("12h")
    expect(end.getTime() - start.getTime()).toBe(12 * 60 * 60_000)
    expect(monitoringExpectedInterval("12h")).toBe(10 * 60_000)
    expect(parseMonitoringRange("12h")).toBe("12h")
  })
})
