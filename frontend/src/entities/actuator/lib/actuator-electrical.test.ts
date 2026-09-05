import { describe, expect, it } from "vitest"
import { actuatorCommandLabel, actuatorCurrentLabel, electricalFreshnessLabel, electricalQualityLabel } from "@/entities/actuator/lib/actuator-electrical"
import type { ProjectOverviewActuator } from "@/entities/project/model/types"

const metric = (unit: "V" | "A", value: number | null) => ({ configured: true, sensor_id: 1, value, unit, quality: "VALID" as const, freshness: "FRESH" as const, recorded_at: null, received_at: null, lower_threshold: null, upper_threshold: null })
const electrical = (patch: Partial<ProjectOverviewActuator["electrical"]> = {}): ProjectOverviewActuator["electrical"] => ({ voltage: metric("V", 12), current: metric("A", 0), configured: true, sensor_id: 1, current_a: 0, quality: "VALID", freshness: "FRESH", recorded_at: null, received_at: null, minimum_running_current_a: null, maximum_running_current_a: null, ...patch })

describe("hiển thị phản hồi điện của cơ cấu chấp hành", () => {
  it("phân biệt 0 A với thiếu dữ liệu và chưa cấu hình", () => {
    expect(actuatorCurrentLabel(electrical())).toBe("0 A")
    expect(actuatorCurrentLabel(electrical({ current_a: null }))).toBe("Không có dữ liệu")
    expect(actuatorCurrentLabel(electrical({ configured: false, current_a: null }))).toBe("Chưa cấu hình đo dòng điện")
  })

  it("Việt hóa quality, freshness và trạng thái lệnh", () => {
    expect(electricalQualityLabel("OUT_OF_RANGE")).toBe("Ngoài phạm vi")
    expect(electricalQualityLabel("INVALID")).toBe("Không hợp lệ")
    expect(electricalQualityLabel("UNVALIDATED")).toBe("Chưa được xác thực")
    expect(electricalFreshnessLabel("STALE")).toBe("Dữ liệu cũ")
    expect(actuatorCommandLabel("ACKNOWLEDGED")).toBe("Đã xác nhận")
    expect(actuatorCommandLabel("FAILED")).toBe("Thất bại")
    expect(actuatorCommandLabel("TIMEOUT")).toBe("Hết thời gian chờ")
  })
})
