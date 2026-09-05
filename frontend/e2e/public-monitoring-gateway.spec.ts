import { expect, test } from "@playwright/test"

test("public gateway chỉ phục vụ Monitoring read-only và range 12h", async ({ page, request }) => {
  const browserRequests: string[] = []
  page.on("request", (item) => browserRequests.push(item.url()))

  await page.goto("/")
  await expect(page.getByText("Aquaponics Platform · Theo dõi từ xa")).toBeVisible()
  await expect(page.getByRole("radio", { name: /12 giờ/ }).first()).toBeVisible()

  const request12h = page.waitForResponse((response) => response.url().includes("range=12h") && response.ok())
  await page.getByRole("radio", { name: /12 giờ/ }).first().click()
  await request12h

  await expect(page.getByText(/Control Pump|Telegram Chat ID|Quản lý thành viên|Cấu hình MQTT/i)).toHaveCount(0)
  expect((await request.get("/admin")).status()).toBe(404)
  expect((await request.get("/admin/projects/81/settings")).status()).toBe(404)
  expect((await request.get("/api/v1/projects/81/monitoring/overview")).status()).toBe(404)
  expect((await request.get("/api/v1/public-monitoring/overview")).status()).toBe(200)

  const currentOrigin = new URL(page.url()).origin
  expect(browserRequests.every((url) => new URL(url).origin === currentOrigin)).toBe(true)
  expect(browserRequests.some((url) => /:1883|:5432/.test(url))).toBe(false)
})
