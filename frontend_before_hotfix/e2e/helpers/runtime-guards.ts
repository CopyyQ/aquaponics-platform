import { expect, type Page, type TestInfo } from "@playwright/test"

export function guardRuntime(page: Page, testInfo: TestInfo) {
  const errors: string[] = []
  page.on("pageerror", (error) => errors.push(`pageerror: ${error.message}`))
  page.on("console", (message) => {
    if (message.type() === "error") errors.push(`console: ${message.text()}`)
  })
  page.on("response", (response) => {
    if (response.status() >= 500) errors.push(`HTTP ${response.status()}: ${response.url()}`)
  })
  page.on("requestfailed", (request) => {
    if (request.resourceType() === "xhr" || request.resourceType() === "fetch") errors.push(`requestfailed: ${request.url()} ${request.failure()?.errorText ?? ""}`)
  })
  return async () => {
    if (errors.length) await testInfo.attach("runtime-errors", { body: errors.join("\n"), contentType: "text/plain" })
    expect(errors, errors.join("\n")).toEqual([])
  }
}
