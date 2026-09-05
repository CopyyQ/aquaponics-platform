import { renderToStaticMarkup } from "react-dom/server"
import { describe, expect, it } from "vitest"
import { ActuatorMobileItem, ProjectDeviceMonitoringCard } from "@/widgets/project-device-monitoring/ProjectDeviceMonitoringCard"
import type { MonitoringDevice } from "@/entities/telemetry/model/project-monitoring"

const device: MonitoringDevice = {
  id: 86,
  code: "DEVICE-01",
  name: "Thiết bị nhà màng",
  is_enabled: true,
  connection_status: "OFFLINE",
  location: "Nhà màng số 1",
  last_seen_at: "2026-07-28T06:51:50Z",
  sensors: [{
    id: 101,
    code: "PH-01-INTERNAL",
    name: "Cảm biến pH",
    unit: "pH",
    is_enabled: true,
    connection_status: "OFFLINE",
    data_status: "OFFLINE",
    latest: { value: 7.2, recorded_at: "2026-07-28T06:40:00Z" },
    lower_threshold: 6.5,
    upper_threshold: 8.5,
    threshold_state: "NORMAL",
    alerts_enabled: true,
  }],
  actuators: [{
    id: 201,
    code: "PUMP-01",
    name: "Bơm tưới 01",
    actuator_model: "Bơm tưới",
    connection_status: "OFFLINE",
    desired_state: true,
    reported_state: false,
    synchronization_status: "OUT_OF_SYNC",
    latest_command: { status: "PUBLISHED", requested_at: "2026-07-28T06:45:00Z" },
    last_reported_at: "2026-07-28T06:40:00Z",
    electrical: { voltage: { configured: true, sensor_id: 300, value: 12, unit: "V", quality: "VALID", freshness: "FRESH", recorded_at: "2026-07-28T06:39:00Z", received_at: "2026-07-28T06:39:01Z", lower_threshold: 11, upper_threshold: 13 }, current: { configured: true, sensor_id: 301, value: 0, unit: "A", quality: "VALID", freshness: "FRESH", recorded_at: "2026-07-28T06:39:00Z", received_at: "2026-07-28T06:39:01Z", lower_threshold: 0.3, upper_threshold: 2 }, configured: true, sensor_id: 301, current_a: 0, quality: "VALID", freshness: "FRESH", recorded_at: "2026-07-28T06:39:00Z", received_at: "2026-07-28T06:39:01Z", minimum_running_current_a: 0.3, maximum_running_current_a: 2 },
    active_incident: null,
  }],
}

describe("ProjectDeviceMonitoringCard", () => {
  it("nhóm Sensor và Actuator một lần theo Device, không hiển thị mã hoặc boolean thô", () => {
    const markup = renderToStaticMarkup(
      <ProjectDeviceMonitoringCard device={device} onOpenMonitoring={() => undefined} />,
    )

    expect(markup).toContain("Thiết bị nhà màng")
    expect(markup).toContain("Cảm biến (1)")
    expect(markup).toContain("Cơ cấu chấp hành (1)")
    expect(markup).toContain("Mất dữ liệu")
    expect(markup).not.toContain("PH-01-INTERNAL")
    expect(markup).not.toContain(">true<")
    expect(markup).not.toContain(">false<")
  })

  it("giữ một Button chuyên dụng để mở biểu đồ thay vì biến Card thành button", () => {
    const markup = renderToStaticMarkup(
      <ProjectDeviceMonitoringCard device={device} onOpenMonitoring={() => undefined} />,
    )

    expect(markup).toContain('aria-label="Xem biểu đồ của Thiết bị nhà màng"')
    expect(markup).not.toContain('role="button"')
  })

  it.each([
    ["VALID", "FRESH", 0, "0 A"],
    ["NO_DATA", "NO_DATA", null, "Không có dữ liệu"],
    ["VALID", "STALE", 1.24, "Dữ liệu cũ"],
    ["INVALID", "FRESH", null, "Không hợp lệ"],
    ["OUT_OF_RANGE", "FRESH", 8.2, "Ngoài phạm vi"],
    ["UNVALIDATED", "FRESH", 1.1, "Chưa được xác thực"],
  ] as const)("hiển thị current với quality %s và freshness %s", (quality, freshness, current, expected) => {
    const actuator = {
      ...device.actuators[0],
      electrical: { ...device.actuators[0].electrical, current: { ...device.actuators[0].electrical.current, value: current, quality, freshness }, current_a: current, quality, freshness },
    }
    const markup = renderToStaticMarkup(<ActuatorMobileItem actuator={actuator} onOpen={() => undefined} />)
    expect(markup).toContain(expected)
  })

  it("phân biệt chưa cấu hình binding, giữ lệnh lỗi ở lịch sử và hiển thị sự cố mở", () => {
    const incident = {
      id: 42,
      technical_severity: "CRITICAL" as const,
      business_risk_level: "EXTREME",
      status: "OPEN",
      rule_name: "Bơm mất dòng",
      evaluator_type: "ACTUATOR_FEEDBACK",
      condition_summary: "Dòng điện thấp hơn ngưỡng.",
      started_at: "2026-07-28T06:39:00Z",
      duration_seconds: 90,
      evidence: {},
    }
    const variants = ["TIMEOUT", "FAILED"].map((status) => ({
      ...device.actuators[0],
      id: status === "TIMEOUT" ? 202 : 203,
      latest_command: { status, requested_at: "2026-07-28T06:45:00Z" },
      electrical: { ...device.actuators[0].electrical, voltage: { ...device.actuators[0].electrical.voltage, configured: false, sensor_id: null, value: null, quality: "NO_DATA" as const, freshness: "NO_DATA" as const }, current: { ...device.actuators[0].electrical.current, configured: false, sensor_id: null, value: null, quality: "NO_DATA" as const, freshness: "NO_DATA" as const }, configured: false, sensor_id: null, current_a: null, quality: "NO_DATA" as const, freshness: "NO_DATA" as const },
      active_incident: incident,
    }))
    const markup = variants.map((actuator) => renderToStaticMarkup(<ActuatorMobileItem actuator={actuator} onOpen={() => undefined} />)).join("")
    expect(markup).toContain("Chưa cấu hình")
    expect(markup).not.toContain("Không có dữ liệu · Không có dữ liệu")
    expect(markup).not.toContain("Thời gian đo")
    expect(markup).not.toContain("Backend nhận lúc")
    expect(markup).toContain("Hết thời gian chờ")
    expect(markup).toContain("Thất bại")
    expect(markup).toContain("Sự cố mở: Bơm mất dòng")
    expect(markup).not.toContain("Kết luận vận hành")
  })
})
