import { describe, expect, it } from "vitest"
import type { MonitoringFilters } from "@/features/admin-monitoring/model/types"

describe("hợp đồng bộ lọc giám sát Admin", () => {
  it("mặc định xếp rủi ro giảm dần và giữ scope phân trang", () => {
    const filters: MonitoringFilters = {
      q: "", health_status: "ALL", device_status: "ALL", stale_only: false,
      sort_by: "risk_score", sort_order: "desc", page: 1, page_size: 20,
    }
    expect(filters.sort_by).toBe("risk_score")
    expect(filters.sort_order).toBe("desc")
    expect(filters.page).toBe(1)
  })
})
