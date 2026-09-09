import { useQuery } from "@tanstack/react-query"
import { useOutletContext, useParams } from "react-router-dom"
import { AlertTriangle } from "lucide-react"
import { getMonitoringLatest, listAlerts, listDevices, queryKeys } from "@/api/resources"
import type { AquaponicsSystem } from "@/api/contracts"
import { OverviewDashboard, createOverviewViewModel } from "@/widgets/canonical-overview/OverviewDashboard"
import { EmptyState } from "@/shared/ui/empty-state"
import { Skeleton } from "@/shared/ui/skeleton"
import { errorMessage } from "@/api/client"

export function OverviewPage() {
  const systemId = Number(useParams().systemId)
  const { system } = useOutletContext<{ system: AquaponicsSystem }>()
  const devices = useQuery({ queryKey: queryKeys.devices(systemId), queryFn: () => listDevices(systemId) })
  const latest = useQuery({ queryKey: queryKeys.monitoringLatest(systemId), queryFn: () => getMonitoringLatest(systemId) })
  const alerts = useQuery({ queryKey: queryKeys.alerts(systemId), queryFn: () => listAlerts(systemId) })
  if (devices.isLoading || latest.isLoading || alerts.isLoading) return <div className="space-y-4"><Skeleton className="h-28" /><Skeleton className="h-72" /></div>
  if (devices.isError || latest.isError || alerts.isError) return <EmptyState icon={AlertTriangle} title="Không thể tải tổng quan" description={errorMessage(devices.error ?? latest.error ?? alerts.error)} />
  return <OverviewDashboard model={createOverviewViewModel(system, devices.data ?? [], latest.data, alerts.data ?? [])} />
}
