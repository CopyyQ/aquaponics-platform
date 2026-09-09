import { expect, test } from "@playwright/test"
import { guardRuntime } from "./helpers/runtime-guards"

test("live authenticated canonical read-only product walk", async ({ page }, testInfo) => {
  test.skip(process.env.E2E_LIVE !== "true", "Requires explicit E2E_LIVE=true and local test credentials.")
  const username = process.env.E2E_ADMIN_USERNAME
  const password = process.env.E2E_ADMIN_PASSWORD
  expect(username, "E2E_ADMIN_USERNAME is required").toBeTruthy()
  expect(password, "E2E_ADMIN_PASSWORD is required").toBeTruthy()
  const assertRuntime = guardRuntime(page, testInfo)
  const legacyRequests: string[] = []
  const unexpectedResponses: string[] = []
  page.on("request", (request) => { if (/\/api\/v1\/(?:projects|admin|alerts)(?:\/|$)/.test(request.url())) legacyRequests.push(request.url()) })
  page.on("response", (response) => { if (response.status() >= 400 && response.request().resourceType() !== "document") unexpectedResponses.push(`${response.status()} ${response.url()}`) })

  await page.goto("/login")
  await page.getByLabel("Tên đăng nhập").fill(username!)
  await page.getByLabel("Mật khẩu", { exact: true }).fill(password!)
  await page.getByRole("button", { name: "Đăng nhập", exact: true }).click()
  await expect(page).toHaveURL(/\/aquaponics-systems$/)
  await expect(page.getByRole("heading", { name: "Hệ thống Aquaponics" })).toBeVisible()

  const fixture = await page.evaluate(async () => {
    const token = localStorage.getItem("aquaponics_access_token")
    const headers = token ? { Authorization: `Bearer ${token}` } : undefined
    const systemsResponse = await fetch("/api/v1/aquaponics-systems", { headers })
    if (!systemsResponse.ok) throw new Error(`systems ${systemsResponse.status}`)
    const systems = await systemsResponse.json() as Array<{ id: number }>
    const system = systems[0]
    if (!system) return null
    const devicesResponse = await fetch(`/api/v1/aquaponics-systems/${system.id}/devices`, { headers })
    if (!devicesResponse.ok) throw new Error(`devices ${devicesResponse.status}`)
    const devices = await devicesResponse.json() as Array<{ id: number; sensors: Array<{ id: number }>; actuators: Array<{ id: number }> }>
    const device = devices[0]
    return { systemId: system.id, deviceId: device?.id ?? null, sensorId: device?.sensors[0]?.id ?? null, actuatorId: device?.actuators[0]?.id ?? null }
  })
  expect(fixture, "Live test database needs at least one Aquaponics System").toBeTruthy()
  const systemId = fixture!.systemId
  const pages = [
    [`/aquaponics-systems/${systemId}/overview`, "Tình trạng thiết bị"],
    [`/aquaponics-systems/${systemId}/monitoring`, "Quan trắc hệ thống"],
    [`/aquaponics-systems/${systemId}/devices`, "Thiết bị"],
    [`/aquaponics-systems/${systemId}/alerts`, "Cảnh báo"],
    [`/aquaponics-systems/${systemId}/members`, "Thành viên hệ thống"],
    [`/aquaponics-systems/${systemId}/activities`, "Hoạt động hệ thống"],
    [`/aquaponics-systems/${systemId}/settings`, "Thiết lập hệ thống"],
    [`/aquaponics-systems/${systemId}/scada`, "Sơ đồ vận hành"],
    ["/catalogs", "Danh mục"], ["/users", "Người dùng"], ["/profile", "Hồ sơ người dùng"],
  ] as const
  for (const [url, text] of pages) {
    await page.goto(url)
    await expect(page.getByText(text, { exact: false }).first()).toBeVisible()
  }
  if (fixture!.deviceId) {
    await page.goto(`/aquaponics-systems/${systemId}/devices/${fixture!.deviceId}`)
    await expect(page.locator("main h2").first()).toBeVisible()
  }
  if (fixture!.deviceId && fixture!.sensorId) {
    await page.goto(`/aquaponics-systems/${systemId}/devices/${fixture!.deviceId}/sensors/${fixture!.sensorId}`)
    await expect(page.locator("main h2").first()).toBeVisible()
  }
  if (fixture!.deviceId && fixture!.actuatorId) {
    await page.goto(`/aquaponics-systems/${systemId}/devices/${fixture!.deviceId}/actuators/${fixture!.actuatorId}`)
    await expect(page.locator("main h2").first()).toBeVisible()
  }

  await page.goto(`/aquaponics-systems/${systemId}/overview`)
  await page.screenshot({ path: "../docs/audits/aquaponics_system_refactor/screenshots/overview-desktop.png", fullPage: true })
  await page.getByRole("button", { name: "Đổi giao diện" }).click()
  await page.reload()
  await expect(page.locator("html")).toHaveClass(/dark/)
  await page.screenshot({ path: "../docs/audits/aquaponics_system_refactor/screenshots/overview-dark.png", fullPage: true })
  await page.setViewportSize({ width: 375, height: 812 })
  await page.reload()
  await page.getByRole("button", { name: "Đổi giao diện" }).click()
  await page.screenshot({ path: "../docs/audits/aquaponics_system_refactor/screenshots/overview-mobile.png", fullPage: true })
  expect(await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth)).toBeLessThanOrEqual(2)
  expect(legacyRequests).toEqual([])
  expect(unexpectedResponses).toEqual([])
  await assertRuntime()
})
