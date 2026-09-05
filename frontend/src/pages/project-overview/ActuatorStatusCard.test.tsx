import { renderToStaticMarkup } from "react-dom/server"
import { describe, expect, it } from "vitest"
import type { ProjectOverviewActuator } from "@/entities/project/model/types"
import { ActuatorStatusCard, incidentDurationLabel } from "@/pages/project-overview/ActuatorStatusCard"

const actuator = (patch: Partial<ProjectOverviewActuator> = {}): ProjectOverviewActuator => ({
  id: 17,
  name: "Bơm tuần hoàn",
  device_name: "Tủ điều khiển 01",
  connection_status: "CONNECTED",
  desired_state: true,
  reported_state: true,
  synchronization_status: "IN_SYNC",
  command_status: "ACKNOWLEDGED",
  last_reported_at: "2026-08-24T01:00:00Z",
  latest_command: null,
  electrical: {
    voltage: { configured: true, sensor_id: 26, value: 12, unit: "V", quality: "VALID", freshness: "FRESH", recorded_at: "2026-08-24T01:00:00Z", received_at: "2026-08-24T01:00:01Z", lower_threshold: null, upper_threshold: null },
    current: { configured: true, sensor_id: 27, value: 0, unit: "A", quality: "VALID", freshness: "FRESH", recorded_at: "2026-08-24T01:00:00Z", received_at: "2026-08-24T01:00:01Z", lower_threshold: 0.5, upper_threshold: 4 },
    configured: true,
    sensor_id: 27,
    current_a: 0,
    quality: "VALID",
    freshness: "FRESH",
    recorded_at: "2026-08-24T01:00:00Z",
    received_at: "2026-08-24T01:00:01Z",
    minimum_running_current_a: 0.5,
    maximum_running_current_a: 4,
  },
  operational_conclusion: {
    code: "RUNNING_CURRENT_LOW",
    label: "Có lệnh chạy nhưng dòng điện thấp",
    explanation: "Kiểm tra nguồn cấp và bơm.",
  },
  active_incident: null,
  ...patch,
})

describe("ActuatorStatusCard", () => {
  it("hiển thị 0 A như một số đo hợp lệ và đủ trạng thái vận hành", () => {
    const markup = renderToStaticMarkup(<ActuatorStatusCard actuator={actuator()} />)
    expect(markup).toContain("0 A")
    expect(markup).toContain("Đã xác nhận")
    expect(markup).toContain("Hợp lệ")
    expect(markup).toContain("Mới")
    expect(markup).toContain("Có lệnh chạy nhưng dòng điện thấp")
  })

  it.each([
    ["NO_DATA", "NO_DATA", "Không có dữ liệu", "Không có dữ liệu"],
    ["INVALID", "FRESH", "Không hợp lệ", "Mới"],
    ["OUT_OF_RANGE", "FRESH", "Ngoài phạm vi", "Mới"],
    ["UNVALIDATED", "STALE", "Chưa được xác thực", "Dữ liệu cũ"],
  ] as const)("hiển thị quality %s và freshness %s", (quality, freshness, qualityLabel, freshnessLabel) => {
    const markup = renderToStaticMarkup(
      <ActuatorStatusCard actuator={actuator({ electrical: { ...actuator().electrical, current_a: null, quality, freshness } })} />,
    )
    expect(markup).toContain(qualityLabel)
    expect(markup).toContain(freshnessLabel)
  })

  it("phân biệt cảm biến dòng chưa cấu hình", () => {
    const markup = renderToStaticMarkup(
      <ActuatorStatusCard actuator={actuator({ electrical: { ...actuator().electrical, configured: false, sensor_id: null, current_a: null, quality: "NO_DATA", freshness: "NO_DATA" } })} />,
    )
    expect(markup).toContain("Chưa cấu hình đo dòng điện")
  })

  it.each([
    ["FAILED", "Thất bại"],
    ["TIMEOUT", "Hết thời gian chờ"],
  ])("Việt hóa trạng thái lệnh %s", (status, label) => {
    expect(renderToStaticMarkup(<ActuatorStatusCard actuator={actuator({ command_status: status })} />)).toContain(label)
  })

  it("hiển thị evidence đã lưu của sự cố thay vì diễn giải lại từ dữ liệu mới nhất", () => {
    const markup = renderToStaticMarkup(
      <ActuatorStatusCard actuator={actuator({
        electrical: { ...actuator().electrical, current_a: 2.5 },
        active_incident: {
          id: 81,
          technical_severity: "CRITICAL",
          business_risk_level: "VERY_HIGH",
          status: "OPEN",
          rule_name: "Bơm không có dòng điện",
          evaluator_type: "ACTUATOR_FEEDBACK",
          condition_summary: "Dòng điện 0,2 A thấp hơn ngưỡng 0,5 A khi cơ cấu phải chạy.",
          started_at: "2026-08-24T01:00:00Z",
          duration_seconds: 3723,
          evidence: {
            current_a: 0.2,
            threshold: 0.5,
            desired_state: true,
            reported_state: false,
            command_status: "FAILED",
            quality: "VALID",
            freshness: "FRESH",
          },
        },
      })} />,
    )
    expect(markup).toContain("Dòng điện 0,2 A thấp hơn ngưỡng 0,5 A")
    expect(markup).toContain("0,2 A")
    expect(markup).toContain("0,5 A")
    expect(markup).toContain("Rất cao")
    expect(markup).toContain("Nghiêm trọng")
    expect(markup).toContain("1 giờ 2 phút 3 giây")
    expect(markup).toContain("Thất bại")
  })

  it("định dạng thời lượng ổn định", () => {
    expect(incidentDurationLabel(0)).toBe("0 giây")
    expect(incidentDurationLabel(90061)).toBe("1 ngày 1 giờ 1 phút 1 giây")
  })
})
