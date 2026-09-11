import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { renderToStaticMarkup } from "react-dom/server"
import { describe, expect, it, vi } from "vitest"

import type { DeviceTemplate } from "@/entities/device-template/model/types"
import { DeviceTemplateCard } from "@/features/manage-device-templates/components/DeviceTemplateCard"

vi.mock("@/features/auth/model/use-protected-query-scope", () => ({
  useProtectedQueryScope: () => ({ active: true, queryScope: [1, 1] as const }),
}))

const template: DeviceTemplate = {
  id: 12,
  code: "NFT_CONTROLLER",
  name: "Bộ điều khiển NFT",
  description: null,
  notes: null,
  device_kind: "GENERIC",
  nominal_output_voltage_v: 12,
  is_active: true,
  created_at: "2026-08-24T00:00:00Z",
  updated_at: "2026-08-24T00:00:00Z",
  sensors: [],
  actuators: [{
    id: 31,
    actuator_model_id: 5,
    code: "NFT_PUMP",
    default_name: "Bơm NFT",
    default_location: "Bể cá",
    default_notes: null,
    actuator_type: "PUMP",
    default_state: false,
    command_capability: "ON_OFF",
    monitor_current: true,
    electrical_profile_id: 8,
    electrical_profile_code: "PUMP_CURRENT_12V",
    electrical_profile_name: "Dòng điện bơm 12 V",
    sort_order: 1,
    is_required: true,
    is_enabled: true,
    model_code: "IRRIGATION_PUMP",
    model_name: "Bơm tưới",
  }],
}

describe("DeviceTemplateCard actuator CRUD", () => {
  it("hiển thị cấu hình actuator và đủ action thêm, sửa, xóa bằng tiếng Việt", () => {
    const client = new QueryClient()
    const markup = renderToStaticMarkup(<QueryClientProvider client={client}><DeviceTemplateCard template={template} /></QueryClientProvider>)
    expect(markup).toContain("Cơ cấu chấp hành")
    expect(markup).toContain("Bơm NFT")
    expect(markup).toContain("Mã: NFT_PUMP")
    expect(markup).toContain("Có giám sát dòng điện")
    expect(markup).toContain("Profile điện: Dòng điện bơm 12 V")
    expect(markup).toContain("Thêm cơ cấu chấp hành")
    expect(markup).toContain('aria-label="Chỉnh sửa Bơm NFT"')
    expect(markup).toContain('aria-label="Xóa Bơm NFT"')
    expect(markup).not.toContain("current_a")
  })
})
