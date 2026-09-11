import { useState } from "react"
import { useQuery } from "@tanstack/react-query"
import { BellOff } from "lucide-react"
import { useNavigate } from "react-router-dom"

import { AlertLifecycleBadge } from "@/entities/alert/ui/AlertLifecycleBadge"
import { adminAlertApi } from "@/features/admin-alerts/api/admin-alert-api"
import { AlertDetailSheet } from "@/features/admin-alerts/components/AlertDetailSheet"
import { useProtectedQueryScope } from "@/features/auth/model/use-protected-query-scope"
import { queryKeys } from "@/shared/api/query-keys"
import { formatDateTime } from "@/shared/lib/date"
import { Card, CardContent } from "@/shared/ui/card"
import { EmptyState } from "@/shared/ui/empty-state"
import { PageHeader } from "@/shared/ui/page-header"
import { Select, SelectContent, SelectGroup, SelectItem, SelectTrigger, SelectValue } from "@/shared/ui/select"
import { StatusBadge } from "@/shared/ui/status-badge"
import { Switch } from "@/shared/ui/switch"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/shared/ui/table"

export function AdminAlertsPage() {
  const navigate = useNavigate()
  const [severity, setSeverity] = useState("ALL")
  const [status, setStatus] = useState("ALL")
  const [unacknowledged, setUnacknowledged] = useState(false)
  const [selected, setSelected] = useState<number | null>(null)
  const { active, queryScope } = useProtectedQueryScope()
  const query = useQuery({ queryKey: queryKeys.alerts.adminList(queryScope, { severity, status, unacknowledged }), queryFn: () => adminAlertApi.list(severity, status, unacknowledged), enabled: active, refetchInterval: 10_000 })
  const openAlert = (id: number) => setSelected(id)

  return <div className="flex flex-col gap-6">
    <PageHeader title="Cảnh báo toàn hệ thống" description="Phân biệt sự cố chưa xử lý với điều kiện đo hiện tại." />
    <div className="flex flex-col gap-3 rounded-xl border bg-card p-3 sm:flex-row sm:items-center">
      <Select value={severity} onValueChange={setSeverity}><SelectTrigger className="sm:w-48" aria-label="Lọc mức độ cảnh báo"><SelectValue /></SelectTrigger><SelectContent><SelectGroup><SelectItem value="ALL">Mọi mức độ</SelectItem><SelectItem value="CRITICAL">Nghiêm trọng</SelectItem><SelectItem value="WARNING">Cảnh báo</SelectItem></SelectGroup></SelectContent></Select>
      <Select value={status} onValueChange={setStatus}><SelectTrigger className="sm:w-48" aria-label="Lọc trạng thái cảnh báo"><SelectValue /></SelectTrigger><SelectContent><SelectGroup><SelectItem value="ALL">Mọi trạng thái</SelectItem><SelectItem value="PENDING">Đang chờ</SelectItem><SelectItem value="OPEN">Đang mở</SelectItem><SelectItem value="ACKNOWLEDGED">Đã xác nhận</SelectItem><SelectItem value="RESOLVED">Đã kết thúc</SelectItem></SelectGroup></SelectContent></Select>
      <label className="flex items-center gap-2 text-sm"><Switch checked={unacknowledged} onCheckedChange={setUnacknowledged} />Chưa xác nhận</label>
      <span className="ml-auto text-sm text-muted-foreground">{query.data?.total ?? 0} cảnh báo</span>
    </div>
    {query.data?.items.length ? <Card><CardContent className="overflow-x-auto p-0"><Table><TableHeader><TableRow><TableHead>Mức độ</TableHead><TableHead>Loại</TableHead><TableHead>Project</TableHead><TableHead>Khách hàng</TableHead><TableHead>Thiết bị</TableHead><TableHead>Cảm biến</TableHead><TableHead>Giá trị / ngưỡng</TableHead><TableHead>Bắt đầu</TableHead><TableHead>Trạng thái</TableHead></TableRow></TableHeader><TableBody>{query.data.items.map((alert) => <TableRow key={alert.id} role="button" tabIndex={0} className="cursor-pointer hover:bg-accent focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-ring" onClick={() => openAlert(alert.id)} onKeyDown={(event) => { if (event.key === "Enter" || event.key === " ") { event.preventDefault(); openAlert(alert.id) } }}><TableCell><StatusBadge value={alert.severity} /></TableCell><TableCell>{alert.alert_type}</TableCell><TableCell><button className="font-medium hover:underline" onClick={(event) => { event.stopPropagation(); navigate(`/admin/projects/${alert.project.id}/overview`) }}>{alert.project.name}</button></TableCell><TableCell><button className="hover:underline" onClick={(event) => { event.stopPropagation(); navigate(`/admin/users/${alert.customer.id}`) }}>{alert.customer.full_name}</button></TableCell><TableCell>{alert.device.name}</TableCell><TableCell>{alert.sensor.name}</TableCell><TableCell>{alert.trigger_value ?? "—"} / {alert.threshold.lower ?? "—"}–{alert.threshold.upper ?? "—"}</TableCell><TableCell>{formatDateTime(alert.started_at)}</TableCell><TableCell><div className="space-y-1"><AlertLifecycleBadge status={alert.status} resolvedByUserId={alert.resolved_by_user_id} />{alert.status !== "RESOLVED" ? <p className="text-xs text-muted-foreground">{alert.condition_active ? "Vẫn bất thường" : "Đã bình thường · Chờ xác nhận"}</p> : null}</div></TableCell></TableRow>)}</TableBody></Table></CardContent></Card> : <EmptyState icon={BellOff} title={query.isError ? "Không thể tải cảnh báo" : "Không có cảnh báo phù hợp"} description={query.isError ? "Kiểm tra kết nối Backend." : "Hãy thay đổi bộ lọc hiện tại."} />}
    <AlertDetailSheet alertId={selected} open={selected !== null} onOpenChange={(nextOpen) => { if (!nextOpen) setSelected(null) }} />
  </div>
}
