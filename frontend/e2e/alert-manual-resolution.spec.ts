import { expect, test } from "@playwright/test"

test("Alert normalized vẫn mở cho đến khi người vận hành xác nhận khắc phục", async ({ page }) => {
  let resolved = false
  const alert = () => ({
    id: 990100,
    sensor_id: 990200,
    alert_type: "ABOVE_UPPER_THRESHOLD",
    severity: "WARNING",
    status: resolved ? "RESOLVED" : "OPEN",
    message: "Cảm biến pH vượt ngưỡng trên 8.5",
    trigger_value: 8.6,
    started_at: "2026-08-17T03:59:30Z",
    acknowledged_at: null,
    acknowledged_by: null,
    condition_active: false,
    normalized_at: "2026-08-17T04:00:00Z",
    resolved_at: resolved ? "2026-08-17T04:20:00Z" : null,
    resolved_by_user_id: resolved ? 1 : null,
    resolved_by_name: resolved ? "Quản trị viên" : null,
    resolution_note: resolved ? "Đã kiểm tra và điều chỉnh nước." : null,
    created_at: "2026-08-17T03:59:30Z",
    updated_at: "2026-08-17T04:00:00Z",
  })

  await page.route("**/api/v1/alerts**", async (route) => {
    if (route.request().method() === "POST" && route.request().url().endsWith("/990100/resolve")) {
      resolved = true
      await route.fulfill({ json: alert() })
      return
    }
    await route.fulfill({ json: [alert()] })
  })

  await page.goto("/alerts")
  await expect(page.getByText("Đang mở").first()).toBeVisible()
  await expect(page.getByText(/Đã trở về ngưỡng bình thường/)).toBeVisible()
  await expect(page.getByText(/Chờ xác nhận khắc phục/)).toBeVisible()
  await expect(page.getByText("Đã khắc phục", { exact: true })).toHaveCount(0)

  await page.getByRole("button", { name: "Xác nhận đã khắc phục" }).click()
  await expect(page.getByRole("heading", { name: "Xác nhận cảnh báo đã được khắc phục?" })).toBeVisible()
  await page.getByLabel("Ghi chú khắc phục").fill("Đã kiểm tra và điều chỉnh nước.")
  await page.getByRole("button", { name: "Xác nhận đã khắc phục" }).last().click()

  await expect(page.getByText("Đã khắc phục", { exact: true }).first()).toBeVisible()
  await expect(page.getByText(/Xác nhận bởi Quản trị viên/)).toBeVisible()
})
