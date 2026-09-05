import { useMutation, useQuery } from "@tanstack/react-query"
import { Boxes, Download } from "lucide-react"
import { Link, useParams } from "react-router-dom"
import { useState } from "react"
import { toast } from "sonner"

import { useProjectContext } from "@/entities/project/model/project-context"
import { projectApi } from "@/entities/project/api/project-api"
import { useAuthStore } from "@/features/auth/model/auth-store"
import { useProtectedQueryScope } from "@/features/auth/model/use-protected-query-scope"
import { DeviceFormDialog } from "@/features/create-device/components/DeviceFormDialog"
import { queryKeys } from "@/shared/api/query-keys"
import { formatBackendError } from "@/shared/api/backend-error"
import { downloadBlob } from "@/shared/lib/download"
import { formatDateTime } from "@/shared/lib/date"
import { Badge } from "@/shared/ui/badge"
import { Button } from "@/shared/ui/button"
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/shared/ui/card"
import { EmptyState } from "@/shared/ui/empty-state"
import { PageHeader } from "@/shared/ui/page-header"
import { Skeleton } from "@/shared/ui/skeleton"
import { StatusBadge } from "@/shared/ui/status-badge"
import { Select, SelectContent, SelectGroup, SelectItem, SelectTrigger, SelectValue } from "@/shared/ui/select"

export function ProjectDevicesPage() {
  const [kindFilter, setKindFilter] = useState<"ALL" | "GENERIC" | "ENERGY_MONITOR">("ALL")
  const projectId = Number(useParams().projectId)
  const projectOverview = useProjectContext()
  const user = useAuthStore((state) => state.user)
  const { active, queryScope } = useProtectedQueryScope()
  const isAdminActive =
    user?.system_role === "ADMIN" &&
    user.status === "ACTIVE" &&
    !user.is_deleted
  const enabled = active && Number.isFinite(projectId)

  const devices = useQuery({
    queryKey: [
      ...queryKeys.projects.devices(queryScope, projectId),
      { includeDisabled: isAdminActive },
    ],
    queryFn: () => projectApi.devices(projectId, isAdminActive),
    enabled,
  })
  const sensorCount =
    devices.data?.items.reduce(
      (total, device) => total + (device.sensor_count ?? 0),
      0,
    ) ?? 0
  const visibleDevices = devices.data?.items.filter((device) => kindFilter === "ALL" || device.device_kind === kindFilter) ?? []

  const exportMutation = useMutation({
    mutationFn: () => projectApi.exportDeviceConfig(projectId),
    onSuccess: (config) => {
      const blob = new Blob([JSON.stringify(config, null, 2)], {
        type: "application/json;charset=utf-8",
      })
      downloadBlob(
        blob,
        `${projectOverview.project.code}-device-config.json`,
      )
      toast.success("Đã xuất cấu hình JSON")
    },
    onError: (error) => {
      toast.error("Không thể xuất cấu hình JSON", {
        description: formatBackendError(
          error,
          "Không thể lấy cấu hình mới nhất từ Backend.",
        ),
      })
    },
  })

  if (devices.isLoading) {
    return (
      <div className="flex flex-col gap-4">
        <Skeleton className="h-20" />
        <div className="grid gap-4 lg:grid-cols-2">
          <Skeleton className="h-72" />
          <Skeleton className="h-72" />
        </div>
      </div>
    )
  }

  if (!enabled || devices.isError || !devices.data) {
    return (
      <EmptyState
        icon={Boxes}
        title="Không thể tải thiết bị"
        description="Kiểm tra quyền truy cập hoặc thử tải lại trang."
        action={
          <Button variant="outline" onClick={() => devices.refetch()}>
            Thử lại
          </Button>
        }
      />
    )
  }

  return (
    <div className="flex flex-col gap-5">
      <PageHeader
        title="Thiết bị và cảm biến"
        description={`${devices.data.total} thiết bị · ${
          `${sensorCount} cảm biến`
        }`}
        actions={
          <>
            {isAdminActive ? (
              <Button
                type="button"
                variant="outline"
                disabled={exportMutation.isPending}
                onClick={() => exportMutation.mutate()}
              >
                <Download data-icon="inline-start" />
                {exportMutation.isPending
                  ? "Đang xuất…"
                  : "Xuất cấu hình JSON"}
              </Button>
            ) : null}
            {isAdminActive ? (
              <DeviceFormDialog
                projectId={projectId}
                projectName={projectOverview.project.name}
              />
            ) : null}
          </>
        }
      />

      <div className="flex justify-end"><Select value={kindFilter} onValueChange={(value) => setKindFilter(value as typeof kindFilter)}><SelectTrigger className="w-full sm:w-64" aria-label="Lọc loại thiết bị"><SelectValue /></SelectTrigger><SelectContent><SelectGroup><SelectItem value="ALL">Tất cả loại thiết bị</SelectItem><SelectItem value="ENERGY_MONITOR">Thiết bị năng lượng</SelectItem><SelectItem value="GENERIC">Thiết bị thông thường</SelectItem></SelectGroup></SelectContent></Select></div>

      {!visibleDevices.length ? (
        <EmptyState
          icon={Boxes}
          title="Dự án chưa có thiết bị"
          description="Thêm thiết bị từ catalog để bắt đầu cấu hình cảm biến và nhận dữ liệu MQTT."
          action={
            isAdminActive ? (
              <DeviceFormDialog
                projectId={projectId}
                projectName={projectOverview.project.name}
              />
            ) : undefined
          }
        />
      ) : (
        <div className="grid gap-4 lg:grid-cols-2">
          {visibleDevices.map((device) => {
            const detailPath = isAdminActive
              ? `/admin/projects/${projectId}/devices/${device.id}`
              : `/projects/${projectId}/devices/${device.id}`
            return (
              <Card key={device.id} className="flex min-h-64 flex-col">
                <CardHeader className="flex-row items-start justify-between gap-4 pb-3">
                  <div className="min-w-0">
                    <CardTitle className="truncate">{device.name}</CardTitle>
                    <CardDescription className="mt-1 font-mono">
                      {device.code}
                    </CardDescription>
                  </div>
                  <div className="flex flex-wrap justify-end gap-2">
                    {device.device_kind === "ENERGY_MONITOR" ? <Badge variant="success">Thiết bị năng lượng</Badge> : null}
                    {!device.is_enabled ? <Badge variant="secondary">Đã tắt</Badge> : <StatusBadge value={device.status} />}
                  </div>
                </CardHeader>
                <CardContent className="flex flex-1 flex-col gap-3">
                  {device.location ? <p className="text-sm text-muted-foreground">{device.location}</p> : null}
                  <p className="text-sm text-muted-foreground">Mẫu: <span className="font-medium text-foreground">{device.template_name ?? "Không dùng mẫu"}</span>{device.nominal_output_voltage_v ? ` · ${device.nominal_output_voltage_v} V danh định` : ""}</p>
                  <p className="text-sm"><span className="font-medium">{device.sensor_count ?? 0} cảm biến</span><span className="text-muted-foreground"> · </span><span className="font-medium">{device.actuator_count ?? 0} cơ cấu chấp hành</span></p>
                  <p className="text-sm text-muted-foreground">Dữ liệu cuối: {formatDateTime(device.last_seen_at)}</p>
                  <Button asChild variant="outline" className="mt-auto self-start">
                    <Link to={detailPath}>Xem chi tiết</Link>
                  </Button>
                </CardContent>
              </Card>
            )
          })}
        </div>
      )}
    </div>
  )
}
