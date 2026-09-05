import { describe, expect, it } from "vitest"

import { compatibleFeedbackSensorModels } from "@/features/manage-device-templates/components/ActuatorModelDialog"
import type { SensorModel } from "@/entities/sensor-model/model/types"

const model = (id: number, code: string, unit: string): SensorModel => ({
  id, code, name: code, unit, description: null, default_lower_threshold: null,
  default_upper_threshold: null, is_visible: true, is_active: true,
  value_type: "NUMBER", chart_type: "LINE", measurement_semantics: "GAUGE",
  created_at: "2026-08-24T00:00:00Z", updated_at: "2026-08-24T00:00:00Z",
})

describe("compatibleFeedbackSensorModels", () => {
  const models = [model(1, "OUTPUT_VOLTAGE_V", "V"), model(2, "INPUT_VOLTAGE_V", "V"), model(3, "LOAD_CURRENT_A", "A"), model(4, "INPUT_CURRENT_A", "A")]

  it("chỉ trả mẫu điện áp cho SUPPLY_VOLTAGE", () => {
    expect(compatibleFeedbackSensorModels(models, "SUPPLY_VOLTAGE").map(item => item.code)).toEqual(["OUTPUT_VOLTAGE_V", "INPUT_VOLTAGE_V"])
  })

  it("chỉ trả mẫu dòng điện cho RUNNING_CURRENT", () => {
    expect(compatibleFeedbackSensorModels(models, "RUNNING_CURRENT").map(item => item.code)).toEqual(["LOAD_CURRENT_A", "INPUT_CURRENT_A"])
  })
})
