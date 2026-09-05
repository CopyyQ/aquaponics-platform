import { describe, expect, it } from "vitest"
import { projectRoutePaths } from "@/app/router/project-route-paths"

describe("project route context", () => {
  it("keeps device and sensor details below a project", () => {
    expect(projectRoutePaths).toContain("devices/:deviceId")
    expect(projectRoutePaths).toContain("devices/:deviceId/sensors/:sensorId")
    expect(projectRoutePaths).not.toContain("/devices/:deviceId")
    expect(projectRoutePaths).not.toContain("/sensors/:sensorId")
  })
})
