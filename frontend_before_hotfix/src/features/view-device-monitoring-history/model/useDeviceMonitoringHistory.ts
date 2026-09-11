import { keepPreviousData, useQuery } from "@tanstack/react-query"
import { telemetryApi } from "@/entities/telemetry/api/telemetry-api"
import type { MonitoringRange } from "@/entities/telemetry/model/project-monitoring"
import { useProtectedQueryScope } from "@/features/auth/model/use-protected-query-scope"
import type { MonitoringDialogTab } from "@/features/view-device-monitoring-history/model/monitoring-dialog.types"
import { queryKeys } from "@/shared/api/query-keys"

export function useDeviceMonitoringHistory({
  projectId,
  deviceId,
  range,
  tab,
  open,
}: {
  projectId: number
  deviceId: number
  range: MonitoringRange
  tab: MonitoringDialogTab
  open: boolean
}) {
  const { active, queryScope } = useProtectedQueryScope()
  const canQuery = active && open && projectId > 0 && deviceId > 0
  const sensorSeries = useQuery({
    queryKey: queryKeys.projects.deviceSensorSeries(
      queryScope,
      projectId,
      deviceId,
      range,
    ),
    queryFn: () => telemetryApi.deviceMonitoringSensorSeries(projectId, deviceId, range),
    enabled: canQuery && tab === "sensors",
    placeholderData: keepPreviousData,
    staleTime: 60_000,
    refetchInterval: open && tab === "sensors" ? 90_000 : false,
  })
  const actuatorHistory = useQuery({
    queryKey: queryKeys.projects.deviceActuatorHistory(
      queryScope,
      projectId,
      deviceId,
      range,
    ),
    queryFn: () => telemetryApi.deviceMonitoringActuatorHistory(projectId, deviceId, range),
    enabled: canQuery && tab === "actuators",
    placeholderData: keepPreviousData,
    staleTime: 60_000,
    refetchInterval: open && tab === "actuators" ? 90_000 : false,
  })
  return { sensorSeries, actuatorHistory }
}
