import { defineConfig, devices } from "@playwright/test"

const remoteRuntime = Boolean(process.env.PLAYWRIGHT_BASE_URL)
const baseURL = process.env.PLAYWRIGHT_BASE_URL ?? "http://127.0.0.1:4174"

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
    command: "npm run dev -- --host 127.0.0.1 --port 4174 --strictPort",
    url: baseURL,
    reuseExistingServer: false,
  },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
})
