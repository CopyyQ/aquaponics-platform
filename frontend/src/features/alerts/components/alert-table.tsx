import { useState } from "react"
import { useMutation, useQueryClient } from "@tanstack/react-query"
import { CheckCheck, CircleCheckBig } from "lucide-react"
import { toast } from "sonner"
import type { Alert } from "@/entities/alert/model/types"
import { alertApi } from "@/entities/alert/api/alert-api"
import { ResolveAlertDialog } from "@/entities/alert/ui/ResolveAlertDialog"
import { AlertLifecycleBadge } from "@/entities/alert/ui/AlertLifecycleBadge"
import { useProtectedQueryScope } from "@/features/auth/model/use-protected-query-scope"
import { invalidateQueries } from "@/shared/api/query-invalidation"
import { queryKeys } from "@/shared/api/query-keys"
import type { UserRole } from "@/entities/user/model/types"
import { canResolveAlerts } from "@/features/auth/lib/permission-policy"
import { formatDateTime } from "@/shared/lib/date"
import { Button } from "@/shared/ui/button"
import { StatusBadge } from "@/shared/ui/status-badge"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/shared/ui/table"

export function AlertTable({ alerts, role }: { alerts: Alert[]; role?: UserRole }) {
  const [selectedAlert, setSelectedAlert] = useState<Alert | null>(null)
  const queryClient = useQueryClient()
  const { queryScope } = useProtectedQueryScope()
  const updateAlertCache = (result: Alert) => {
    queryClient.setQueriesData<Alert[]>({ queryKey: queryKeys.alerts.all }, (current) => current?.map((item) => item.id === result.id ? result : item))
  }
  const acknowledge = useMutation({ mutationFn: alertApi.acknowledge, onSuccess: async (result) => { updateAlertCache(result); await invalidateQueries.alerts(queryClient, queryScope, undefined, result.id); toast.success("Đã xác nhận cảnh báo") }, onError: () => toast.error("Không thể xác nhận cảnh báo") })
  const resolve = useMutation({ mutationFn: alertApi.resolve, onSuccess: async (result) => { updateAlertCache(result); await invalidateQueries.alerts(queryClient, queryScope, undefined, result.id); setSelectedAlert(null); toast.success("Đã xác nhận cảnh báo được khắc phục") }, onError: () => toast.error("Không thể xác nhận khắc phục cảnh báo") })
  const pending = acknowledge.isPending || resolve.isPending
  return <>
    <Table><TableHeader><TableRow><TableHead>Thời gian</TableHead><TableHead>Nội dung</TableHead><TableHead>Mức độ</TableHead><TableHead>Trạng thái</TableHead><TableHead className="text-right">Thao tác</TableHead></TableRow></TableHeader><TableBody>{alerts.map((alert) => <TableRow key={alert.id}><TableCell className="whitespace-nowrap text-muted-foreground">{formatDateTime(alert.started_at)}</TableCell><TableCell><div className="font-medium">{alert.message}</div>{alert.trigger_value !== null && <div className="mt-1 text-xs text-muted-foreground">Giá trị gần nhất: {alert.trigger_value}</div>}</TableCell><TableCell><StatusBadge value={alert.severity} /></TableCell><TableCell><div className="space-y-1"><AlertLifecycleBadge status={alert.status} resolvedByUserId={alert.resolved_by_user_id} />{alert.status !== "RESOLVED" ? <p className="text-xs text-muted-foreground">{alert.condition_active ? "Điều kiện hiện tại: Vẫn bất thường" : "Đã trở về ngưỡng bình thường · Chờ xác nhận khắc phục"}</p> : alert.resolved_by_user_id !== null ? <p className="text-xs text-muted-foreground">Xác nhận bởi {alert.resolved_by_name || `User #${alert.resolved_by_user_id}`}</p> : <p className="text-xs text-muted-foreground">Không có thông tin người xác nhận trong dữ liệu lịch sử.</p>}</div></TableCell><TableCell><div className="flex justify-end gap-2">{canResolveAlerts(role) && alert.status !== "RESOLVED" && <>{alert.status !== "ACKNOWLEDGED" && <Button variant="outline" size="sm" disabled={pending} onClick={() => acknowledge.mutate(alert.id)}><CheckCheck />{acknowledge.isPending ? "Đang lưu…" : "Xác nhận đã xem"}</Button>}<Button size="sm" disabled={pending} onClick={() => setSelectedAlert(alert)}><CircleCheckBig />Xác nhận đã khắc phục</Button></>}</div></TableCell></TableRow>)}</TableBody></Table>
    <ResolveAlertDialog
      open={selectedAlert !== null}
      onOpenChange={(open) => { if (!open) setSelectedAlert(null) }}
      conditionActive={selectedAlert?.condition_active ?? false}
      currentValue={selectedAlert?.trigger_value ?? null}
      actorName={null}
      pending={resolve.isPending}
      onConfirm={(resolutionNote) => {
        if (selectedAlert) resolve.mutate({ id: selectedAlert.id, resolutionNote })
      }}
    />
  </>
}
