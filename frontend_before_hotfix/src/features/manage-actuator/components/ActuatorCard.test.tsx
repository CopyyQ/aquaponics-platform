import { renderToStaticMarkup } from "react-dom/server"
import { describe, expect, it } from "vitest"

import { ActuatorElectricalPanel } from "@/features/manage-actuator/components/ActuatorElectricalPanel"
import type { Actuator } from "@/entities/actuator/model/types"
import type { ElectricalFeedbackMetric } from "@/entities/project/model/types"

const metric = (overrides: Partial<ElectricalFeedbackMetric> = {}): ElectricalFeedbackMetric => ({
  configured: true,
  sensor_id: 93,
  sensor_code: "OUTPUT-VOLTAGE",
  sensor_model_code: "OUTPUT_VOLTAGE_V",
  value_key: "voltage_v",
  value: 12.1,
  unit: "V",
  quality: "VALID",
  freshness: "FRESH",
  recorded_at: "2026-08-24T00:00:00Z",
  received_at: "2026-08-24T00:00:01Z",
  lower_threshold: 11,
  upper_threshold: 13,
  threshold_source: "MODEL_DEFAULT",
  threshold_status: "IN_RANGE",
  ...overrides,
})

const render = (voltage: ElectricalFeedbackMetric, current: ElectricalFeedbackMetric) => renderToStaticMarkup(
  <ActuatorElectricalPanel electrical={{ voltage, current } as Actuator["electrical_feedbacks"]} />,
)

describe("ActuatorElectricalPanel", () => {
  it("hiển thị điện áp, dòng điện, ngưỡng và giá trị 0", () => {
    const markup = render(metric(), metric({ unit: "A", value: 0, value_key: "current_a", lower_threshold: 0.3, upper_threshold: 2, threshold_status: "BELOW_RANGE" }))
    expect(markup).toContain("12,1 V")
    expect(markup).toContain("0 A")
    expect(markup).toContain("11 V")
    expect(markup).toContain("13 V")
    expect(markup).toContain("Trong ngưỡng")
    expect(markup).toContain("Thấp hơn ngưỡng")
  })

  it("phân biệt chưa cấu hình, không có dữ liệu, dữ liệu cũ và ngoài ngưỡng", () => {
    const unconfigured = metric({ configured: false, sensor_id: null, value: null, freshness: "NO_DATA", threshold_status: "UNCONFIGURED" })
    const noData = metric({ value: null, freshness: "NO_DATA", quality: "NO_DATA", threshold_status: "NO_DATA" })
    expect(render(unconfigured, noData)).toContain("Chưa cấu hình")
    expect(render(unconfigured, noData)).toContain("Không có dữ liệu")
    expect(render(metric({ freshness: "STALE", threshold_status: "STALE" }), metric({ threshold_status: "ABOVE_RANGE" }))).toContain("Dữ liệu cuối trước khi mất kết nối")
    expect(render(metric({ threshold_status: "ABOVE_RANGE" }), metric())).toContain("Cao hơn ngưỡng")
  })
})
