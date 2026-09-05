import { describe, expect, it } from "vitest"
import { formatDateTime, formatVietnamTime } from "@/shared/lib/date"

describe("Vietnam datetime formatting", () => {
  it.each([
    ["2026-09-03T08:00:00Z", "03/09/2026 15:00:00", "15:00"],
    ["2026-09-03T00:00:00Z", "03/09/2026 07:00:00", "07:00"],
  ])("converts UTC instant %s once", (utc, expectedDateTime, expectedTime) => {
    expect(formatDateTime(utc)).toBe(expectedDateTime)
    expect(formatVietnamTime(utc)).toBe(expectedTime)
  })
})
