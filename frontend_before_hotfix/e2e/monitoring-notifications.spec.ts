import { expect, test } from "@playwright/test"
import { guardRuntime } from "./helpers/runtime-guards"

test.skip(true, "Historical Project routes and recipient-level notification API are absent from current canonical OpenAPI.")

test("Project Monitoring và Notification page có contract mới", async ({ page }, testInfo) => {
  const assertRuntime = guardRuntime(page, testInfo)
  await page.goto("/admin/projects/81/monitoring")
  await page.getByRole("button", { name: /Xem biểu đồ của/ }).first().click()
  await expect(page.getByRole("radio", { name: /12 giờ/ }).first()).toBeVisible()
  const request12h = page.waitForResponse((response) => response.url().includes("range=12h") && response.ok())
  await page.getByRole("radio", { name: /12 giờ/ }).first().click()
  await request12h

  await page.goto("/admin/projects/81/notifications")
  await expect(page.getByRole("heading", { name: "Thông báo cảnh báo" })).toBeVisible()
  await expect(page.getByText("Telegram", { exact: true })).toBeVisible()
  await expect(page.getByRole("button", { name: /Thêm người nhận/ }).first()).toBeVisible()
  await assertRuntime()
})

test("Public Monitoring không hiển thị thao tác quản trị khi Project đã bật public", async ({ page }, testInfo) => {
  const assertRuntime = guardRuntime(page, testInfo)
  await page.goto("/admin/projects/81/settings")
  await expect(page.getByRole("heading", { name: "Theo dõi từ xa" })).toBeVisible()
  await expect(page.getByText("Giám sát dự án", { exact: true })).toBeVisible()
  await expect(page.getByText("Chỉ đọc", { exact: true })).toBeVisible()
  await expect(page.getByLabel("Đường dẫn công khai")).toHaveCount(0)
  const publicLink = page.getByRole("link", { name: /Mở giám sát từ xa/ })
  if (await publicLink.isVisible()) {
    await expect(publicLink).toHaveAttribute("href", /^https:\/\/[a-z0-9-]+\.trycloudflare\.com\/?$/)
  } else {
    await expect(page.getByRole("button", { name: /Mở giám sát từ xa/ })).toBeDisabled()
  }
  await assertRuntime()
})

test("Sensor Detail dùng dải 12h dùng chung", async ({ page }, testInfo) => {
  const assertRuntime = guardRuntime(page, testInfo)
  await page.goto("/admin/overview")
  const target = await page.evaluate(async () => {
    const token = localStorage.getItem("aquaponics_access_token")
    const response = await fetch("/api/v1/projects/81/monitoring/inventory", { headers: token ? { Authorization: `Bearer ${token}` } : {} })
    if (!response.ok) throw new Error(`Không thể tải inventory: ${response.status}`)
    const payload = await response.json() as { devices: Array<{ id: number; sensors: Array<{ id: number }> }> }
    const device = payload.devices.find((item) => item.sensors.length > 0)
    return device ? { deviceId: device.id, sensorId: device.sensors[0].id } : null
  })
  expect(target).toBeTruthy()
  await page.goto(`/admin/projects/81/devices/${target!.deviceId}/sensors/${target!.sensorId}`)
  await expect(page.getByRole("radio", { name: /12 giờ/ })).toBeVisible()
  const sensorRequest = page.waitForResponse((response) => {
    if (!response.url().includes(`/telemetry/sensors/${target!.sensorId}/history`) || !response.ok()) return false
    const url = new URL(response.url())
    const start = new Date(url.searchParams.get("start") ?? 0).getTime()
    const end = new Date(url.searchParams.get("end") ?? 0).getTime()
    return Math.abs(end - start - 12 * 60 * 60_000) < 5_000
  })
  await page.getByRole("radio", { name: /12 giờ/ }).click()
  await sensorRequest
  await assertRuntime()
})
