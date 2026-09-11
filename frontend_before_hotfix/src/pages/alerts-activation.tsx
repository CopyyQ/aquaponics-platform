import { useState } from "react"
import { useQuery } from "@tanstack/react-query"
import { AlertTriangle, CheckCircle2 } from "lucide-react"
import { Link, useParams } from "react-router-dom"
import { listAlerts, queryKeys } from "@/api/resources"
import type { AlertLifecycleStatus } from "@/api/contracts"
import { errorMessage } from "@/api/client"
import { Badge } from "@/shared/ui/badge"
import { Card, CardContent } from "@/shared/ui/card"
import { EmptyState } from "@/shared/ui/empty-state"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/shared/ui/select"
import { Skeleton } from "@/shared/ui/skeleton"
import { StatusBadge } from "@/shared/ui/status-badge"

const statuses: readonly AlertLifecycleStatus[] = ["PENDING", "OPEN", "ACKNOWLEDGED", "NORMALIZED", "RESOLVED"]
function isAlertStatus(value: string): value is AlertLifecycleStatus { return statuses.some((status) => status === value) }

export function AlertsPage() {
  const systemId = useParams().systemId ?? ""
  const validId = Boolean(systemId)
  const [status, setStatus] = useState<AlertLifecycleStatus | "ALL">("ALL")
  const alerts = useQuery({ queryKey: [...queryKeys.alerts(systemId), status], queryFn: () => listAlerts(systemId, status === "ALL" ? undefined : status), enabled: validId })
  if (!validId) return <EmptyState icon={AlertTriangle} title="Đường dẫn hệ thống không hợp lệ" description="System ID phải là số nguyên dương." />
  return <div className="space-y-5"><div className="flex flex-wrap items-start justify-between gap-3"><div><h2 className="text-xl font-semibold">Cảnh báo vận hành</h2><p className="text-sm text-muted-foreground">Alert từ Sensor và Actuator trong phạm vi hệ thống. Điều kiện bình thường hoá và xác nhận khắc phục là hai trạng thái riêng.</p></div><Select value={status} onValueChange={(value) => { if (value === "ALL" || isAlertStatus(value)) setStatus(value) }}><SelectTrigger className="w-52" aria-label="Lọc trạng thái Alert"><SelectValue /></SelectTrigger><SelectContent><SelectItem value="ALL">Tất cả trạng thái</SelectItem>{statuses.map((value) => <SelectItem key={value} value={value}>{value}</SelectItem>)}</SelectContent></Select></div>{alerts.isLoading ? <Skeleton className="h-96" /> : alerts.isError ? <EmptyState icon={AlertTriangle} title="Không thể tải cảnh báo" description={errorMessage(alerts.error)} /> : alerts.data?.length ? <div className="space-y-3">{alerts.data.map((alert) => <Link key={alert.id} to={`/aquaponics-systems/${systemId}/alerts/${alert.id}`}><Card className="transition-colors hover:border-primary"><CardContent className="flex flex-col gap-4 p-5"><div className="flex flex-wrap items-start justify-between gap-3"><div className="flex items-start gap-3"><div className="rounded-xl bg-amber-500/10 p-3 text-amber-600"><AlertTriangle className="size-5" aria-hidden="true" /></div><div><div className="flex flex-wrap items-center gap-2"><Badge variant={alert.severity === "CRITICAL" ? "destructive" : "warning"}>{alert.severity}</Badge><StatusBadge value={alert.status} /><span className="text-xs text-muted-foreground">{alert.resource_type} · {alert.metric}</span></div><p className="mt-2 font-medium">{alert.message}</p><p className="mt-1 text-xs text-muted-foreground">Giá trị {alert.actual_value ?? "—"} · Ngưỡng {alert.threshold_value ?? "—"} · {new Date(alert.started_at).toLocaleString("vi-VN")}</p></div></div><span className="text-xs text-muted-foreground">{alert.condition_active ? "Điều kiện còn hoạt động" : alert.status === "RESOLVED" ? "Đã xác nhận khắc phục" : "Đã trở về ngưỡng bình thường"}</span></div></CardContent></Card></Link>)}</div> : <EmptyState icon={CheckCircle2} title="Không có cảnh báo" description="Không có Alert phù hợp với bộ lọc hiện tại." />}</div>
}
