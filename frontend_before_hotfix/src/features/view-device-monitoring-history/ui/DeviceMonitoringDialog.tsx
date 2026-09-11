import { Activity, AlertTriangle, RadioTower, RotateCcw } from "lucide-react"
import { getReportedStateLabel } from "@/entities/actuator/lib/actuator-monitoring"
import { getSensorConnectionStatus } from "@/entities/sensor/lib/get-sensor-connection-status"
import { formatSensorValue } from "@/entities/sensor/lib/format-sensor-value"
import { getSensorValueStatus } from "@/entities/sensor/lib/get-sensor-value-status"
import { monitoringExpectedInterval, monitoringRangeLabel } from "@/entities/telemetry/lib/monitoring-range"
import type {
  CoreId,
  MonitoringActuator,
  MonitoringDevice,
  MonitoringRange,
  MonitoringSensor,
} from "@/entities/telemetry/model/project-monitoring"
import { useDeviceMonitoringHistory } from "@/features/view-device-monitoring-history/model/useDeviceMonitoringHistory"
import type { MonitoringDialogTab } from "@/features/view-device-monitoring-history/model/monitoring-dialog.types"
import { ActuatorHistoryStatistics } from "@/features/view-device-monitoring-history/ui/ActuatorHistoryStatistics"
import { ActuatorStateHistoryChart } from "@/features/view-device-monitoring-history/ui/ActuatorStateHistoryChart"
import { MonitoringRangeSelector } from "@/features/view-device-monitoring-history/ui/MonitoringRangeSelector"
import { TimeSeriesChart } from "@/shared/charts/time-series"
import { formatDateTime } from "@/shared/lib/date"
import { Badge } from "@/shared/ui/badge"
import { Button } from "@/shared/ui/button"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/shared/ui/dialog"
import {
  Select,
  SelectContent,
  SelectGroup,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/shared/ui/select"
import { Skeleton } from "@/shared/ui/skeleton"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/shared/ui/tabs"

function ConnectionBadge({ status }: { status: MonitoringDevice["connection_status"] }) {
  const display = getSensorConnectionStatus(status)
  const variant = display.tone === "success"
    ? "success"
    : display.tone === "offline"
      ? "destructive"
      : display.tone === "warning"
        ? "warning"
        : "secondary"
  return <Badge variant={variant}>{display.label}</Badge>
}

function SensorResourceButton({
  sensor,
  selected,
  onSelect,
}: {
  sensor: MonitoringSensor
  selected: boolean
  onSelect: () => void
}) {
  const valueStatus = getSensorValueStatus(
    sensor.latest?.value ?? null,
    sensor.lower_threshold,
    sensor.upper_threshold,
  )
  return <button
    type="button"
    aria-pressed={selected}
    className="flex w-full flex-col gap-1 rounded-lg border p-3 text-left hover:bg-accent focus-visible:ring-2 focus-visible:ring-ring data-[selected=true]:border-primary data-[selected=true]:bg-accent"
    data-selected={selected}
    onClick={onSelect}
  >
    <span className="line-clamp-2 text-sm font-medium">{sensor.name}</span>
    <span className="text-sm font-semibold tabular-nums">{formatSensorValue(sensor.latest?.value ?? null, sensor.unit)}</span>
    <span className="text-xs text-muted-foreground">{valueStatus.label} · {sensor.latest ? formatDateTime(sensor.latest.recorded_at) : "Chưa có dữ liệu"}</span>
  </button>
}

function ActuatorResourceButton({
  actuator,
  selected,
  onSelect,
}: {
  actuator: MonitoringActuator
  selected: boolean
  onSelect: () => void
}) {
  return <button
    type="button"
    aria-pressed={selected}
    className="flex w-full flex-col gap-1 rounded-lg border p-3 text-left hover:bg-accent focus-visible:ring-2 focus-visible:ring-ring data-[selected=true]:border-primary data-[selected=true]:bg-accent"
    data-selected={selected}
    onClick={onSelect}
  >
    <span className="line-clamp-2 text-sm font-medium">{actuator.name}</span>
    <span className="text-sm font-semibold">{getReportedStateLabel(actuator.reported_state)}</span>
    <span className="text-xs text-muted-foreground">{actuator.last_reported_at ? formatDateTime(actuator.last_reported_at) : "Chưa có dữ liệu"}</span>
  </button>
}

function ResourceSelect({
  resources,
  value,
  onValueChange,
}: {
  resources: Array<{ id: CoreId; name: string }>
  value: CoreId | null
  onValueChange: (id: CoreId) => void
}) {
  if (!resources.length) return null
  return <div className="lg:hidden">
    <Select value={value === null ? undefined : String(value)} onValueChange={(next) => { const resource = resources.find((item) => String(item.id) === next); if (resource) onValueChange(resource.id) }}>
      <SelectTrigger aria-label="Chọn tài nguyên để xem biểu đồ">
        <SelectValue placeholder="Chọn tài nguyên" />
      </SelectTrigger>
      <SelectContent>
        <SelectGroup>
          {resources.map((resource) => <SelectItem key={resource.id} value={String(resource.id)}>{resource.name}</SelectItem>)}
        </SelectGroup>
      </SelectContent>
    </Select>
  </div>
}

function ActuatorStatusStrip({ actuator }: { actuator: MonitoringActuator }) {
  const sync = actuator.synchronization_status === "IN_SYNC" ? "Đã đồng bộ" : actuator.synchronization_status === "OUT_OF_SYNC" ? "Chưa đồng bộ" : "Chưa xác định"
  const command = actuator.latest_command
  const commandLabel = command?.status === "TIMEOUT" ? "Hết thời gian chờ" : command?.status === "FAILED" ? "Thất bại" : command?.status === "ACKNOWLEDGED" ? "Đã xác nhận" : command?.status === "PUBLISHED" ? "Đã gửi" : command ? "Đang chờ" : "Chưa có lệnh"
  return <div className="rounded-lg border bg-muted/20 p-3 text-sm"><div className="flex flex-wrap items-center gap-x-4 gap-y-2"><span className="font-medium">{actuator.name}</span><span className="font-mono text-xs text-muted-foreground">{actuator.code}</span><ConnectionBadge status={actuator.connection_status} /><span>{getReportedStateLabel(actuator.reported_state)}</span><span className="text-muted-foreground">Yêu cầu: {getReportedStateLabel(actuator.desired_state)}</span><span className="text-muted-foreground">{sync}</span></div><p className="mt-2 text-xs text-muted-foreground">Lệnh gần nhất: {commandLabel}{command ? ` · ${formatDateTime(command.requested_at)}` : ""}</p>{actuator.active_incident ? <p className="mt-2 text-xs text-destructive">Sự cố mở: {actuator.active_incident.rule_name}</p> : <p className="mt-2 text-xs text-muted-foreground">Không có sự cố đang mở</p>}</div>
}

export function DeviceMonitoringDialog({
  open,
  projectId,
  device,
  tab,
  resourceId,
  range,
  onOpenChange,
  onTabChange,
  onResourceChange,
  onRangeChange,
}: {
  open: boolean
  projectId: number
  device: MonitoringDevice | null
  tab: MonitoringDialogTab
  resourceId: CoreId | null
  range: MonitoringRange
  onOpenChange: (open: boolean) => void
  onTabChange: (tab: MonitoringDialogTab) => void
  onResourceChange: (resourceId: CoreId) => void
  onRangeChange: (range: MonitoringRange) => void
}) {
  const history = useDeviceMonitoringHistory({
    projectId,
    deviceId: Number(device?.id ?? 0),
    range,
    tab,
    open: open && device !== null,
  })
  const resources = tab === "sensors" ? device?.sensors ?? [] : device?.actuators ?? []
  const selectedResourceId = resources.some((resource) => resource.id === resourceId)
    ? resourceId
    : resources[0]?.id ?? null
  const selectedSensor = tab === "sensors"
    ? device?.sensors.find((sensor) => sensor.id === selectedResourceId) ?? null
    : null
  const selectedActuator = tab === "actuators"
    ? device?.actuators.find((actuator) => actuator.id === selectedResourceId) ?? null
    : null
  const sensorSeries = history.sensorSeries.data?.series.find(
    (series) => series.sensor_id === selectedSensor?.id,
  )
  const actuatorHistory = history.actuatorHistory.data?.items.find(
    (item) => item.actuator_id === selectedActuator?.id,
  )

  return <Dialog open={open} onOpenChange={onOpenChange}>
    <DialogContent className="flex max-h-[calc(100dvh-1rem)] max-w-[min(1380px,calc(100vw-1rem))] flex-col gap-4 overflow-hidden p-4 sm:max-h-[calc(100dvh-2rem)] sm:p-6">
      <DialogHeader className="pr-8">
        <div className="flex flex-wrap items-center gap-2">
          <DialogTitle>Theo dõi: {device?.name ?? "Thiết bị"}</DialogTitle>
          {device ? <ConnectionBadge status={device.connection_status} /> : null}
        </div>
        <DialogDescription>
          {device?.location ?? "Chưa cập nhật vị trí"} · Cập nhật cuối: {device?.last_seen_at ? formatDateTime(device.last_seen_at) : "Chưa có dữ liệu"}
        </DialogDescription>
      </DialogHeader>
      <MonitoringRangeSelector range={range} onRangeChange={onRangeChange} />
      <Tabs value={tab} onValueChange={(value) => onTabChange(value as MonitoringDialogTab)} className="flex min-h-0 flex-1 flex-col">
        <TabsList className="w-full sm:w-fit">
          <TabsTrigger value="sensors" className="flex-1 sm:flex-none">Cảm biến ({device?.sensors.length ?? 0})</TabsTrigger>
          <TabsTrigger value="actuators" className="flex-1 sm:flex-none">Cơ cấu chấp hành ({device?.actuators.length ?? 0})</TabsTrigger>
        </TabsList>
        <div className="mt-3 min-h-0 flex-1 overflow-y-auto">
          <TabsContent value="sensors" className="mt-0">
            {!device?.sensors.length ? <div className="flex min-h-64 items-center justify-center rounded-lg border border-dashed text-sm text-muted-foreground">Thiết bị chưa có cảm biến.</div> : <div className="grid gap-4 lg:grid-cols-[280px_minmax(0,1fr)]">
              <ResourceSelect resources={device.sensors} value={selectedResourceId} onValueChange={onResourceChange} />
              <div className="hidden max-h-[min(62dvh,640px)] flex-col gap-2 overflow-y-auto lg:flex">
                {device.sensors.map((sensor) => <SensorResourceButton key={sensor.id} sensor={sensor} selected={sensor.id === selectedResourceId} onSelect={() => onResourceChange(sensor.id)} />)}
              </div>
              <div className="min-w-0">
                {history.sensorSeries.isPending ? <Skeleton className="h-80" /> : history.sensorSeries.isError ? <div className="flex min-h-64 flex-col items-center justify-center gap-3 rounded-lg border border-dashed p-6 text-center"><AlertTriangle aria-hidden="true" /><p className="text-sm">Không thể tải dữ liệu cảm biến.</p><Button variant="outline" size="sm" onClick={() => { void history.sensorSeries.refetch() }}><RotateCcw data-icon="inline-start" />Thử lại</Button></div> : selectedSensor && sensorSeries?.points.length ? <TimeSeriesChart
                  data={sensorSeries.points.map((point) => ({ timestamp: point.recorded_at, value: point.value }))}
                  unit={selectedSensor.unit}
                  title={selectedSensor.name}
                  currentValue={selectedSensor.latest?.value ?? null}
                  safeMin={selectedSensor.lower_threshold}
                  safeMax={selectedSensor.upper_threshold}
                  status={selectedSensor.connection_status === "OFFLINE" ? "offline" : "normal"}
                  rangeLabel={monitoringRangeLabel(range)}
                  lastUpdatedAt={selectedSensor.latest?.recorded_at}
                  expectedIntervalMs={monitoringExpectedInterval(range)}
                /> : <div className="flex min-h-64 flex-col items-center justify-center gap-2 rounded-lg border border-dashed p-6 text-center text-sm text-muted-foreground"><RadioTower aria-hidden="true" /><p>Chưa có dữ liệu đo trong khoảng đã chọn.</p></div>}
              </div>
            </div>}
          </TabsContent>
          <TabsContent value="actuators" className="mt-0">
            {!device?.actuators.length ? <div className="flex min-h-64 items-center justify-center rounded-lg border border-dashed text-sm text-muted-foreground">Thiết bị chưa có cơ cấu chấp hành.</div> : <div className="grid gap-4 lg:grid-cols-[280px_minmax(0,1fr)]">
              <ResourceSelect resources={device.actuators} value={selectedResourceId} onValueChange={onResourceChange} />
              <div className="hidden max-h-[min(62dvh,640px)] flex-col gap-2 overflow-y-auto lg:flex">
                {device.actuators.map((actuator) => <ActuatorResourceButton key={actuator.id} actuator={actuator} selected={actuator.id === selectedResourceId} onSelect={() => onResourceChange(actuator.id)} />)}
              </div>
              <div className="flex min-w-0 flex-col gap-4">
                {selectedActuator ? <ActuatorStatusStrip actuator={selectedActuator} /> : null}
                {history.actuatorHistory.isPending ? <><Skeleton className="h-64" /><Skeleton className="h-24" /></> : history.actuatorHistory.isError ? <div className="flex min-h-64 flex-col items-center justify-center gap-3 rounded-lg border border-dashed p-6 text-center"><AlertTriangle aria-hidden="true" /><p className="text-sm">Không thể tải lịch sử cơ cấu chấp hành.</p><Button variant="outline" size="sm" onClick={() => { void history.actuatorHistory.refetch() }}><RotateCcw data-icon="inline-start" />Thử lại</Button></div> : selectedActuator && actuatorHistory ? <>
                  <ActuatorStateHistoryChart points={actuatorHistory.points} gaps={actuatorHistory.gaps} actuatorName={selectedActuator.name} />
                  <ActuatorHistoryStatistics statistics={actuatorHistory.statistics} electrical={selectedActuator.electrical} />
                </> : <div className="flex min-h-64 flex-col items-center justify-center gap-2 rounded-lg border border-dashed p-6 text-center text-sm text-muted-foreground"><Activity aria-hidden="true" /><p>Chưa có lịch sử bật/tắt.</p></div>}
              </div>
            </div>}
          </TabsContent>
        </div>
      </Tabs>
    </DialogContent>
  </Dialog>
}
