import { describe, expect, it } from "vitest"
import { endpoints } from "./resources"

describe("canonical endpoint builders", () => {
  const systemId = "2cfcf7c6-7417-4342-86c7-89c5482384ed"
  const deviceId = "8aa2d34e-457e-418d-b47e-f7c63cce82d2"
  const userId = "b92890b0-58d3-48af-9cb5-47ff255cab38"

  it("keeps every runtime resource under one AquaponicsSystem scope", () => {
    expect(endpoints.system(systemId)).toBe(`/aquaponics-systems/${systemId}`)
    expect(endpoints.devices(systemId)).toBe(`/aquaponics-systems/${systemId}/devices`)
    expect(endpoints.sensors(systemId, deviceId)).toBe(`/aquaponics-systems/${systemId}/devices/${deviceId}/sensors`)
    expect(endpoints.actuators(systemId, deviceId)).toBe(`/aquaponics-systems/${systemId}/devices/${deviceId}/actuators`)
    expect(endpoints.alerts(systemId)).toBe(`/aquaponics-systems/${systemId}/alerts`)
    expect(endpoints.monitoringLatest(systemId)).toBe(`/aquaponics-systems/${systemId}/monitoring/latest`)
    expect(endpoints.monitoringSeries(systemId)).toBe(`/aquaponics-systems/${systemId}/monitoring/series`)
    expect(endpoints.alertSettings(systemId)).toBe(`/aquaponics-systems/${systemId}/alerts/settings`)
    expect(endpoints.mqttExport(systemId)).toBe(`/aquaponics-systems/${systemId}/mqtt-config/export`)
    expect(Object.values(endpoints).filter((value) => typeof value === "string").join(" ")).not.toContain("NaN")
  })

  it("uses canonical user-centric Aquaponics System endpoints", () => {
    expect(endpoints.userSystems(userId)).toBe(`/users/${userId}/aquaponics-systems`)
    expect(endpoints.systemOwner(systemId)).toBe(`/aquaponics-systems/${systemId}/owner`)
  })
})
