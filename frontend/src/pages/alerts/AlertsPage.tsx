import { useState } from "react"
import { useQuery } from "@tanstack/react-query"
import { BellOff } from "lucide-react"
import { alertApi } from "@/entities/alert/api/alert-api"
import type { AlertStatus } from "@/entities/alert/model/types"
import { AlertTable } from "@/features/alerts/components/alert-table"
import { useAuthStore } from "@/features/auth/model/auth-store"
import { useProtectedQueryScope } from "@/features/auth/model/use-protected-query-scope"
import { queryKeys } from "@/shared/api/query-keys"
import { Card, CardContent } from "@/shared/ui/card"
import { EmptyState } from "@/shared/ui/empty-state"
import { PageHeader } from "@/shared/ui/page-header"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/shared/ui/select"

export function AlertsPage() {
  const role = useAuthStore((state) => state.user?.system_role)
  const { active, queryScope } = useProtectedQueryScope()
  const [status, setStatus] = useState<AlertStatus | "ALL">("ALL")
  const query = useQuery({ queryKey: queryKeys.alerts.list(queryScope, status), queryFn: () => alertApi.list(status === "ALL" ? undefined : { status }), enabled: active, refetchInterval: 30_000 })
  return <div className="space-y-6"><PageHeader title="Cảnh báo" description="Theo dõi riêng trạng thái sự cố và điều kiện đo hiện tại." actions={<Select value={status} onValueChange={(value) => setStatus(value as AlertStatus | "ALL")}><SelectTrigger className="w-48" aria-label="Lọc trạng thái cảnh báo"><SelectValue /></SelectTrigger><SelectContent><SelectItem value="ALL">Tất cả trạng thái</SelectItem><SelectItem value="PENDING">Đang chờ</SelectItem><SelectItem value="OPEN">Đang mở</SelectItem><SelectItem value="ACKNOWLEDGED">Đã xác nhận</SelectItem><SelectItem value="RESOLVED">Đã khắc phục</SelectItem></SelectContent></Select>} />{query.data?.length ? <Card><CardContent className="p-0"><AlertTable alerts={query.data} role={role} /></CardContent></Card> : <EmptyState icon={BellOff} title="Không có cảnh báo" description="Không tìm thấy cảnh báo phù hợp với bộ lọc hiện tại." />}</div>
}
