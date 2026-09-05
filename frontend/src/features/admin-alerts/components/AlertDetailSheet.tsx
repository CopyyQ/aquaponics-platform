import { useState } from "react"
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { CheckCheck, CircleCheckBig, ExternalLink } from "lucide-react"
import { useNavigate } from "react-router-dom"
import { toast } from "sonner"

import { ResolveAlertDialog } from "@/entities/alert/ui/ResolveAlertDialog"
import { AlertLifecycleBadge } from "@/entities/alert/ui/AlertLifecycleBadge"
import { adminAlertApi } from "@/features/admin-alerts/api/admin-alert-api"
import { useAuthStore } from "@/features/auth/model/auth-store"
import { useProtectedQueryScope } from "@/features/auth/model/use-protected-query-scope"
import { invalidateQueries } from "@/shared/api/query-invalidation"
import { queryKeys } from "@/shared/api/query-keys"
import { formatDateTime } from "@/shared/lib/date"
import { Button } from "@/shared/ui/button"
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/shared/ui/dialog"
import { Skeleton } from "@/shared/ui/skeleton"
import { StatusBadge } from "@/shared/ui/status-badge"

export function AlertDetailSheet({ alertId, open, onOpenChange }: { alertId: number | null; open: boolean; onOpenChange: (open: boolean) => void }) {
  const [resolutionOpen, setResolutionOpen] = useState(false)
  const navigate = useNavigate()
  const client = useQueryClient()
  const actorName = useAuthStore((state) => state.user?.full_name)
  const { queryScope } = useProtectedQueryScope()
  const query = useQuery({
    queryKey: queryKeys.alerts.adminDetail(alertId as number),
    queryFn: () => adminAlertApi.get(alertId as number),
    enabled: open && alertId !== null,
  })
  const mutationOptions = {
    onSuccess: async (result: Awaited<ReturnType<typeof adminAlertApi.acknowledge>>) => {
      client.setQueryData(queryKeys.alerts.adminDetail(result.id), result)
      await invalidateQueries.alerts(client, queryScope, result.project.id, result.id)
      toast.success("Đã cập nhật cảnh báo")
    },
    onError: () => toast.error("Không thể cập nhật cảnh báo"),
  }
  const acknowledge = useMutation({ mutationFn: () => adminAlertApi.acknowledge(alertId as number), ...mutationOptions })
  const resolve = useMutation({
    mutationFn: (resolutionNote: string) => adminAlertApi.resolve({ id: alertId as number, resolutionNote }),
    onSuccess: async (result) => {
      client.setQueryData(queryKeys.alerts.adminDetail(result.id), result)
      await invalidateQueries.alerts(client, queryScope, result.project.id, result.id)
      setResolutionOpen(false)
      toast.success("Đã xác nhận cảnh báo được khắc phục")
    },
    onError: () => toast.error("Không thể xác nhận khắc phục cảnh báo"),
  })
  const alert = query.data

  return <>
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="right-0 left-auto top-0 h-screen max-w-2xl translate-x-0 translate-y-0 overflow-y-auto rounded-none sm:w-[42rem]">
        <DialogHeader>
          <DialogTitle>Chi tiết cảnh báo</DialogTitle>
          <DialogDescription>Phân biệt trạng thái sự cố với điều kiện đo hiện tại.</DialogDescription>
        </DialogHeader>
        {query.isLoading ? <Skeleton className="h-96" /> : alert ? <div className="flex flex-col gap-6">
          <div className="flex flex-wrap gap-2"><StatusBadge value={alert.severity} /><AlertLifecycleBadge status={alert.status} resolvedByUserId={alert.resolved_by_user_id} /></div>
          {alert.status !== "RESOLVED" ? <div className="rounded-lg border bg-muted/30 p-4">
            <p className="font-medium">Cảnh báo: Đang mở</p>
            <p className="mt-1 text-sm text-muted-foreground">Điều kiện hiện tại: {alert.condition_active ? "Vẫn bất thường" : "Đã trở về ngưỡng bình thường"}</p>
            {!alert.condition_active ? <p className="mt-1 text-sm font-medium text-amber-700 dark:text-amber-300">Chờ xác nhận khắc phục</p> : null}
          </div> : <div className="rounded-lg border bg-muted/30 p-4">
            {alert.resolved_by_user_id !== null ? <><p className="font-medium">Cảnh báo: Đã khắc phục</p><p className="mt-2 text-sm">Xác nhận bởi: <strong>{alert.resolved_by_name || `User #${alert.resolved_by_user_id}`}</strong></p><p className="text-sm">Thời gian: {formatDateTime(alert.resolved_at)}</p><p className="text-sm">Ghi chú: {alert.resolution_note || "—"}</p></> : <><p className="font-medium">Bản ghi đã kết thúc theo cơ chế cũ</p><p className="mt-2 text-sm text-muted-foreground">Không có actor hoặc ghi chú xác nhận; hệ thống không coi đây là bằng chứng người vận hành đã khắc phục.</p></>}
          </div>}
          <dl className="grid gap-4 sm:grid-cols-2">
            {[["Project", alert.project.name], ["Khách hàng", alert.customer.full_name], ["Thiết bị", `${alert.device.name} (${alert.device.code})`], ["Cảm biến", `${alert.sensor.name} (${alert.sensor.unit})`], ["Giá trị quan sát", alert.current_value ?? alert.trigger_value ?? "—"], ["Ngưỡng", `${alert.threshold.lower ?? "—"} – ${alert.threshold.upper ?? "—"}`], ["Bắt đầu", formatDateTime(alert.started_at)], ["Đã xem", formatDateTime(alert.acknowledged_at)], ["Trở về bình thường", formatDateTime(alert.normalized_at)]].map(([label, value]) => <div key={label as string}><dt className="text-sm text-muted-foreground">{label}</dt><dd className="mt-1 font-medium">{value}</dd></div>)}
          </dl>
          <div><h3 className="mb-3 font-semibold">Telemetry trước và sau cảnh báo</h3>{alert.telemetry_context?.length ? <div className="flex flex-col gap-2">{alert.telemetry_context.map((point) => <div key={point.recorded_at} className="flex justify-between rounded-lg border p-3 text-sm"><span>{formatDateTime(point.recorded_at)}</span><strong>{point.value} {alert.sensor.unit}</strong></div>)}</div> : <p className="text-sm text-muted-foreground">Không có telemetry lân cận.</p>}</div>
          <DialogFooter className="flex-wrap">
            <Button variant="outline" onClick={() => navigate(`/admin/users/${alert.customer.id}`)}><ExternalLink data-icon="inline-start" />Mở khách hàng</Button>
            <Button variant="outline" onClick={() => navigate(`/admin/projects/${alert.project.id}/overview`)}><ExternalLink data-icon="inline-start" />Mở Project</Button>
            {alert.status !== "RESOLVED" ? <>
              {alert.status !== "ACKNOWLEDGED" ? <Button variant="outline" disabled={acknowledge.isPending} onClick={() => acknowledge.mutate()}><CheckCheck data-icon="inline-start" />Xác nhận đã xem</Button> : null}
              <Button disabled={resolve.isPending} onClick={() => setResolutionOpen(true)}><CircleCheckBig data-icon="inline-start" />Xác nhận đã khắc phục</Button>
            </> : null}
          </DialogFooter>
        </div> : <p className="text-destructive">Không thể tải chi tiết cảnh báo.</p>}
      </DialogContent>
    </Dialog>
    {alert ? <ResolveAlertDialog
      open={resolutionOpen}
      onOpenChange={setResolutionOpen}
      conditionActive={alert.condition_active}
      currentValue={alert.current_value ?? alert.trigger_value}
      lowerThreshold={alert.threshold.lower}
      upperThreshold={alert.threshold.upper}
      actorName={actorName}
      pending={resolve.isPending}
      onConfirm={(note) => resolve.mutate(note)}
    /> : null}
  </>
}
