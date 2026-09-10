import { expect, test } from "@playwright/test"
import { guardRuntime } from "./helpers/runtime-guards"

test.skip(true, "Historical /admin/projects SCADA route; canonical SCADA is covered by canonical navigation and live walk.")

test("@smoke SCADA Project 81 biểu diễn Energy Monitor và refresh không reload", async ({ page }, testInfo) => {
  const assertRuntime = guardRuntime(page, testInfo)
  let documentLoads = 0
  page.on("request", (request) => { if (request.isNavigationRequest() && request.frame() === page.mainFrame()) documentLoads += 1 })
  await page.goto("/admin/projects/81/scada")
  await expect(page.getByRole("heading", { name: "Sơ đồ vận hành Aquaponics" })).toBeVisible()
  await expect(page.getByTestId("scada-canvas")).toBeVisible()
  await page.getByRole("button", { name: "Danh sách vận hành" }).click()
  const dialog = page.getByRole("dialog")
  const energyHeading = dialog.getByRole("heading", { name: /Thiết bị năng lượng/ })
  await expect(energyHeading).toBeVisible()
  await expect(dialog).toContainText("W")
  await energyHeading.locator("..").getByRole("button", { name: "Chọn trên sơ đồ" }).first().click()
  for (const label of ["Điện áp đầu ra", "Điện áp đầu vào", "Dòng điện tiêu thụ", "Dòng điện đầu vào", "Công suất tiêu thụ", "Điện năng tiêu thụ"]) {
    await expect(page.getByText(new RegExp(`^${label}:`))).toBeVisible()
  }
  await expect(page.getByText(/Thời gian hoạt động/)).toHaveCount(0)
  await expect(page.getByText(/OPERATING_HOURS/)).toHaveCount(0)
  await expect(page.getByRole("link", { name: "Mở dashboard năng lượng" })).toBeVisible()
  const loadsBeforeRefresh = documentLoads
  await page.getByRole("button", { name: "Làm mới" }).click()
  await expect(page.getByRole("button", { name: "Làm mới" })).toBeVisible()
  expect(documentLoads).toBe(loadsBeforeRefresh)
  await assertRuntime()
})
