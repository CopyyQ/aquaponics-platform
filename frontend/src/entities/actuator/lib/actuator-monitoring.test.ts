import { describe, expect, it } from "vitest"
import {
  getCommandStatus,
  getDesiredStateLabel,
  getReportedStateLabel,
  isAwaitingActuatorConfirmation,
} from "@/entities/actuator/lib/actuator-monitoring"

describe("actuator monitoring labels", () => {
  it("không hiển thị raw boolean", () => {
    expect(getDesiredStateLabel(true)).toBe("Yêu cầu bật")
    expect(getDesiredStateLabel(false)).toBe("Yêu cầu tắt")
    expect(getReportedStateLabel(true)).toBe("Đang bật")
    expect(getReportedStateLabel(false)).toBe("Đang tắt")
    expect(getReportedStateLabel(null)).toBe("Chưa xác định")
  })

  it("phân biệt command đang chờ xác nhận", () => {
    expect(getCommandStatus("PUBLISHED").active).toBe(true)
    expect(isAwaitingActuatorConfirmation(true, false, "PUBLISHED")).toBe(true)
    expect(isAwaitingActuatorConfirmation(true, true, "ACKNOWLEDGED")).toBe(false)
  })
})
