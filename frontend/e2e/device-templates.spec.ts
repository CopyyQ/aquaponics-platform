import { expect, test } from "@playwright/test"
import { guardRuntime } from "./helpers/runtime-guards"

test.skip(true, "Historical /admin/device-templates route; canonical catalog coverage uses /catalogs.")

const exactCodes = ["OUTPUT_VOLTAGE_V", "INPUT_VOLTAGE_V", "LOAD_CURRENT_A", "INPUT_CURRENT_A", "POWER_W", "ENERGY_TOTAL_WH"]

test("@smoke ENERGY_MONITOR_12V có đúng 6 phép đo", async ({ page }, testInfo) => {
  const assertRuntime = guardRuntime(page, testInfo)
  await page.goto("/admin/device-templates")
  const card = page.getByTestId("energy-monitor-template")
  await expect(card).toBeVisible()
  await expect(card).toContainText("Thiết bị giám sát năng lượng 12V")
  await expect(card).toContainText("ENERGY_MONITOR")
  await expect(card).toContainText("Danh định 12 V")
  await expect(card).toContainText("6 cảm biến")
  await expect(card).toContainText("6 bắt buộc")
  await expect(card).toContainText("Cấu hình hoàn chỉnh")
  const list = card.getByTestId("device-template-sensor-list")
  for (const code of exactCodes) await expect(list).toContainText(code)
  await expect(list).toContainText("V · NUMBER · GAUGE")
  await expect(list).toContainText("Wh · NUMBER · COUNTER")
  await expect(list).not.toContainText("OPERATING_HOURS_TOTAL_H")
  await expect(list).not.toContainText("OPERATING-HOURS")
  await assertRuntime()
})

test("dialog Thêm cảm biến dùng catalog backend và mapping chuẩn được bảo vệ", async ({ page }, testInfo) => {
  const assertRuntime = guardRuntime(page, testInfo)
  await page.goto("/admin/device-templates")
  const card = page.getByTestId("energy-monitor-template")
  await card.getByTestId("add-template-sensor").click()
  const dialog = page.getByRole("dialog")
  await expect(dialog).toBeVisible()
  await expect(dialog.getByRole("combobox", { name: "Sensor Model" })).toBeVisible()
  await expect(dialog.getByText("Bắt buộc", { exact: true })).toBeVisible()
  await expect(dialog.getByLabel("Thứ tự hiển thị")).toBeVisible()
  await page.getByRole("button", { name: "Hủy" }).click()
  const powerMapping = card.getByRole("listitem").filter({ hasText: "POWER_W" })
  await expect(powerMapping.getByRole("button", { name: /là phép đo bắt buộc/ })).toBeDisabled()
  await assertRuntime()
})

for (const width of [390, 768, 1024, 1440]) {
  test(`responsive Device Template ${width}px`, async ({ page }) => {
    await page.setViewportSize({ width, height: 900 })
    await page.goto("/admin/device-templates")
    await expect(page.getByTestId("energy-monitor-template")).toBeVisible()
    await page.getByTestId("energy-monitor-template").getByTestId("add-template-sensor").click()
    await expect(page.getByRole("dialog")).toBeVisible()
    const overflow = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth)
    expect(overflow).toBeLessThanOrEqual(2)
  })
}
