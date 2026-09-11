import { describe, expect, it } from "vitest"

import axios, { AxiosHeaders } from "axios"

import {
  formatBackendErrorPayload,
  formatResourceLoadError,
} from "@/shared/api/backend-error"

describe("formatBackendErrorPayload", () => {
  it("hiển thị code, current_role và nội dung lỗi lồng của Backend", () => {
    expect(
      formatBackendErrorPayload(
        {
          detail: {
            code: "ADMIN_REQUIRED",
            current_role: "OWNER",
            detail: "Chỉ Quản trị viên mới có quyền thực hiện thao tác này.",
          },
        },
        "Lỗi dự phòng",
      ),
    ).toBe(
      "code: ADMIN_REQUIRED • current_role: OWNER • Chỉ Quản trị viên mới có quyền thực hiện thao tác này.",
    )
  })

  it("hiển thị lỗi xác thực dạng top-level của Backend", () => {
    expect(
      formatBackendErrorPayload(
        {
          code: "TOKEN_REVOKED",
          detail: "Phiên đăng nhập đã hết hiệu lực.",
        },
        "Lỗi dự phòng",
      ),
    ).toBe("code: TOKEN_REVOKED • Phiên đăng nhập đã hết hiệu lực.")
  })
})

describe("formatResourceLoadError", () => {
  it.each([
    [401, "Phiên đăng nhập đã hết hạn."],
    [403, "Bạn không có quyền truy cập danh sách mẫu thiết bị."],
    [404, "Endpoint không tồn tại hoặc route API đang cấu hình sai."],
    [500, "Backend gặp lỗi khi tải danh sách mẫu thiết bị."],
  ])("phân loại HTTP %s", (status, expected) => {
    const error = new axios.AxiosError(
      "request failed",
      undefined,
      undefined,
      undefined,
      {
        status,
        statusText: "",
        headers: {},
        config: { headers: new AxiosHeaders() },
        data: {},
      },
    )
    expect(
      formatResourceLoadError(error, "danh sách mẫu thiết bị"),
    ).toBe(expected)
  })
})
