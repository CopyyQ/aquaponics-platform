import { useQuery } from "@tanstack/react-query"
import { telemetryApi } from "@/entities/telemetry/api/telemetry-api"
import { useProtectedQueryScope } from "@/features/auth/model/use-protected-query-scope"
import { queryKeys } from "@/shared/api/query-keys"

export function useProjectMonitoringPage(projectId: number) {
  const { active, queryScope } = useProtectedQueryScope()
  const validProjectId = Number.isInteger(projectId) && projectId > 0
  const inventoryQuery = useQuery({
    queryKey: queryKeys.projects.monitoringLatest(queryScope, projectId),
    queryFn: () => telemetryApi.projectMonitoringLatest(projectId),
    enabled: active && validProjectId,
    refetchInterval: 60_000,
    staleTime: 30_000,
  })
  const summaryQuery = useQuery({
    queryKey: queryKeys.projects.summary(queryScope, projectId),
    queryFn: () => telemetryApi.projectMonitoringSummary(projectId),
    enabled: active && validProjectId,
    staleTime: 30_000,
  })

  return {
    active,
    validProjectId,
    devices: inventoryQuery.data?.devices ?? [],
    summary: summaryQuery.data,
    error: inventoryQuery.error ?? summaryQuery.error,
    isInitialLoading: inventoryQuery.isPending || summaryQuery.isPending,
    isRefetching: inventoryQuery.isFetching || summaryQuery.isFetching,
    refetch: async () => { await Promise.all([inventoryQuery.refetch(), summaryQuery.refetch()]) },
  }
}
