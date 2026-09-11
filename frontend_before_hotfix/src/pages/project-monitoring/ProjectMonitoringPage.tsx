import { Activity } from "lucide-react"
import { useEffect, useMemo } from "react"
import { useParams, useSearchParams } from "react-router-dom"
import { useProjectContext } from "@/entities/project/model/project-context"
import type { CoreId, MonitoringRange } from "@/entities/telemetry/model/project-monitoring"
import type { MonitoringDialogTab } from "@/features/view-device-monitoring-history/model/monitoring-dialog.types"
import { DeviceMonitoringDialog } from "@/features/view-device-monitoring-history/ui/DeviceMonitoringDialog"
import { normalizeMonitoringSearchParams } from "@/pages/project-monitoring/project-monitoring.types"
import { useProjectMonitoringPage } from "@/pages/project-monitoring/useProjectMonitoringPage"
import { Button } from "@/shared/ui/button"
import { EmptyState } from "@/shared/ui/empty-state"
import { Skeleton } from "@/shared/ui/skeleton"
import { ProjectMonitoringView } from "@/widgets/project-monitoring/ProjectMonitoringView"

const parseId = (value: string | null) => { const id = Number(value); return Number.isInteger(id) && id > 0 ? id : null }

export function ProjectMonitoringPage() {
  const project = useProjectContext()
  const projectId = Number(useParams().projectId)
  const [params, setParams] = useSearchParams()
  const monitoring = useProjectMonitoringPage(projectId)
  const dialogDeviceId = parseId(params.get("monitoringDevice"))
  const device = useMemo(() => monitoring.devices.find((item) => item.id === dialogDeviceId) ?? null, [monitoring.devices, dialogDeviceId])
  const dialogTab: MonitoringDialogTab = params.get("monitoringTab") === "actuators" ? "actuators" : "sensors"
  const resourceId = parseId(params.get("resource"))

  useEffect(() => {
    const next = normalizeMonitoringSearchParams(params)
    if (next.toString() !== params.toString()) setParams(next, { replace: true })
  }, [params, setParams])

  const updateDialog = (changes: Record<string, string | null>) => setParams((current) => { const next = new URLSearchParams(current); Object.entries(changes).forEach(([key, value]) => value === null ? next.delete(key) : next.set(key, value)); return next })
  const openDialog = (deviceId: CoreId, tab: MonitoringDialogTab, resource?: CoreId) => updateDialog({ monitoringDevice: String(deviceId), monitoringTab: tab, resource: resource ? String(resource) : null })

  if (monitoring.isInitialLoading) return <div className="flex flex-col gap-4" aria-busy="true"><Skeleton className="h-32" /><Skeleton className="h-56" /><Skeleton className="h-96" /><span className="sr-only">Đang tải dữ liệu giám sát</span></div>
  if (monitoring.error) return <EmptyState icon={Activity} title="Không thể tải dữ liệu giám sát" description="Kiểm tra quyền truy cập hoặc thử lại." action={<Button variant="outline" onClick={() => { void monitoring.refetch() }}>Thử lại</Button>} />
  if (!monitoring.summary) return <EmptyState icon={Activity} title="Chưa có dữ liệu giám sát" description="Dự án chưa có dữ liệu vận hành." />

  return <>
    <ProjectMonitoringView project={project.project} summary={monitoring.summary} devices={monitoring.devices} mode="admin" isRefetching={monitoring.isRefetching} onRefresh={() => { void monitoring.refetch() }} onOpenMonitoring={openDialog} />
    <DeviceMonitoringDialog open={device !== null} projectId={projectId} device={device} tab={dialogTab} resourceId={resourceId} range={(params.get("range") as MonitoringRange | null) ?? "24h"} onOpenChange={(open) => { if (!open) updateDialog({ monitoringDevice: null, monitoringTab: null, resource: null, range: null }) }} onTabChange={(tab) => updateDialog({ monitoringTab: tab })} onResourceChange={(id) => updateDialog({ resource: String(id) })} onRangeChange={(range) => updateDialog({ range })} />
  </>
}
