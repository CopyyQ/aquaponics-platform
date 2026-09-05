import { defineConfig, devices } from "@playwright/test"

const remoteRuntime = Boolean(process.env.PLAYWRIGHT_BASE_URL)
const baseURL = process.env.PLAYWRIGHT_BASE_URL ?? "http://localhost:3000"

export default defineConfig({
  testDir: "./e2e",
  fullyParallel: false,
  forbidOnly: Boolean(process.env.CI),
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,
  reporter: [["list"], ["html", { open: "never" }]],
  use: {
    baseURL,
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
    video: "retain-on-failure",
  },
  webServer: remoteRuntime ? undefined : {
    command: "npm run dev -- --host 0.0.0.0",
    url: baseURL,
    reuseExistingServer: !process.env.CI,
  },
  projects: [
    { name: "public-gateway", testMatch: /public-monitoring-gateway\.spec\.ts/, use: { ...devices["Desktop Chrome"] } },
    { name: "setup", testMatch: /auth\.setup\.ts/ },
    { name: "chromium", use: { ...devices["Desktop Chrome"], storageState: "playwright/.auth/admin.json" }, dependencies: ["setup"] },
    { name: "firefox-smoke", grep: /@smoke/, use: { ...devices["Desktop Firefox"], storageState: "playwright/.auth/admin.json" }, dependencies: ["setup"] },
    { name: "webkit-smoke", grep: /@smoke/, use: { ...devices["Desktop Safari"], storageState: "playwright/.auth/admin.json" }, dependencies: ["setup"] },
  ],
})
