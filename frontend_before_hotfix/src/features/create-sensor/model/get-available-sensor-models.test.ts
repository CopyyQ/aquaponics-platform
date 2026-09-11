import { describe, expect, it } from "vitest"
import type { SensorModel } from "@/entities/sensor-model/model/types"
import { getAvailableSensorModels } from "@/features/create-sensor/model/get-available-sensor-models"

const environmentalModels = [
  ["AIR_HUMIDITY", "Cảm biến độ ẩm môi trường", "%RH"],
  ["AIR_TEMPERATURE", "Cảm biến nhiệt độ môi trường", "°C"],
  ["AIR_PRESSURE", "Cảm biến áp suất không khí", "hPa"],
  ["ILLUMINANCE", "Cảm biến ánh sáng", "lux"],
].map(([code, name, unit], index): SensorModel => ({
  id: index + 1,
  code,
  name,
  unit,
  description: null,
  default_lower_threshold: null,
  default_upper_threshold: null,
  is_visible: true,
  is_active: true,
  value_type: "NUMBER",
  chart_type: "LINE",
  measurement_semantics: "GAUGE",
  created_at: "2026-07-27T00:00:00Z",
  updated_at: "2026-07-27T00:00:00Z",
}))

describe("environmental models in the create-sensor combobox", () => {
  it("offers all four active models", () => {
    expect(getAvailableSensorModels(environmentalModels, new Set(), "")).toHaveLength(4)
  })

  it("excludes inactive and already-used models", () => {
    const models = [
      { ...environmentalModels[0], is_active: false },
      ...environmentalModels.slice(1),
    ]
    const availableCodes = getAvailableSensorModels(models, new Set([2]), "")
      .map((model) => model.code)

    expect(availableCodes).not.toContain("AIR_HUMIDITY")
    expect(availableCodes).not.toContain("AIR_TEMPERATURE")
  })
})
