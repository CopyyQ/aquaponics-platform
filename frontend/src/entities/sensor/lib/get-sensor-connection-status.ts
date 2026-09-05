import type { ConnectionStatus } from "@/entities/device/model/types"

export function getSensorConnectionStatus(status: ConnectionStatus | undefined) {
  if (status === "ONLINE") return { label: "Đang kết nối", tone: "success" as const }
  if (status === "OFFLINE") return { label: "Mất kết nối", tone: "offline" as const }
  if (status === "DISABLED") return { label: "Đã tắt", tone: "neutral" as const }
  return { label: "Chờ kết nối", tone: "warning" as const }
}
