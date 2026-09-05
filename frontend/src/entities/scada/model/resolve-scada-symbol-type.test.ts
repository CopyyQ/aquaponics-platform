import { describe, expect, it } from "vitest"
import { resolveScadaSymbolType } from "@/entities/scada/model/resolve-scada-symbol-type"

describe("resolveScadaSymbolType", () => {
  it("nhận diện Energy Monitor bằng device_kind thay vì tên", () => {
    expect(resolveScadaSymbolType({ entityType: "DEVICE", deviceKind: "ENERGY_MONITOR", templateCode: "POWER_12V" })).toBe("ENERGY_MONITOR")
    expect(resolveScadaSymbolType({ entityType: "DEVICE", deviceKind: "GENERIC", templateCode: "ENERGY_MONITOR_BY_NAME_ONLY" })).toBe("CONTROLLER_DEVICE")
  })

  it("ánh xạ Sensor và Actuator từ catalog code", () => {
    expect(resolveScadaSymbolType({ entityType: "SENSOR", modelCode: "PH" })).toBe("PH_SENSOR")
    expect(resolveScadaSymbolType({ entityType: "SENSOR", modelCode: "AIR_HUMIDITY" })).toBe("HUMIDITY_SENSOR")
    expect(resolveScadaSymbolType({ entityType: "ACTUATOR", modelCode: "GROW_LIGHT" })).toBe("GROW_LIGHT")
    expect(resolveScadaSymbolType({ entityType: "ACTUATOR", modelCode: "FISH_TANK_PUMP" })).toBe("WATER_PUMP")
  })

  it("dùng generic symbol khi catalog thiếu metadata", () => {
    expect(resolveScadaSymbolType({ entityType: "SENSOR", modelCode: "CUSTOM" })).toBe("GENERIC_SENSOR")
    expect(resolveScadaSymbolType({ entityType: "ACTUATOR" })).toBe("GENERIC_ACTUATOR")
  })
})
