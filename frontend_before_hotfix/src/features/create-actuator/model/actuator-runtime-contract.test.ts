import { readFileSync } from "node:fs"
import { resolve } from "node:path"
import { describe, expect, it } from "vitest"

function readSource(relativePath: string) {
  return readFileSync(resolve(process.cwd(), relativePath), "utf8")
}

describe("hợp đồng cấu hình cơ cấu chấp hành", () => {
  it("form runtime không nhận mã hoặc tên từ người dùng", () => {
    const source = readSource(
      "src/features/create-actuator/components/ActuatorFormDialog.tsx",
    )

    expect(source).toContain("Mẫu cơ cấu chấp hành")
    expect(source).toContain("Vị trí lắp đặt")
    expect(source).toContain("Ghi chú")
    expect(source).not.toContain(">Mã kỹ thuật<")
    expect(source).not.toContain(">Tên hiển thị<")
    expect(source).not.toContain("setCode")
    expect(source).not.toContain("setName")
  })

  it("API create chỉ gửi các trường cấu hình công khai", () => {
    const source = readSource(
      "src/entities/actuator/api/actuator-api.ts",
    )

    expect(source).toContain("actuator_model_id: number")
    expect(source).not.toContain("code?:")
    expect(source).not.toContain("name:")
    expect(source).toContain("httpClient.delete")
  })

  it("file MQTT được tải mới từ Backend thay vì dựng ở Frontend", () => {
    const source = readSource(
      "src/features/export-project-config/components/MqttConnectionPanel.tsx",
    )

    expect(source).toContain("downloadMqttConfig")
    expect(source).not.toContain("JSON.stringify")
    expect(source).toContain("config.actuators")
  })
})
