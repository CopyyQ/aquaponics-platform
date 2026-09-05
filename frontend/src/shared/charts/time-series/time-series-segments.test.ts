import { describe, expect, it } from "vitest"
import { buildThresholdSegments } from "@/shared/charts/time-series/time-series-segments"

const point = (minute: number, value: number) => ({ timestamp: new Date(Date.UTC(2026, 0, 1, 0, minute)).toISOString(), value })
const tones = (values: number[], safeMin?: number | null, safeMax?: number | null) => buildThresholdSegments(values.map((value, index) => point(index, value)), { safeMin, safeMax, expectedIntervalMs: 60_000 }).segments.map((segment) => segment.tone)

describe("buildThresholdSegments", () => {
  it("giữ toàn bộ đoạn trong ngưỡng màu xanh", () => expect(tones([5, 6, 7], 4, 8)).toEqual(["in-range", "in-range"]))
  it("chỉ phần trên ngưỡng là ngoài ngưỡng", () => expect(tones([7, 9], 4, 8)).toEqual(["in-range", "out-of-range"]))
  it("chỉ phần dưới ngưỡng là ngoài ngưỡng", () => expect(tones([3, 5], 4, 8)).toEqual(["out-of-range", "in-range"]))
  it("cắt đúng cả ngưỡng dưới và trên", () => expect(tones([2, 10], 4, 8)).toEqual(["out-of-range", "in-range", "out-of-range"]))
  it("điểm đúng bằng ngưỡng vẫn trong ngưỡng", () => expect(tones([4, 8], 4, 8)).toEqual(["in-range"]))
  it("ngắt segment tại khoảng dữ liệu thiếu", () => { const result = buildThresholdSegments([point(0, 5), point(1, 6), point(10, 7)], { safeMin: 4, safeMax: 8, expectedIntervalMs: 60_000 }); expect(result.gaps).toHaveLength(1); expect(result.segments).toHaveLength(1) })
  it("hỗ trợ một điểm duy nhất", () => expect(buildThresholdSegments([point(0, 5)], { safeMin: 4, safeMax: 8 }).segments).toHaveLength(1))
  it("không có threshold thì mọi đoạn đều trong ngưỡng", () => expect(tones([-100, 100])).toEqual(["in-range"]))
})
