import { readFileSync } from "node:fs"
import { describe, expect, it } from "vitest"

describe("User detail Aquaponics Systems", () => {
  it("uses an owner-only creation dialog with only a name field", () => {
    const source = readFileSync(new URL("./user-detail-canonical.tsx", import.meta.url), "utf8")
    expect(source).not.toMatch(/\bProject\b|Dự án|\/projects|\/admin\/users/)
    expect(source).not.toContain("listAvailableUserAquaponicsSystems")
    expect(source).not.toContain("TECHNICIAN")
    expect(source).not.toContain("VIEWER")
    expect(source).toContain("Tên hệ thống")
    expect(source).toContain("Hệ thống Aquaponics sở hữu")
    expect(source).toContain("Quản lý tài khoản")
  })
})
