import { expect, test } from "@playwright/test"

test.skip(true, "Historical admin activation endpoint is absent from the canonical OpenAPI; system lifecycle uses canonical CRUD.")

test("Project disabled vẫn hiển thị và có thể kích hoạt lại không reload", async ({ page }) => {
  let status: "ACTIVE" | "DISABLED" = "DISABLED"
  const project = () => ({
    id: 990081,
    name: "Dự án hotfix cô lập",
    code: "HOTFIX-P0",
    location: "Khu kiểm thử",
    status,
    device_count: 2,
    sensor_count: 4,
    open_alert_count: 0,
    latest_telemetry_at: null,
  })
  const activeProject = {
    ...project(),
    id: 990082,
    name: "Dự án đang hoạt động cô lập",
    code: "ACTIVE-P0",
    status: "ACTIVE" as const,
  }
  await page.route("**/api/v1/admin/users/990001", (route) => route.fulfill({ json: {
    id: 990001,
    username: "hotfix-owner",
    full_name: "Owner Hotfix",
    email: "hotfix@example.test",
    phone_number: "0000000000",
    address: "",
    system_role: "OWNER",
    status: "ACTIVE",
    is_deleted: false,
    deleted_at: null,
    disabled_at: null,
    disabled_reason: null,
    locked_at: null,
    locked_reason: null,
    token_version: 1,
    must_change_password: false,
    last_login_at: null,
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
    project_count: 1,
    device_count: 2,
    sensor_count: 4,
    open_alert_count: 0,
    online_device_count: 0,
    offline_device_count: 2,
  } }))
  await page.route("**/api/v1/admin/users/990001/projects", (route) => route.fulfill({ json: { items: [activeProject, project()], total: 2 } }))
  await page.route("**/api/v1/admin/users/990001/activity", (route) => route.fulfill({ json: [] }))
  await page.route("**/api/v1/projects/990081/activate", async (route) => {
    status = "ACTIVE"
    await route.fulfill({ json: { ...project(), owner_user_id: 990001, description: null, disabled_at: null, disabled_by_user_id: null, disabled_reason: null, created_at: new Date().toISOString(), updated_at: new Date().toISOString() } })
  })

  await page.goto("/admin/users/990001")
  await page.getByRole("tab", { name: "Dự án" }).click()
  await expect(page.getByRole("button", { name: "Đang hoạt động" })).toHaveAttribute("aria-pressed", "true")
  await expect(page.getByText("Dự án đang hoạt động cô lập").first()).toBeVisible()
  await expect(page.getByText("Dự án hotfix cô lập")).toHaveCount(0)
  await page.getByRole("button", { name: "Đã vô hiệu hóa" }).click()
  await expect(page.getByText("Dự án hotfix cô lập").first()).toBeVisible()
  await expect(page.getByText("Dự án đang hoạt động cô lập")).toHaveCount(0)
  await expect(page.getByText("Đã vô hiệu hóa").first()).toBeVisible()
  await page.getByRole("button", { name: "Tất cả" }).click()
  await expect(page.getByText("Dự án hotfix cô lập").first()).toBeVisible()
  await expect(page.getByText("Dự án đang hoạt động cô lập").first()).toBeVisible()
  await page.getByRole("button", { name: "Đã vô hiệu hóa" }).click()
  await page.getByRole("button", { name: "Kích hoạt lại" }).first().click()
  await expect(page.getByRole("heading", { name: "Kích hoạt lại dự án?" })).toBeVisible()
  await page.getByRole("button", { name: "Kích hoạt lại" }).last().click()
  await expect(page.getByText("Dự án hotfix cô lập")).toHaveCount(0)
  await page.getByRole("button", { name: "Đang hoạt động" }).click()
  await expect(page.getByText("Dự án hotfix cô lập").first()).toBeVisible()
  await expect(page).toHaveURL(/\/admin\/users\/990001$/)
})
