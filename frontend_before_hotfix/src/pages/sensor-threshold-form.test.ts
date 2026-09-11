import { describe, expect, it } from "vitest"

import type { ThresholdAlertConfig } from "@/api/contracts"
import { thresholdDraftFromResponse } from "@/pages/sensor-detail-canonical"

const response: ThresholdAlertConfig = {
  id: 17,
  sensor_id: "31de12b4-baf0-4269-9bd8-8ea003a07e77",
  actuator_id: null,
  metric_type: "SENSOR_VALUE",
  enabled: true,
  lower_threshold: 30,
  upper_threshold: 50,
  below_risk_level: "LOW_MEDIUM",
  above_risk_level: "VERY_HIGH",
  below_message: "Thông báo dưới từ API",
  above_message: "Thông báo trên từ API",
  below_consequence: "Ảnh hưởng dưới từ API",
  above_consequence: "Ảnh hưởng trên từ API",
  below_recommended_actions: "Khuyến nghị dưới từ API",
  above_recommended_actions: "Khuyến nghị trên từ API",
  delay_seconds: 10,
  created_at: "2026-09-09T00:00:00Z",
  updated_at: "2026-09-09T01:00:00Z",
}

describe("Sensor Threshold Alert form", () => {
  it("hydrates every editable field from the GET/save canonical response", () => {
    expect(thresholdDraftFromResponse(response)).toEqual({
      enabled: response.enabled,
      lower_threshold: response.lower_threshold,
      upper_threshold: response.upper_threshold,
      below_risk_level: response.below_risk_level,
      above_risk_level: response.above_risk_level,
      below_message: response.below_message,
      above_message: response.above_message,
      below_consequence: response.below_consequence,
      above_consequence: response.above_consequence,
      below_recommended_actions: response.below_recommended_actions,
      above_recommended_actions: response.above_recommended_actions,
      delay_seconds: response.delay_seconds,
    })
  })
})
