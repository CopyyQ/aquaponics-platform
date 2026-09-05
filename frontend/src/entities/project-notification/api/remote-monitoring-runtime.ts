export interface RemoteMonitoringRuntime {
  status: "running" | "starting" | "stopped" | "unavailable" | "gateway-unavailable"
  url: string
  gateway_url: string
}

const runtimePath = "/runtime/public-monitoring/tunnel.json"

export async function getRemoteMonitoringRuntime(): Promise<RemoteMonitoringRuntime | null> {
  const response = await fetch(`${runtimePath}?t=${Date.now()}`, { cache: "no-store" })
  if (!response.ok) return null
  const value = await response.json() as Partial<RemoteMonitoringRuntime>
  const validUrl = typeof value.url === "string"
    && /^https:\/\/[a-z0-9-]+\.trycloudflare\.com\/?$/i.test(value.url)
  return {
    status: value.status ?? "stopped",
    url: validUrl ? value.url! : "",
    gateway_url: typeof value.gateway_url === "string" ? value.gateway_url : "",
  }
}
