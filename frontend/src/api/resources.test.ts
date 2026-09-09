import { describe, expect, it } from "vitest"
import { endpoints } from "./resources"

describe("canonical endpoint builders", () => {
  it("keeps every runtime resource under one AquaponicsSystem scope", () => {
    expect(endpoints.devices(12)).toBe("/aquaponics-systems/12/devices")
    expect(endpoints.sensors(12, 34)).toBe("/aquaponics-systems/12/devices/34/sensors")
    expect(endpoints.actuators(12, 34)).toBe("/aquaponics-systems/12/devices/34/actuators")
    expect(endpoints.alerts(12)).toBe("/aquaponics-systems/12/alerts")
    expect(endpoints.monitoringLatest(12)).toBe("/aquaponics-systems/12/monitoring/latest")
    expect(endpoints.monitoringSeries(12)).toBe("/aquaponics-systems/12/monitoring/series")
    expect(endpoints.alertSettings(12)).toBe("/aquaponics-systems/12/alerts/settings")
    expect(endpoints.mqttExport(12)).toBe("/aquaponics-systems/12/mqtt-config/export")
  })
})
