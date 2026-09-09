import { expect, test, type Page } from "@playwright/test"

const session = { user: { id: 1, username: "operator", full_name: "Người vận hành", email: "operator@example.test", phone_number: null, address: null, role_id: 1, status: "ACTIVE", must_change_password: false, last_login_at: null, created_at: "2026-01-01T00:00:00Z", updated_at: "2026-01-01T00:00:00Z", token_version: 1, is_deleted: false, deleted_at: null, disabled_at: null, disabled_by_user_id: null, disabled_reason: null, locked_at: null, locked_by_user_id: null, locked_reason: null }, permissions: ["aquaponics_systems.read", "devices.read", "monitoring.read", "scada.read", "incidents.read", "activities.read", "sensors.telemetry.read", "actuators.readings.read"] }
const system = { id: 7, code: "SYS-07", name: "Vườn thử nghiệm", location: "Nhà kính A", description: null, owner_user_id: 1, status: "ACTIVE" }
const device = { id: 11, aquaponics_system_id: 7, code: "CTRL-01", name: "Bộ điều khiển trung tâm", description: null, location: "Khu A", device_template_id: null, status: "ONLINE", is_enabled: true, sensors: [{ id: 21, device_id: 11, sensor_model_id: 31, code: "PH-01", name: "pH nước", installation_location: null, description: null, status: "ONLINE", is_enabled: true }], actuators: [{ id: 41, device_id: 11, actuator_model_id: 51, code: "PUMP-01", name: "Bơm tuần hoàn", location: "Khu A", notes: null, is_enabled: true, desired_state: true, reported_state: true, voltage_v: 12, current_a: 1.2 }] }

async function mockCanonicalApi(page: Page) {
  await page.addInitScript(() => localStorage.setItem("aquaponics_access_token", "test-token"))
  await page.route("**/api/v1/auth/session", (route) => route.fulfill({ json: session }))
  await page.route("**/api/v1/aquaponics-systems", (route) => route.fulfill({ json: [system] }))
  await page.route("**/api/v1/aquaponics-systems/7", (route) => route.fulfill({ json: system }))
  await page.route("**/api/v1/aquaponics-systems/7/devices", (route) => route.fulfill({ json: [device] }))
  await page.route("**/api/v1/aquaponics-systems/7/devices/11", (route) => route.fulfill({ json: device }))
  await page.route("**/api/v1/aquaponics-systems/7/monitoring/latest", (route) => route.fulfill({ json: { aquaponics_system_id: 7, devices: [{ id: 11, code: "CTRL-01", name: "Bộ điều khiển trung tâm", is_enabled: true, connection_status: "ONLINE", location: "Khu A", last_seen_at: "2026-01-01T00:00:00Z", sensors: [{ id: 21, code: "PH-01", name: "pH nước", unit: "pH", is_enabled: true, connection_status: "ONLINE", data_status: "ONLINE", latest: { value: 7.1, recorded_at: "2026-01-01T00:00:00Z" }, lower_threshold: 6, upper_threshold: 8 }], actuators: [] }] } }))
  await page.route("**/api/v1/aquaponics-systems/7/monitoring/series**", (route) => route.fulfill({ json: { aquaponics_system_id: 7, range: "24h", resolution: "hour", series: [{ sensor_id: 21, unit: "pH", points: [{ recorded_at: "2026-01-01T00:00:00Z", value: 7.1 }, { recorded_at: "2026-01-01T01:00:00Z", value: 7.2 }], gaps: [] }] } }))
  await page.route("**/api/v1/aquaponics-systems/7/alerts**", (route) => route.fulfill({ json: [] }))
  await page.route("**/api/v1/aquaponics-systems/7/scada/runtime", (route) => route.fulfill({ json: { aquaponics_system: system, dashboard: { id: null, status: "GENERATED", version: 1, schema_version: 1 }, layout: { schema_version: 1, camera: {}, symbols: [{ id: "sensor-21", type: "PH_SENSOR", label: "pH nước", position: [0, 0, 0], binding: { entity_type: "SENSOR", entity_id: 21 } }], connections: [] }, inventory: { devices: [], sensors: [], actuators: [] }, runtime: { devices: [], sensors: [{ id: 21, value: 7.1, recorded_at: "2026-01-01T00:00:00Z", received_at: "2026-01-01T00:00:00Z", freshness: "FRESH", quality: "VALID", quality_reason: null }], actuators: [], alerts: [] }, summary: { active_devices_total: 1, connected_devices: 1, waiting_devices: 0, disconnected_devices: 0, unknown_connectivity_devices: 0, disabled_devices: 0, active_sensors_total: 1, fresh_sensors: 1, fresh_valid_sensors: 1, fresh_invalid_sensors: 0, stale_sensors: 0, no_data_sensors: 0, disabled_sensors: 0, active_actuators_total: 0, actuators_on: 0, actuators_off: 0, actuators_out_of_sync: 0, commands_pending: 0, commands_failed: 0, commands_timeout: 0, disabled_actuators: 0, open_alerts: 0, critical_alerts: 0, warning_alerts: 0, unplaced_entities: 0 }, issues: [], unplaced_entities: [], updated_at: "2026-01-01T00:00:00Z" } }))
}

test("login screen uses canonical domain language", async ({ page }) => {
  await page.goto("/login")
  await expect(page.getByText("Vận hành Hệ thống Aquaponics")).toBeVisible()
})

test("authenticated operator can navigate the canonical operational surfaces", async ({ page }) => {
  await mockCanonicalApi(page)
  await page.goto("/aquaponics-systems")
  await expect(page.getByRole("heading", { name: "Hệ thống Aquaponics" })).toBeVisible()
  await page.getByRole("link", { name: /Vườn thử nghiệm/ }).click()
  await expect(page.getByRole("heading", { name: "Vườn thử nghiệm" })).toBeVisible()
  await expect(page.getByText("Cần chú ý")).toBeVisible()
  await page.getByRole("link", { name: "Quan trắc" }).click()
  await expect(page.getByRole("heading", { name: "Quan trắc hệ thống" })).toBeVisible()
  await expect(page.getByText("pH nước")).toBeVisible()
  await page.getByRole("link", { name: "Thiết bị" }).click()
  await page.getByRole("link", { name: /Bộ điều khiển trung tâm/ }).click()
  await expect(page.getByRole("heading", { name: "Bộ điều khiển trung tâm" })).toBeVisible()
  await expect(page.getByText("Sensors")).toBeVisible()
})

for (const width of [375, 768, 1440]) {
  test(`canonical system layout has no horizontal overflow at ${width}px`, async ({ page }) => {
    await page.setViewportSize({ width, height: 900 })
    await mockCanonicalApi(page)
    await page.goto("/aquaponics-systems/7/overview")
    await expect(page.getByRole("heading", { name: "Vườn thử nghiệm" })).toBeVisible()
    const overflow = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth)
    expect(overflow).toBeLessThanOrEqual(2)
  })
}
