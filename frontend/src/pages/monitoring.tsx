import { Activity } from "lucide-react"
import { useMemo } from "react"
import { useQuery } from "@tanstack/react-query"
import { useOutletContext, useParams, useSearchParams } from "react-router-dom"
import type { AquaponicsSystem, MonitoringActuatorHistoryRead, MonitoringRange, MonitoringSeriesRead } from "@/api/contracts"
import { errorMessage } from "@/api/client"
import { getMonitoringActuatorHistory, getMonitoringLatest, getMonitoringSeries, listAlerts, queryKeys } from "@/api/resources"
import { useAuth } from "@/app/auth"
import type { MonitoringDialogTab } from "@/features/view-device-monitoring-history/model/monitoring-dialog.types"
import { CanonicalDeviceMonitoringDialog } from "@/features/view-device-monitoring-history/ui/CanonicalDeviceMonitoringDialog"
import { adaptCanonicalMonitoring } from "@/pages/monitoring-canonical-adapter"
import { Button } from "@/shared/ui/button"
import { EmptyState } from "@/shared/ui/empty-state"
import { Skeleton } from "@/shared/ui/skeleton"
import { ProjectMonitoringView } from "@/widgets/project-monitoring/ProjectMonitoringView"

const monitoringRanges: readonly MonitoringRange[] = ["1h", "6h", "12h", "24h", "30d"]

function parseId(value: string | null) {
  return value?.trim() || null
}

function parseRange(value: string | null): MonitoringRange {
  return monitoringRanges.find((range) => range === value) ?? "24h"
}

export function MonitoringPage() {
  const systemId = useParams().systemId ?? ""
  const { system } = useOutletContext<{ system: AquaponicsSystem }>()
  const { can } = useAuth()
  const [params, setParams] = useSearchParams()
  const selectedDeviceId = parseId(params.get("monitoringDevice"))
  const selectedResourceId = parseId(params.get("resource"))
  const tab: MonitoringDialogTab = params.get("monitoringTab") === "actuators" ? "actuators" : "sensors"
  const range = parseRange(params.get("range"))

  const latest = useQuery({
    queryKey: queryKeys.monitoringLatest(systemId),
    queryFn: () => getMonitoringLatest(systemId),
    enabled: Boolean(systemId),
    staleTime: 30_000,
    refetchInterval: 60_000,
  })
  const alerts = useQuery({
    queryKey: queryKeys.alerts(systemId),
    queryFn: () => listAlerts(systemId),
    enabled: Boolean(systemId) && can("incidents.read"),
    staleTime: 30_000,
    refetchInterval: 60_000,
  })
  const series = useQuery({
    queryKey: queryKeys.monitoringSeries(systemId, range),
    queryFn: () => getMonitoringSeries(systemId, range),
    enabled: selectedDeviceId !== null && tab === "sensors",
    staleTime: 30_000,
  })
  const actuatorHistory = useQuery({
    queryKey: queryKeys.monitoringActuatorHistory(systemId, selectedDeviceId ?? "", range),
    queryFn: () => getMonitoringActuatorHistory(systemId, selectedDeviceId ?? "", range),
    enabled: selectedDeviceId !== null && tab === "actuators",
    staleTime: 30_000,
  })

  const adapted = useMemo(
    () => latest.data ? adaptCanonicalMonitoring(latest.data, alerts.data ?? []) : null,
    [latest.data, alerts.data],
  )

  const updateDialog = (changes: Record<string, string | null>) => {
    setParams((current) => {
      const next = new URLSearchParams(current)
      for (const [key, value] of Object.entries(changes)) {
        if (value === null) next.delete(key)
        else next.set(key, value)
      }
      return next
    }, { replace: true })
  }

  const openDialog = (deviceId: string | number, nextTab: MonitoringDialogTab, resourceId?: string | number) => {
    updateDialog({
      monitoringDevice: String(deviceId),
      monitoringTab: nextTab,
      resource: resourceId ? String(resourceId) : null,
    })
  }

  if (latest.isLoading || (can("incidents.read") && alerts.isLoading)) {
    return <div className="flex flex-col gap-4" aria-busy="true"><Skeleton className="h-32" /><Skeleton className="h-56" /><Skeleton className="h-96" /><span className="sr-only">Đang tải dữ liệu giám sát</span></div>
  }

  if (latest.isError || !latest.data || (can("incidents.read") && alerts.isError)) {
    return <EmptyState
      icon={Activity}
      title="Không thể tải dữ liệu giám sát"
      description={errorMessage(latest.error ?? alerts.error)}
      action={<Button variant="outline" onClick={() => { void Promise.all([latest.refetch(), alerts.refetch()]) }}>Thử lại</Button>}
    />
  }

  if (!adapted) {
    return <EmptyState icon={Activity} title="Chưa có dữ liệu giám sát" description="Hệ thống chưa có dữ liệu vận hành." />
  }

  const selectedCanonicalDevice = latest.data.devices.find((item) => item.id === selectedDeviceId) ?? null
  const emptySeries: MonitoringSeriesRead = {
    aquaponics_system_id: systemId,
    range,
    resolution: "raw",
    series: [],
  }
  const emptyActuatorHistory: MonitoringActuatorHistoryRead = {
    aquaponics_system_id: systemId,
    device_id: selectedDeviceId ?? "",
    range,
    items: [],
  }

  return <>
    <ProjectMonitoringView
      project={{ code: system.code, name: system.name, location: system.location }}
      summary={adapted.summary}
      devices={adapted.devices}
      mode="admin"
      isRefetching={latest.isFetching || alerts.isFetching}
      onRefresh={() => { void Promise.all([latest.refetch(), alerts.refetch()]) }}
      onOpenMonitoring={openDialog}
    />
    <CanonicalDeviceMonitoringDialog
      device={selectedCanonicalDevice}
      series={series.data ?? emptySeries}
      actuatorHistory={actuatorHistory.data ?? emptyActuatorHistory}
      range={range}
      tab={tab}
      resourceId={selectedResourceId}
      loading={tab === "sensors" ? (series.isLoading || series.isFetching) : (actuatorHistory.isLoading || actuatorHistory.isFetching)}
      error={tab === "sensors" ? series.error : actuatorHistory.error}
      open={selectedCanonicalDevice !== null}
      onOpenChange={(open) => {
        if (!open) updateDialog({ monitoringDevice: null, monitoringTab: null, resource: null, range: null })
      }}
      onTabChange={(nextTab) => updateDialog({ monitoringTab: nextTab, resource: null })}
      onResourceChange={(id) => updateDialog({ resource: String(id) })}
      onRangeChange={(nextRange) => updateDialog({ range: nextRange })}
    />
  </>
}
