import { describe, expect, it } from "vitest"

import { resolveApiBaseUrl } from "@/shared/api/http-client"

describe("resolveApiBaseUrl", () => {
  it("không lặp /api/v1 khi Docker dùng Nginx proxy", () => {
    expect(resolveApiBaseUrl("/api/v1")).toBe("/api/v1")
    expect(resolveApiBaseUrl("/api/v1/")).toBe("/api/v1")
  })

  it("thêm API prefix cho host phát triển", () => {
    expect(resolveApiBaseUrl("http://localhost:8000")).toBe(
      "http://localhost:8000/api/v1",
    )
  })

  it("mặc định dùng cùng origin qua Nginx", () => {
    expect(resolveApiBaseUrl(undefined)).toBe("/api/v1")
  })
})
