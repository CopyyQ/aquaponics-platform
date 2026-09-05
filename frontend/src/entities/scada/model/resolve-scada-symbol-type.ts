import type { ScadaSymbolType } from "@/entities/scada/model/types"

type SymbolEntity = {
  entityType: "DEVICE" | "SENSOR" | "ACTUATOR"
  deviceKind?: string | null
  templateCode?: string | null
  modelCode?: string | null
}

export function resolveScadaSymbolType(entity: SymbolEntity): ScadaSymbolType {
  const modelCode = entity.modelCode?.toUpperCase() ?? ""
  if (entity.entityType === "DEVICE") return entity.deviceKind === "ENERGY_MONITOR" ? "ENERGY_MONITOR" : "CONTROLLER_DEVICE"
  if (entity.entityType === "ACTUATOR") {
    if (modelCode.includes("AIR") && modelCode.includes("PUMP")) return "AIR_PUMP"
    if (modelCode.includes("PUMP") || modelCode.includes("MIST")) return "WATER_PUMP"
    if (modelCode.includes("VALVE")) return "VALVE"
    if (modelCode.includes("FAN")) return "FAN"
    if (modelCode.includes("LIGHT")) return "GROW_LIGHT"
    if (modelCode.includes("HEATER")) return "HEATER"
    return "GENERIC_ACTUATOR"
  }
  const sensorTypes: Record<string, ScadaSymbolType> = {
    PH: "PH_SENSOR", TEMP: "WATER_TEMPERATURE_SENSOR", WATER_TEMPERATURE: "WATER_TEMPERATURE_SENSOR",
    AIR_TEMPERATURE: "ENVIRONMENT_TEMPERATURE_SENSOR", AIR_HUMIDITY: "HUMIDITY_SENSOR",
    HUMIDITY: "HUMIDITY_SENSOR", DO: "DISSOLVED_OXYGEN_SENSOR", DISSOLVED_OXYGEN: "DISSOLVED_OXYGEN_SENSOR",
    EC: "EC_SENSOR", TDS: "TDS_SENSOR", TDS_01: "TDS_SENSOR", WATER_LEVEL: "WATER_LEVEL_SENSOR",
    ILLUMINANCE: "LIGHT_SENSOR", LIGHT: "LIGHT_SENSOR", AIR_PRESSURE: "AIR_PRESSURE_SENSOR",
  }
  return sensorTypes[modelCode] ?? "GENERIC_SENSOR"
}
