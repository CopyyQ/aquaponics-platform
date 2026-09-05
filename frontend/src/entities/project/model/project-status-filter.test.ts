import { describe, expect, it } from "vitest"

import type { AdminUserProject } from "@/entities/project/model/types"
import { filterProjectsByStatus, projectStatusCounts } from "@/entities/project/model/project-status-filter"

const projects = [
  { id: 1, name: "Active", code: "A", status: "ACTIVE" },
  { id: 2, name: "Disabled one", code: "D1", status: "DISABLED" },
  { id: 3, name: "Disabled two", code: "D2", status: "DISABLED" },
].map((project) => ({
  ...project,
  location: null,
  device_count: 0,
  sensor_count: 0,
  open_alert_count: 0,
  latest_telemetry_at: null,
})) as AdminUserProject[]

describe("Project status filter", () => {
  it("tách active, disabled và all mà không làm mất Project disabled", () => {
    expect(filterProjectsByStatus(projects, "active").map((item) => item.id)).toEqual([1])
    expect(filterProjectsByStatus(projects, "disabled").map((item) => item.id)).toEqual([2, 3])
    expect(filterProjectsByStatus(projects, "all").map((item) => item.id)).toEqual([1, 2, 3])
    expect(projectStatusCounts(projects)).toEqual({ active: 1, disabled: 2 })
  })
})
