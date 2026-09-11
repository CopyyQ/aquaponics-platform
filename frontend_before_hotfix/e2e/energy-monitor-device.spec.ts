import { expect, test } from "@playwright/test"
import { guardRuntime } from "./helpers/runtime-guards"

test.skip(true, "Historical special runtime device-kind API conflicts with the canonical mixed Device/Sensor model.")

type RuntimeDevice = { id: number; device_kind?: string }
type MqttConfig = {
  sensors: Array<{ sensor_code: string; sensor_model_code: string }>
  energy_monitoring?: { power_sensor_code: string; energy_sensor_code: string; supported_ranges: string[] }
}

const canonicalModels = ["OUTPUT_VOLTAGE_V", "INPUT_VOLTAGE_V", "LOAD_CURRENT_A", "INPUT_CURRENT_A", "POWER_W", "ENERGY_TOTAL_WH"]

test("Energy Device Project 81 có dashboard 6/6 và batch API", async ({ page }, testInfo) => {
  const assertRuntime = guardRuntime(page, testInfo)
  await page.goto("/admin/overview")
  const devices = await page.evaluate(async () => {
    const token = localStorage.getItem("aquaponics_access_token")
    const response = await fetch("/api/v1/projects/81/devices?include_disabled=true", { headers: token ? { Authorization: `Bearer ${token}` } : {} })
    if (!response.ok) throw new Error(`Không thể tải Device Project 81: ${response.status}`)
    const body = await response.json() as { items?: RuntimeDevice[] } | RuntimeDevice[]
    return Array.isArray(body) ? body : body.items ?? []
  })
  const energyDevice = devices.find((item) => item.device_kind === "ENERGY_MONITOR")
  expect(energyDevice, "Project 81 phải có Energy Monitor runtime").toBeTruthy()
  const requests: string[] = []
  page.on("request", (request) => { if (request.resourceType() === "xhr" || request.resourceType() === "fetch") requests.push(request.url()) })
  await page.goto(`/admin/projects/81/devices/${energyDevice!.id}`)
  await expect(page.getByLabel("Dashboard thiết bị giám sát năng lượng")).toBeVisible()
  const measurements = page.getByTestId("energy-monitor-measurements")
  await expect(measurements.locator(":scope > *")).toHaveCount(6)
  await expect(measurements).toContainText("Điện áp đầu ra")
  await expect(measurements).toContainText("Điện áp đầu vào")
  await expect(measurements).toContainText("Dòng điện tiêu thụ")
  await expect(measurements).toContainText("Dòng điện đầu vào")
  await expect(measurements).toContainText("Công suất tiêu thụ")
  await expect(measurements).toContainText("Điện năng tiêu thụ")
  await expect(measurements).not.toContainText("Thời gian hoạt động")
  await expect(measurements).not.toContainText("OPERATING_HOURS_TOTAL_H")
  await expect(measurements).not.toContainText("Điện áp đầu ra đo thực tế")
  await expect(measurements).not.toContainText("Dòng điện tải")
  await expect(measurements).not.toContainText("Điện năng tích lũy")
  await expect(page.getByText("Phép đo dự kiến").locator("..")).toContainText("6")
  await expect(page.getByText("Công suất tiêu thụ", { exact: true }).last()).toBeVisible()
  await expect(page.getByText("Điện năng tiêu thụ", { exact: true }).last()).toBeVisible()
  await expect(page.getByRole("radio", { name: "12 giờ" })).toBeVisible()
  expect(requests.filter((url) => url.includes("energy-overview"))).toHaveLength(1)
  expect(requests.filter((url) => url.includes("energy-power-series"))).toHaveLength(1)
  const twelveHourRequest = page.waitForResponse((response) => response.url().includes("energy-power-series") && response.url().includes("range=12h") && response.ok())
  await page.getByRole("radio", { name: "12 giờ" }).click()
  await twelveHourRequest
  expect(requests.filter((url) => /sensors?\/\d+\/latest/.test(url))).toHaveLength(0)
  const config = await page.evaluate(async ({ projectId, deviceId }) => {
    const token = localStorage.getItem("aquaponics_access_token")
    const response = await fetch(`/api/v1/projects/${projectId}/devices/${deviceId}/mqtt-connection-config`, { headers: token ? { Authorization: `Bearer ${token}` } : {} })
    if (!response.ok) throw new Error(`Không thể tải cấu hình MQTT: ${response.status}`)
    return await response.json() as MqttConfig
  }, { projectId: 81, deviceId: energyDevice!.id })
  expect(config.sensors).toHaveLength(6)
  expect(config.sensors.map((item) => item.sensor_model_code)).toEqual(canonicalModels)
  expect(config.sensors.map((item) => item.sensor_code)).toEqual(["OUTPUT-VOLTAGE", "INPUT-VOLTAGE", "LOAD-CURRENT", "INPUT-CURRENT", "POWER", "ENERGY"])
  expect(config.energy_monitoring).toEqual({ power_sensor_code: "POWER", energy_sensor_code: "ENERGY", supported_ranges: ["1h", "6h", "12h", "24h", "1m"], range_meanings: { "1h": "ONE_HOUR", "6h": "SIX_HOURS", "12h": "TWELVE_HOURS", "24h": "TWENTY_FOUR_HOURS", "1m": "ONE_MONTH" } })
  expect(JSON.stringify(config)).not.toContain("OPERATING")
  await assertRuntime()
})
