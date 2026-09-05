import { useMemo, useState } from "react"
import { useQuery } from "@tanstack/react-query"
import { Activity, AlertTriangle, Database, RadioTower, Router } from "lucide-react"
import { alertApi } from "@/entities/alert/api/alert-api"
import { deviceApi } from "@/entities/device/api/device-api"
import { sensorApi } from "@/entities/sensor/api/sensor-api"
import { sensorModelApi } from "@/entities/sensor-model/api/sensor-model-api"
import { telemetryApi } from "@/entities/telemetry/api/telemetry-api"
import { buildTelemetryWindow, telemetryRangeLabels, type TelemetryRange } from "@/entities/telemetry/lib/telemetry-display"
import { httpClient } from "@/shared/api/http-client"
import { downloadBlob } from "@/shared/lib/download"
import { Card, CardContent } from "@/shared/ui/card"
import { EmptyState } from "@/shared/ui/empty-state"
import { Skeleton } from "@/shared/ui/skeleton"
import { ActiveAlertsPanel } from "@/widgets/monitoring/active-alerts-panel"
import { LatestTelemetryGrid } from "@/widgets/monitoring/latest-telemetry-grid"
import { MonitoringChartPanel } from "@/widgets/monitoring/monitoring-chart-panel"
import { MonitoringHealthSummary } from "@/widgets/monitoring/monitoring-health-summary"
import { MonitoringMetricCard } from "@/widgets/monitoring/monitoring-metric-card"
import { useProtectedQueryScope } from "@/features/auth/model/use-protected-query-scope"
import { queryKeys } from "@/shared/api/query-keys"

export function MonitoringDashboard() {
  const { active, queryScope } = useProtectedQueryScope()
  const [sensorId, setSensorId] = useState<number | null>(null)
  const [range, setRange] = useState<TelemetryRange>("24h")
  const latest = useQuery({ queryKey: queryKeys.telemetry.latest(queryScope), queryFn: telemetryApi.latest, enabled: active, refetchInterval: 30_000 })
  const devices = useQuery({ queryKey: queryKeys.devices.list(queryScope), queryFn: deviceApi.list, enabled: active, refetchInterval: 30_000 })
  const sensors = useQuery({ queryKey: queryKeys.sensors.list(queryScope), queryFn: () => sensorApi.list(), enabled: active, refetchInterval: 30_000 })
  const alerts = useQuery({ queryKey: queryKeys.alerts.list(queryScope, "monitoring-active"), queryFn: () => alertApi.list(), enabled: active, refetchInterval: 30_000 })
  const models = useQuery({ queryKey: queryKeys.sensorModels.list(queryScope), queryFn: sensorModelApi.list, enabled: active })
  const selected = latest.data?.find((item) => item.sensor_id === sensorId) ?? latest.data?.[0]
  const selectedSensor = sensors.data?.find((sensor) => sensor.id === selected?.sensor_id)
  const telemetryWindow = useMemo(() => buildTelemetryWindow(range), [range])
  const history = useQuery({
    queryKey: queryKeys.telemetry.history(queryScope, selected?.sensor_id, range),
    queryFn: () => telemetryApi.history(selected!.sensor_id, telemetryWindow.start.toISOString(), telemetryWindow.end.toISOString()),
    enabled: active && Boolean(selected),
  })

  const latestReceivedAt = latest.data?.map((item) => item.recorded_at).filter((value): value is string => Boolean(value)).sort().at(-1) ?? null
  const activeAlerts = alerts.data?.filter((alert) => alert.status !== "RESOLVED") ?? []

  const exportCsv = async () => {
    if (!selected) return
    const { data } = await httpClient.get(telemetryApi.exportUrl(selected.sensor_id, telemetryWindow.start.toISOString(), telemetryWindow.end.toISOString()), { responseType: "blob" })
    downloadBlob(data, `${selected.sensor_code}-telemetry-${range}.csv`)
  }

  if (latest.isLoading || devices.isLoading || sensors.isLoading) {
    return <div className="flex flex-col gap-5">
      <Skeleton className="h-44" />
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">{Array.from({ length: 4 }).map((_, index) => <Skeleton key={index} className="h-32" />)}</div>
      <Skeleton className="h-96" />
    </div>
  }

  if (latest.isError || devices.isError || sensors.isError) {
    return <Card className="border-destructive/30 shadow-none">
      <CardContent className="p-8">
        <EmptyState icon={AlertTriangle} title="Không thể tải dữ liệu quan trắc" description="Vui lòng kiểm tra kết nối API hoặc thử làm mới trang." />
      </CardContent>
    </Card>
  }

  const latestItems = latest.data ?? []
  const deviceItems = devices.data ?? []
  const sensorItems = sensors.data ?? []
  const alertItems = alerts.data ?? []

  if (!latestItems.length) {
    return <div className="flex flex-col gap-5">
      <MonitoringHealthSummary devices={deviceItems} sensors={sensorItems} alerts={alertItems} latestReceivedAt={latestReceivedAt} />
      <EmptyState icon={Activity} title="Chưa có dữ liệu quan trắc" description="Dữ liệu sẽ xuất hiện sau khi thiết bị gửi telemetry hợp lệ." />
    </div>
  }

  return <div className="flex flex-col gap-6">
    <MonitoringHealthSummary devices={deviceItems} sensors={sensorItems} alerts={alertItems} latestReceivedAt={latestReceivedAt} />
    <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
      <MonitoringMetricCard title="Cảm biến trực tuyến" value={`${sensorItems.filter((sensor) => sensor.status === "ONLINE").length}/${sensorItems.length}`} description={`${sensorItems.filter((sensor) => sensor.status === "OFFLINE").length} cảm biến mất kết nối`} icon={RadioTower} tone="success" />
      <MonitoringMetricCard title="Gateway trực tuyến" value={`${deviceItems.filter((device) => device.status === "ONLINE").length}/${deviceItems.length}`} description={`${deviceItems.filter((device) => device.status === "WAITING_CONNECTION").length} gateway chờ kết nối`} icon={Router} />
      <MonitoringMetricCard title="Cảnh báo chưa xử lý" value={activeAlerts.length} description={`${activeAlerts.filter((alert) => alert.severity === "CRITICAL").length} cảnh báo nghiêm trọng`} icon={AlertTriangle} tone={activeAlerts.length ? "danger" : "success"} />
      <MonitoringMetricCard title="Loại cảm biến" value={models.data?.length ?? "—"} description={`Khoảng đang xem: ${telemetryRangeLabels[range]}`} icon={Database} />
    </section>
    <LatestTelemetryGrid items={latestItems} selectedSensorId={selected?.sensor_id} onSelectSensor={setSensorId} />
    <section className="grid gap-6 xl:grid-cols-[minmax(0,1.55fr)_minmax(360px,0.75fr)]">
      <MonitoringChartPanel latestItems={latestItems} selected={selected} selectedSensor={selectedSensor} history={history.data} isLoading={history.isLoading} range={range} onRangeChange={setRange} onSensorChange={setSensorId} onExportCsv={exportCsv} />
      <ActiveAlertsPanel alerts={alertItems} sensors={sensorItems} />
    </section>
    <Card className="shadow-none">
      <CardContent className="grid gap-4 p-5 text-sm sm:grid-cols-3">
        <div><div className="text-xs text-muted-foreground">Cảm biến đang chọn</div><div className="mt-1 font-semibold">{selected?.sensor_name}</div></div>
        <div><div className="text-xs text-muted-foreground">Mã cảm biến</div><div className="mt-1 font-mono font-semibold">{selected?.sensor_code}</div></div>
        <div><div className="text-xs text-muted-foreground">Thiết bị</div><div className="mt-1 font-semibold">{selected?.device_name}</div></div>
      </CardContent>
    </Card>
  </div>
}
