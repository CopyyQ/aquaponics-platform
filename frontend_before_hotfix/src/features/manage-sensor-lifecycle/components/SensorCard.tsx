import { Link } from "react-router-dom"
import { Activity, ArrowRight, BellRing } from "lucide-react"
import { useMutation, useQueryClient } from "@tanstack/react-query"
import { toast } from "sonner"
import type { Sensor } from "@/entities/sensor/model/types"
import { formatRelative } from "@/shared/lib/date"
import { Button } from "@/shared/ui/button"
import { Badge } from "@/shared/ui/badge"
import { Card, CardContent, CardHeader, CardTitle } from "@/shared/ui/card"
import { StatusBadge } from "@/shared/ui/status-badge"
import { EditSensorDialog } from "@/features/edit-sensor/components/EditSensorDialog"
import { sensorApi } from "@/entities/sensor/api/sensor-api"
import { useProtectedQueryScope } from "@/features/auth/model/use-protected-query-scope"
import { invalidateQueries } from "@/shared/api/query-invalidation"

export function SensorCard({ sensor, projectId, unit, admin = false }: { sensor: Sensor; projectId: number; unit?: string; admin?: boolean }) {
  const detailPath = `${admin ? "/admin" : ""}/projects/${projectId}/devices/${sensor.device_id}/sensors/${sensor.id}`
  const client = useQueryClient()
  const { queryScope } = useProtectedQueryScope()
  const lifecycle = useMutation({ mutationFn: () => sensor.is_enabled ? sensorApi.disableFromDevice(sensor.device_id, sensor.id, "Tắt từ trang quản trị") : sensorApi.activateToDevice(sensor.device_id, sensor.id), onSuccess: async () => { await invalidateQueries.sensors(client, queryScope, projectId, sensor.device_id, sensor.id); toast.success(sensor.is_enabled ? "Đã vô hiệu hóa cảm biến" : "Đã kích hoạt cảm biến") }, onError: () => toast.error("Không thể cập nhật cảm biến") })
  return <Card className="transition-shadow hover:shadow-md"><CardHeader className="flex-row items-start justify-between"><div className="flex gap-3"><div className="rounded-lg bg-primary/10 p-2.5 text-primary"><Activity className="size-5" /></div><div><CardTitle className="text-base">{sensor.name}</CardTitle><div className="mt-1 font-mono text-xs text-muted-foreground">{sensor.code}</div></div></div><div className="flex flex-wrap gap-2"><Badge variant="secondary">Cảm biến</Badge><StatusBadge value={sensor.status} /></div></CardHeader><CardContent><div className="grid grid-cols-2 gap-3 rounded-lg bg-muted/40 p-3 text-sm"><div><div className="text-xs text-muted-foreground">Ngưỡng dưới</div><div className="font-semibold">{sensor.lower_threshold ?? "—"} {unit}</div></div><div><div className="text-xs text-muted-foreground">Ngưỡng trên</div><div className="font-semibold">{sensor.upper_threshold ?? "—"} {unit}</div></div></div><div className="mt-4 flex flex-wrap items-center justify-between gap-2"><div className="flex items-center gap-1 text-xs text-muted-foreground"><BellRing className="size-3.5" />{sensor.warning_enabled ? "Đang bật cảnh báo" : "Đã tắt cảnh báo"} · {formatRelative(sensor.last_seen_at)}</div>{admin ? <div className="flex flex-wrap gap-2">{sensor.is_enabled ? <><EditSensorDialog sensor={sensor} projectId={projectId} /><Button size="sm" variant="ghost" disabled={lifecycle.isPending} onClick={() => lifecycle.mutate()}>Vô hiệu hóa</Button></> : <Button size="sm" variant="ghost" disabled={lifecycle.isPending} onClick={() => lifecycle.mutate()}>Kích hoạt lại</Button>}</div> : null}<Button asChild variant="ghost" size="sm"><Link to={detailPath}>Chi tiết <ArrowRight /></Link></Button></div></CardContent></Card>
}
