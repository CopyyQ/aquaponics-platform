import { describe, expect, it } from "vitest"

import {
  formatTelemetryValue,
  getTelemetryStatus,
  getTelemetrySummary,
} from "@/entities/telemetry/lib/telemetry-display"

describe("hiển thị dữ liệu quan trắc", () => {
  it("tính thống kê chuỗi dữ liệu", () => {
    const summary = getTelemetrySummary([
      {
        timestamp: "2026-07-20T00:00:00Z",
        value: 6,
        min_value: 6,
        max_value: 6,
        record_count: 1,
        resolution: "RAW",
      },
      {
        timestamp: "2026-07-20T01:00:00Z",
        value: 8,
        min_value: 8,
        max_value: 8,
        record_count: 1,
        resolution: "RAW",
      },
    ])

    expect(summary).toEqual({ min: 6, max: 8, average: 7, count: 2 })
  })

  it("định dạng dữ liệu thiếu và dữ liệu có đơn vị", () => {
    expect(formatTelemetryValue(null, "pH")).toBe("Chưa có dữ liệu")
    expect(formatTelemetryValue(7.125, "pH", 2)).toBe("7.13 pH")
  })

  it("ưu tiên trạng thái ngoại tuyến và nhận diện vượt ngưỡng", () => {
    expect(getTelemetryStatus(7, 6.5, 8.5, true)).toBe("offline")
    expect(getTelemetryStatus(9, 6.5, 8.5)).toBe("warning")
    expect(getTelemetryStatus(7, 6.5, 8.5)).toBe("normal")
  })
})
