import type { AlertStatus } from "@/entities/alert/model/types"
import { Badge } from "@/shared/ui/badge"
import { StatusBadge } from "@/shared/ui/status-badge"

export function AlertLifecycleBadge({ status, resolvedByUserId }: { status: AlertStatus; resolvedByUserId: number | null }) {
  if (status === "RESOLVED" && resolvedByUserId === null) {
    return <Badge variant="outline">Kết thúc theo dữ liệu cũ</Badge>
  }
  return <StatusBadge value={status} />
}
