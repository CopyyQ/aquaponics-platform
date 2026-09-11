import type { UserStatus } from "@/entities/user/model/types"
import { StatusBadge } from "@/shared/ui/status-badge"

export function AccountStatusBadge({ status }: { status: UserStatus }) {
  return <StatusBadge value={status} />
}
