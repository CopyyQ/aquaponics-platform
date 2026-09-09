import { useState } from "react"
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { AlertTriangle, Check, CheckCircle2 } from "lucide-react"
import { useParams } from "react-router-dom"
import { acknowledgeAlert, listAlerts, queryKeys, resolveAlert } from "@/api/resources"
import { useAuth } from "@/app/auth"
import { Badge } from "@/shared/ui/badge"
import { Button } from "@/shared/ui/button"
import { Card, CardContent } from "@/shared/ui/card"
import { EmptyState } from "@/shared/ui/empty-state"
import { Input } from "@/shared/ui/input"
import { Skeleton } from "@/shared/ui/skeleton"
import { StatusBadge } from "@/shared/ui/status-badge"
import { errorMessage } from "@/api/client"

export function AlertsPage() {
  const systemId = Number(useParams().systemId); const { can } = useAuth(); const client = useQueryClient(); const [note, setNote] = useState<Record<number, string>>({})
  const alerts = useQuery({ queryKey: queryKeys.alerts(systemId), queryFn: () => listAlerts(systemId) })
  const ack = useMutation({ mutationFn: (id: number) => acknowledgeAlert(systemId, id), onSuccess: () => void client.invalidateQueries({ queryKey: queryKeys.alerts(systemId) }) })
  const resolve = useMutation({ mutationFn: (id: number) => resolveAlert(systemId, id, { resolution_note: note[id]?.trim() || "Đã kiểm tra và xử lý từ giao diện vận hành" }), onSuccess: () => void client.invalidateQueries({ queryKey: queryKeys.alerts(systemId) }) })
  if (alerts.isLoading) return <Skeleton className="h-96" />
  if (alerts.isError) return <EmptyState icon={AlertTriangle} title="Không thể tải cảnh báo" description={errorMessage(alerts.error)} />
  return <div className="space-y-5"><div><h2 className="text-xl font-semibold">Cảnh báo vận hành</h2><p className="text-sm text-muted-foreground">Cảnh báo Sensor và Actuator trong phạm vi hệ thống.</p></div>{alerts.data?.length ? <div className="space-y-3">{alerts.data.map((alert) => <Card key={alert.id}><CardContent className="flex flex-col gap-4 p-5"><div className="flex flex-wrap items-start justify-between gap-3"><div className="flex items-start gap-3"><div className="rounded-xl bg-amber-500/10 p-3 text-amber-600"><AlertTriangle className="size-5" aria-hidden="true" /></div><div><div className="flex flex-wrap items-center gap-2"><Badge variant={alert.severity === "CRITICAL" ? "destructive" : "warning"}>{alert.severity}</Badge><StatusBadge value={alert.status} /><span className="text-xs text-muted-foreground">{alert.resource_type} · {alert.metric}</span></div><p className="mt-2 font-medium">{alert.message}</p><p className="mt-1 text-xs text-muted-foreground">Giá trị {alert.actual_value ?? "—"} · Ngưỡng {alert.threshold_value ?? "—"} · {new Date(alert.started_at).toLocaleString("vi-VN")}</p></div></div><span className="text-xs text-muted-foreground">{alert.condition_active ? "Điều kiện còn hoạt động" : "Điều kiện đã bình thường"}</span></div>{alert.status !== "RESOLVED" ? <div className="flex flex-wrap items-center justify-end gap-2">{alert.status === "OPEN" && can("incidents.acknowledge") ? <Button size="sm" variant="outline" onClick={() => ack.mutate(alert.id)} disabled={ack.isPending}><Check />Xác nhận</Button> : null}{can("incidents.resolve") ? <><Input className="w-64" placeholder="Ghi chú xử lý (tuỳ chọn)" value={note[alert.id] ?? ""} onChange={(event) => setNote((current) => ({ ...current, [alert.id]: event.target.value }))} /><Button size="sm" onClick={() => resolve.mutate(alert.id)} disabled={resolve.isPending}><CheckCircle2 />Khắc phục</Button></> : null}</div> : null}</CardContent></Card>)}</div> : <EmptyState icon={CheckCircle2} title="Không có cảnh báo" description="Hệ thống hiện không có cảnh báo cần xử lý." />}</div>
}
