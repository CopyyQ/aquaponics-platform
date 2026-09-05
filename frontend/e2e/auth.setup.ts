import { expect, test as setup } from "@playwright/test"

const authFile = "playwright/.auth/admin.json"

setup("đăng nhập Admin", async ({ page }) => {
  const username = process.env.E2E_ADMIN_USERNAME
  const password = process.env.E2E_ADMIN_PASSWORD
  if (!username || !password) throw new Error("Thiếu E2E_ADMIN_USERNAME hoặc E2E_ADMIN_PASSWORD")
  await page.goto("/login")
  await page.getByLabel("Tên đăng nhập").fill(username)
  await page.getByLabel("Mật khẩu", { exact: true }).fill(password)
  await page.getByRole("button", { name: "Đăng nhập", exact: true }).click()
  await expect(page).toHaveURL(/\/admin\//)
  await page.context().storageState({ path: authFile })
})
