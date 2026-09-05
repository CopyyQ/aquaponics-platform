import { renderToStaticMarkup } from "react-dom/server"
import { describe, expect, it } from "vitest"

import { ActuatorHistoryStatistics } from "@/features/view-device-monitoring-history/ui/ActuatorHistoryStatistics"

const metric = (unit: "V" | "A", value: number | null, freshness: "FRESH" | "STALE" | "NO_DATA" = "FRESH") => ({ configured: true, sensor_id: 1, value, unit, quality: "VALID" as const, freshness, recorded_at: "2026-09-03T11:16:46Z", received_at: "2026-09-03T11:16:46Z", lower_threshold: null, upper_threshold: null })

describe("ActuatorHistoryStatistics", () => {
  it("đặt điện áp và dòng điện trong Thống kê hoạt động, kể cả giá trị 0", () => {
    const markup = renderToStaticMarkup(<ActuatorHistoryStatistics statistics={{ on_duration_seconds: 3600, off_duration_seconds: 0, unknown_duration_seconds: 0, on_percentage: 100, on_count: 1, off_count: 1, last_changed_at: "2026-09-03T10:30:00Z" }} electrical={{ voltage: metric("V", 12.1), current: metric("A", 0), configured: true, sensor_id: 1, current_a: 0, quality: "VALID", freshness: "FRESH", recorded_at: "2026-09-03T11:16:46Z", received_at: "2026-09-03T11:16:46Z", minimum_running_current_a: null, maximum_running_current_a: null }} />)
    expect(markup).toContain("Thống kê hoạt động")
    expect(markup).toContain("Điện áp hiện tại")
    expect(markup).toContain("12,1 V")
    expect(markup).toContain("Dòng điện hiện tại")
    expect(markup).toContain("0 A")
    expect(markup).not.toContain("Giám sát điện")
    expect(markup).not.toContain("Hợp lệ")
  })

  it("thể hiện dữ liệu cũ gọn trong ô thống kê", () => {
    const markup = renderToStaticMarkup(<ActuatorHistoryStatistics statistics={null} electrical={{ voltage: metric("V", 12.1, "STALE"), current: metric("A", null, "NO_DATA"), configured: true, sensor_id: 1, current_a: null, quality: "NO_DATA", freshness: "NO_DATA", recorded_at: null, received_at: null, minimum_running_current_a: null, maximum_running_current_a: null }} />)
    expect(markup).toContain("Dữ liệu cũ")
    expect(markup).toContain("Không có dữ liệu")
  })
})
