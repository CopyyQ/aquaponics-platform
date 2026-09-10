import { Activity, Bolt, ChevronDown, ChevronUp, Eye, MapPin, WifiOff } from "lucide-react"
import { useState } from "react"
import {
  getCommandStatus,
  getDesiredStateLabel,
  getReportedStateLabel,
  isAwaitingActuatorConfirmation,
} from "@/entities/actuator/lib/actuator-monitoring"
import { electricalQualityLabel } from "@/entities/actuator/lib/actuator-electrical"
import { formatSensorValue } from "@/entities/sensor/lib/format-sensor-value"
import { getSensorDataStatus } from "@/entities/sensor/lib/get-sensor-data-status"
import type {
  CoreId,
  MonitoringActuator,
  MonitoringDevice,
  MonitoringSensor,
} from "@/entities/telemetry/model/project-monitoring"
import type { ElectricalFeedbackMetric } from "@/entities/project/model/types"
import { formatDateTime, formatVietnamTime } from "@/shared/lib/date"
import { Badge } from "@/shared/ui/badge"
import { Button } from "@/shared/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/shared/ui/card"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/shared/ui/table"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/shared/ui/tabs"

function ConnectionBadge({ status }: { status: MonitoringDevice["connection_status"] }) {
  const label = status === "ONLINE" ? "Kết nối" : status === "OFFLINE" ? "Mất kết nối" : "Chờ"
  const variant = status === "ONLINE" ? "success" : status === "OFFLINE" ? "destructive" : "warning"
  return <Badge variant={variant}>{label}</Badge>
}

function ValueStatusBadge({ sensor }: { sensor: MonitoringSensor }) {
  if (sensor.latest?.freshness === "STALE") return <Badge variant="warning">Dữ liệu cũ</Badge>
  if (sensor.latest?.freshness === "NO_DATA" || !sensor.latest) return <Badge variant="secondary">Không có dữ liệu</Badge>
  const status = sensor.threshold_state === "BELOW"
    ? { label: "Thấp hơn ngưỡng", tone: "danger" as const }
    : sensor.threshold_state === "ABOVE"
      ? { label: "Cao hơn ngưỡng", tone: "danger" as const }
      : sensor.threshold_state === "NORMAL"
        ? { label: "Trong ngưỡng", tone: "success" as const }
        : { label: "Chưa cấu hình ngưỡng", tone: "neutral" as const }
  return <Badge variant={status.tone === "danger" ? "destructive" : status.tone === "success" ? "success" : "secondary"}>{status.label}</Badge>
}

function DataStatusBadge({ sensor }: { sensor: MonitoringSensor }) {
  const status = sensor.latest?.freshness === "STALE"
    ? { label: "Dữ liệu cũ", tone: "warning" as const }
    : sensor.latest?.freshness === "NO_DATA" || !sensor.latest
      ? { label: "Không có dữ liệu", tone: "neutral" as const }
      : sensor.latest?.freshness === "FRESH"
        ? { label: "Đang nhận dữ liệu", tone: "success" as const }
        : getSensorDataStatus(sensor.latest.recorded_at, sensor.data_status)
  const variant = status.tone === "danger"
    ? "destructive"
    : status.tone === "success"
      ? "success"
      : status.tone === "warning"
        ? "warning"
        : "secondary"
  return <Badge variant={variant}>{status.label}</Badge>
}

function SensorRow({
  sensor,
  deviceOffline,
  onOpen,
}: {
  sensor: MonitoringSensor
  deviceOffline: boolean
  onOpen?: () => void
}) {
  return <TableRow>
    <TableCell className="font-medium"><span className="line-clamp-2">{sensor.name}</span></TableCell>
    <TableCell><DataStatusBadge sensor={sensor} /></TableCell>
    <TableCell className="tabular-nums">
      <span aria-label={sensor.latest ? undefined : "Chưa có dữ liệu"}>{formatSensorValue(sensor.latest?.value ?? null, sensor.unit)}</span>
      {deviceOffline && sensor.latest ? <p className="mt-1 text-xs text-muted-foreground">Dữ liệu cuối trước khi mất kết nối.</p> : null}
    </TableCell>
    <TableCell><ValueStatusBadge sensor={sensor} /></TableCell>
    <TableCell className="whitespace-nowrap text-sm text-muted-foreground">{sensor.latest ? formatDateTime(sensor.latest.recorded_at) : "Chưa có dữ liệu"}</TableCell>
    {onOpen ? <TableCell className="text-right"><Button variant="ghost" size="sm" onClick={onOpen} aria-label={`Xem biểu đồ của ${sensor.name}`}><Eye data-icon="inline-start" />Xem</Button></TableCell> : null}
  </TableRow>
}

function SensorMobileItem({
  sensor,
  deviceOffline,
  onOpen,
}: {
  sensor: MonitoringSensor
  deviceOffline: boolean
  onOpen?: () => void
}) {
  return <li className="flex flex-col gap-3 rounded-lg border p-4">
    <div className="flex items-start justify-between gap-3"><span className="font-medium">{sensor.name}</span><ValueStatusBadge sensor={sensor} /></div>
    <div><p className="text-xs text-muted-foreground">Trạng thái dữ liệu</p><DataStatusBadge sensor={sensor} /></div>
    <div className="flex flex-wrap items-end justify-between gap-3"><div><p className="text-xs text-muted-foreground">Giá trị cuối</p><p className="text-lg font-semibold tabular-nums">{formatSensorValue(sensor.latest?.value ?? null, sensor.unit)}</p>{deviceOffline && sensor.latest ? <p className="text-xs text-muted-foreground">Dữ liệu cuối trước khi mất kết nối.</p> : null}</div><div className="text-right text-xs text-muted-foreground"><p>Cập nhật cuối</p><p>{sensor.latest ? formatDateTime(sensor.latest.recorded_at) : "Chưa có dữ liệu"}</p></div></div>
    {onOpen ? <Button variant="outline" size="sm" className="w-full" onClick={onOpen} aria-label={`Xem biểu đồ của ${sensor.name}`}><Eye data-icon="inline-start" />Xem biểu đồ</Button> : null}
  </li>
}

function ActuatorStateBadge({ state }: { state: boolean | null }) {
  return <Badge variant={state === true ? "success" : state === false ? "secondary" : "outline"}>{getReportedStateLabel(state)}</Badge>
}

function SynchronizationBadge({ status }: { status: MonitoringActuator["synchronization_status"] }) {
  const label = status === "IN_SYNC" ? "Đã đồng bộ" : status === "OUT_OF_SYNC" ? "Chưa đồng bộ" : "Chưa xác định"
  return <Badge variant={status === "IN_SYNC" ? "success" : status === "OUT_OF_SYNC" ? "warning" : "outline"}>{label}</Badge>
}

function ActuatorElectricalSummary({ actuator }: { actuator: MonitoringActuator }) {
  const { voltage, current } = actuator.electrical
  if (!voltage.configured && !current.configured) return <span className="text-sm text-muted-foreground">Chưa cấu hình</span>
  const status = (metric: ElectricalFeedbackMetric) => metric.freshness === "NO_DATA" ? "Không có dữ liệu" : metric.freshness === "STALE" ? "Dữ liệu cũ" : metric.quality !== "VALID" ? electricalQualityLabel(metric.quality) : "Mới"
  const sameStatus = status(voltage) === status(current)
  const value = (metric: ElectricalFeedbackMetric) => metric.value === null ? "—" : formatSensorValue(metric.value, metric.unit)
  return <div className="flex flex-wrap items-center gap-x-2 gap-y-0.5 text-sm tabular-nums" aria-label={`Điện áp ${value(voltage)}, ${status(voltage)}; dòng điện ${value(current)}, ${status(current)}`}><span className="inline-flex items-center gap-1"><Bolt className="size-3.5" aria-hidden="true" />{value(voltage)}{sameStatus ? null : <small className="text-muted-foreground">· {status(voltage)}</small>}</span><span aria-hidden="true" className="text-muted-foreground">·</span><span className="inline-flex items-center gap-1"><Activity className="size-3.5" aria-hidden="true" />{value(current)}{sameStatus ? null : <small className="text-muted-foreground">· {status(current)}</small>}</span>{sameStatus && status(voltage) !== "Mới" ? <small className="basis-full text-muted-foreground">{status(voltage)}</small> : null}</div>
}

function ActuatorRow({
  actuator,
  onOpen,
}: {
  actuator: MonitoringActuator
  onOpen: () => void
}) {
  const command = getCommandStatus(actuator.latest_command?.status ?? null)
  const awaiting = isAwaitingActuatorConfirmation(actuator.desired_state, actuator.reported_state, actuator.latest_command?.status ?? null)
  return <TableRow>
    <TableCell className="max-w-52 font-medium"><span className="block truncate">{actuator.name}</span><p className="mt-0.5 truncate font-mono text-xs text-muted-foreground" title={actuator.code}>{actuator.code}</p></TableCell>
    <TableCell><ConnectionBadge status={actuator.connection_status} /></TableCell>
    <TableCell className="min-w-36"><ActuatorStateBadge state={actuator.reported_state} /><span className="ml-1 text-xs text-muted-foreground">→ {getDesiredStateLabel(actuator.desired_state)}</span><div className="mt-1"><SynchronizationBadge status={actuator.synchronization_status} /></div>{actuator.active_incident ? <p className="mt-1 truncate text-xs text-destructive">Sự cố: {actuator.active_incident.rule_name}</p> : null}</TableCell>
    <TableCell><Badge variant={command.tone === "danger" ? "destructive" : command.tone === "success" ? "success" : command.tone === "warning" ? "warning" : "secondary"}>{command.label}</Badge>{awaiting ? <span className="sr-only">Đang chờ thiết bị xác nhận.</span> : null}</TableCell>
    <TableCell className="tabular-nums"><ActuatorElectricalSummary actuator={actuator} /></TableCell>
    <TableCell className="whitespace-nowrap text-sm text-muted-foreground" title={actuator.last_reported_at ? formatDateTime(actuator.last_reported_at) : undefined}>{formatVietnamTime(actuator.last_reported_at)}</TableCell>
    <TableCell className="text-right"><Button variant="ghost" size="sm" onClick={onOpen} aria-label={`Xem lịch sử của ${actuator.name}`}><Eye data-icon="inline-start" />Xem</Button></TableCell>
  </TableRow>
}

export function ActuatorMobileItem({ actuator, onOpen }: { actuator: MonitoringActuator; onOpen: () => void }) {
  const command = getCommandStatus(actuator.latest_command?.status ?? null)
  const awaiting = isAwaitingActuatorConfirmation(actuator.desired_state, actuator.reported_state, actuator.latest_command?.status ?? null)
  return <li className="flex flex-col gap-3 rounded-lg border p-4">
    <div className="flex items-start justify-between gap-3"><div><span className="font-medium">{actuator.name}</span><p className="mt-1 font-mono text-xs text-muted-foreground">{actuator.code}</p></div><ActuatorStateBadge state={actuator.reported_state} /></div>
    <div className="grid grid-cols-2 gap-3 text-sm"><div><p className="text-xs text-muted-foreground">Kết nối</p><ConnectionBadge status={actuator.connection_status} /></div><div><p className="text-xs text-muted-foreground">Trạng thái</p><ActuatorStateBadge state={actuator.reported_state} /><p className="mt-1 text-xs text-muted-foreground">Yêu cầu: {getDesiredStateLabel(actuator.desired_state)}</p><div className="mt-1"><SynchronizationBadge status={actuator.synchronization_status} /></div></div><div><p className="text-xs text-muted-foreground">Lệnh gần nhất</p><p>{command.label}</p>{awaiting ? <p className="text-xs text-muted-foreground">Đang chờ xác nhận.</p> : null}</div><div><p className="text-xs text-muted-foreground">Cập nhật trạng thái</p><p>{actuator.last_reported_at ? formatDateTime(actuator.last_reported_at) : "Chưa có dữ liệu"}</p></div><div className="col-span-2"><p className="text-xs text-muted-foreground">Thông số điện</p><ActuatorElectricalSummary actuator={actuator} /></div>{actuator.active_incident ? <p className="col-span-2 text-sm text-destructive">Sự cố mở: {actuator.active_incident.rule_name}</p> : null}</div>
    <Button variant="outline" size="sm" className="w-full" onClick={onOpen} aria-label={`Xem lịch sử của ${actuator.name}`}><Eye data-icon="inline-start" />Xem lịch sử</Button>
  </li>
}

export function ProjectDeviceMonitoringCard({
  device,
  onOpenMonitoring,
  readOnly = false,
}: {
  device: MonitoringDevice
  onOpenMonitoring?: (tab: "sensors" | "actuators", resourceId?: CoreId) => void
  readOnly?: boolean
}) {
  const [collapsed, setCollapsed] = useState(false)
  return <Card className="overflow-hidden">
    <CardHeader className="gap-4 border-b bg-card">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2"><CardTitle className="truncate text-base sm:text-lg">{device.name}</CardTitle><ConnectionBadge status={device.connection_status} /></div>
          <CardDescription className="mt-1 flex flex-wrap items-center gap-x-3 gap-y-1"><span className="inline-flex items-center gap-1"><MapPin aria-hidden="true" />{device.location ?? "Chưa cập nhật vị trí"}</span><span>{device.sensors.length} cảm biến{readOnly ? "" : ` · ${device.actuators.length} cơ cấu chấp hành`}</span></CardDescription>
        </div>
        <div className="flex shrink-0 flex-wrap items-center gap-2">
          <Badge variant={device.is_enabled ? "secondary" : "outline"}>{device.is_enabled ? "Đang sử dụng" : "Đã vô hiệu hóa"}</Badge>
          {onOpenMonitoring ? <Button variant="outline" size="sm" onClick={() => onOpenMonitoring("sensors")} aria-label={`Xem biểu đồ của ${device.name}`}><Eye data-icon="inline-start" />Xem biểu đồ</Button> : null}
          <Button variant="ghost" size="icon" onClick={() => setCollapsed((current) => !current)} aria-expanded={!collapsed} aria-label={collapsed ? `Mở rộng ${device.name}` : `Thu gọn ${device.name}`}>{collapsed ? <ChevronDown /> : <ChevronUp />}</Button>
        </div>
      </div>
      <div className="flex flex-wrap items-center gap-2 text-xs text-muted-foreground"><span>Cập nhật cuối: {device.last_seen_at ? formatDateTime(device.last_seen_at) : "Chưa có dữ liệu"}</span>{device.connection_status === "OFFLINE" ? <span className="inline-flex items-center gap-1 text-destructive"><WifiOff aria-hidden="true" />Dữ liệu cuối vẫn được giữ lại</span> : null}</div>
    </CardHeader>
    {!collapsed ? <CardContent className="p-4 sm:p-6"><Tabs defaultValue="sensors">
      {!readOnly ? <TabsList className="w-full sm:w-fit"><TabsTrigger value="sensors" className="flex-1 sm:flex-none">Cảm biến ({device.sensors.length})</TabsTrigger><TabsTrigger value="actuators" className="flex-1 sm:flex-none">Cơ cấu chấp hành ({device.actuators.length})</TabsTrigger></TabsList> : null}
      <TabsContent value="sensors">
        {!device.sensors.length ? <p className="rounded-lg border border-dashed p-6 text-center text-sm text-muted-foreground">Thiết bị chưa có cảm biến.</p> : <>
          <div className="hidden overflow-hidden rounded-lg border md:block"><Table><TableHeader><TableRow><TableHead>Tên cảm biến</TableHead><TableHead>Trạng thái dữ liệu</TableHead><TableHead>Giá trị cuối</TableHead><TableHead>Trạng thái giá trị</TableHead><TableHead>Cập nhật cuối</TableHead>{onOpenMonitoring ? <TableHead className="text-right">Thao tác</TableHead> : null}</TableRow></TableHeader><TableBody>{device.sensors.map((sensor) => <SensorRow key={sensor.id} sensor={sensor} deviceOffline={device.connection_status === "OFFLINE"} onOpen={onOpenMonitoring ? () => onOpenMonitoring("sensors", sensor.id) : undefined} />)}</TableBody></Table></div>
          <ul className="grid gap-3 md:hidden">{device.sensors.map((sensor) => <SensorMobileItem key={sensor.id} sensor={sensor} deviceOffline={device.connection_status === "OFFLINE"} onOpen={onOpenMonitoring ? () => onOpenMonitoring("sensors", sensor.id) : undefined} />)}</ul>
        </>}
      </TabsContent>
      {!readOnly ? <TabsContent value="actuators">
        {!device.actuators.length ? <p className="rounded-lg border border-dashed p-6 text-center text-sm text-muted-foreground">Thiết bị chưa có cơ cấu chấp hành.</p> : <>
          <div className="hidden overflow-x-auto rounded-lg border lg:block"><Table><TableHeader><TableRow><TableHead>Cơ cấu</TableHead><TableHead>Kết nối</TableHead><TableHead>Trạng thái</TableHead><TableHead>Lệnh</TableHead><TableHead>Điện</TableHead><TableHead>Cập nhật</TableHead><TableHead className="text-right">Thao tác</TableHead></TableRow></TableHeader><TableBody>{device.actuators.map((actuator) => <ActuatorRow key={actuator.id} actuator={actuator} onOpen={() => onOpenMonitoring?.("actuators", actuator.id)} />)}</TableBody></Table></div>
          <ul className="grid gap-3 lg:hidden">{device.actuators.map((actuator) => <ActuatorMobileItem key={actuator.id} actuator={actuator} onOpen={() => onOpenMonitoring?.("actuators", actuator.id)} />)}</ul>
        </>}
      </TabsContent> : null}
    </Tabs></CardContent> : null}
  </Card>
}
