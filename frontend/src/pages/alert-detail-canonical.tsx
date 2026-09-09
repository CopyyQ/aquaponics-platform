import { useState } from "react"
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { AlertTriangle, ArrowLeft, Check, CheckCircle2 } from "lucide-react"
import { Link, useParams } from "react-router-dom"
import { acknowledgeAlert, getAlert, queryKeys, resolveAlert } from "@/api/resources"
import { errorMessage } from "@/api/client"
import { useAuth } from "@/app/auth"
import { Badge } from "@/shared/ui/badge"
import { Button } from "@/shared/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/shared/ui/card"
import { EmptyState } from "@/shared/ui/empty-state"
import { Label } from "@/shared/ui/label"
import { Skeleton } from "@/shared/ui/skeleton"
import { StatusBadge } from "@/shared/ui/status-badge"
import { Textarea } from "@/shared/ui/textarea"

export function AlertDetailPage() {
  const params = useParams()
  const systemId = Number(params.systemId)
  const alertId = Number(params.alertId)
  const validIds = systemId > 0 && alertId > 0
  const { can } = useAuth()
  const client = useQueryClient()
  const [note, setNote] = useState("")
  const alert = useQuery({ queryKey: queryKeys.alert(systemId, alertId), queryFn: () => getAlert(systemId, alertId), enabled: validIds })
  const refresh = async () => { await Promise.all([client.invalidateQueries({ queryKey: queryKeys.alert(systemId, alertId) }), client.invalidateQueries({ queryKey: queryKeys.alerts(systemId) }), client.invalidateQueries({ queryKey: queryKeys.monitoringLatest(systemId) }), client.invalidateQueries({ queryKey: queryKeys.scada(systemId) })]) }
  const ack = useMutation({ mutationFn: () => acknowledgeAlert(systemId, alertId), onSuccess: refresh })
  const resolve = useMutation({ mutationFn: () => resolveAlert(systemId, alertId, { resolution_note: note.trim() }), onSuccess: refresh })
  if (!validIds) return <EmptyState icon={AlertTriangle} title="Đường dẫn Alert không hợp lệ" description="System và Alert ID phải là số nguyên dương." />
  if (alert.isLoading) return <Skeleton className="h-96" />
  if (alert.isError || !alert.data) return <EmptyState icon={AlertTriangle} title="Không thể tải Alert" description={errorMessage(alert.error)} />
  const value = alert.data
  const sourceLink = value.device_id && value.resource_type === "SENSOR" && value.sensor_id ? `/aquaponics-systems/${systemId}/devices/${value.device_id}/sensors/${value.sensor_id}` : value.device_id && value.resource_type === "ACTUATOR" && value.actuator_id ? `/aquaponics-systems/${systemId}/devices/${value.device_id}/actuators/${value.actuator_id}` : null
  return <div className="max-w-4xl space-y-5"><Link className="inline-flex items-center gap-2 text-sm text-primary hover:underline" to={`/aquaponics-systems/${systemId}/alerts`}><ArrowLeft className="size-4" />Danh sách Alert</Link><div className="flex flex-wrap items-start justify-between gap-3"><div><div className="flex flex-wrap items-center gap-2"><Badge variant={value.severity === "CRITICAL" ? "destructive" : "warning"}>{value.severity}</Badge><StatusBadge value={value.status} /><StatusBadge value={value.resource_type} /></div><h2 className="mt-3 text-2xl font-semibold">{value.message}</h2><p className="mt-1 text-sm text-muted-foreground">{value.alert_type} · {value.metric} · {value.direction ?? "Không có hướng"}</p></div><span className="text-sm text-muted-foreground">#{value.id}</span></div><div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4"><Info label="Giá trị thực tế" value={value.actual_value === null ? "—" : String(value.actual_value)} /><Info label="Ngưỡng" value={value.threshold_value === null ? "—" : String(value.threshold_value)} /><Info label="Risk" value={value.risk_level} /><Info label="Số lần" value={String(value.occurrence_count)} /></div><Card><CardHeader><CardTitle>Nguồn và vòng đời</CardTitle></CardHeader><CardContent className="grid gap-4 sm:grid-cols-2"><Info label="Resource" value={`${value.resource_type} #${value.sensor_id ?? value.actuator_id ?? "—"}`} /><Info label="Device" value={value.device_id ? `#${value.device_id}` : "—"} /><Info label="Bắt đầu" value={new Date(value.started_at).toLocaleString("vi-VN")} /><Info label="Kích hoạt gần nhất" value={new Date(value.last_triggered_at).toLocaleString("vi-VN")} /><Info label="Bình thường hoá" value={value.normalized_at ? new Date(value.normalized_at).toLocaleString("vi-VN") : value.condition_active ? "Điều kiện còn hoạt động" : "—"} /><Info label="Khắc phục" value={value.resolved_at ? new Date(value.resolved_at).toLocaleString("vi-VN") : "Chưa xác nhận"} />{sourceLink ? <Link className="text-sm font-medium text-primary hover:underline sm:col-span-2" to={sourceLink}>Mở {value.resource_type === "SENSOR" ? "Sensor" : "Actuator"} nguồn</Link> : null}</CardContent></Card>{value.status !== "RESOLVED" ? <Card><CardHeader><CardTitle>Thao tác vận hành</CardTitle></CardHeader><CardContent className="space-y-4">{can("incidents.acknowledge") && value.status !== "ACKNOWLEDGED" && value.status !== "NORMALIZED" ? <Button variant="outline" onClick={() => ack.mutate()} disabled={ack.isPending}><Check />Xác nhận đã xem</Button> : null}{can("incidents.resolve") ? <div className="space-y-3"><div><Label htmlFor="resolution-note">Ghi chú khắc phục</Label><Textarea id="resolution-note" className="mt-1" value={note} onChange={(event) => setNote(event.target.value)} placeholder="Mô tả việc kiểm tra và xử lý (ít nhất 3 ký tự)" /></div><Button onClick={() => resolve.mutate()} disabled={value.condition_active || note.trim().length < 3 || resolve.isPending}><CheckCircle2 />Xác nhận khắc phục</Button>{value.condition_active ? <p className="text-sm text-amber-700 dark:text-amber-300">Chỉ xác nhận khắc phục sau khi điều kiện đã trở về bình thường.</p> : null}</div> : null}{ack.isError || resolve.isError ? <p role="alert" className="text-sm text-destructive">{errorMessage(ack.error ?? resolve.error)}</p> : null}</CardContent></Card> : <Card><CardContent className="p-5"><p className="font-medium">Đã khắc phục bởi {value.resolved_by_name ?? `User #${value.resolved_by_user_id ?? "—"}`}</p><p className="mt-1 text-sm text-muted-foreground">{value.resolution_note ?? "Không có ghi chú"}</p></CardContent></Card>}</div>
}

function Info({ label, value }: { label: string; value: string }) { return <div><p className="text-xs text-muted-foreground">{label}</p><p className="mt-1 font-medium">{value}</p></div> }
