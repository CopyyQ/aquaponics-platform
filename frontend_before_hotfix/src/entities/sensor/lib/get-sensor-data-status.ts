import type { ConnectionStatus } from "@/entities/device/model/types"

export function getSensorDataStatus(
  latestAt: string | null,
  status: ConnectionStatus,
) {
  if (latestAt === null) return { label: "Chưa có dữ liệu", tone: "neutral" as const }
  if (status === "OFFLINE") return { label: "Mất dữ liệu", tone: "danger" as const }
  if (status === "WAITING_CONNECTION") {
    return { label: "Mất dữ liệu", tone: "warning" as const }
  }
  return { label: "Đang nhận dữ liệu", tone: "success" as const }
}
