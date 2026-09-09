import { Activity, AlertTriangle, Cpu, Gauge, Radio, TriangleAlert } from "lucide-react"
import type { Alert, AquaponicsSystem, Device, MonitoringLatest } from "@/api/contracts"
import { Badge } from "@/shared/ui/badge"
import { Card, CardContent, CardHeader, CardTitle } from "@/shared/ui/card"
import { EmptyState } from "@/shared/ui/empty-state"
import { StatusBadge } from "@/shared/ui/status-badge"

export interface AquaponicsSystemOverviewViewModel {
  system: AquaponicsSystem
  deviceCount: number
  onlineDevices: number
  sensorCount: number
  reportingSensors: number
  actuatorCount: number
  activeAlerts: number
  criticalAlerts: number
  devices: Device[]
  latest: MonitoringLatest | undefined
  alerts: Alert[]
  staleSensors: number
  noDataSensors: number
  outOfSyncActuators: number
  measurements: { unit: string; count: number; values: { name: string; value: number; freshness: string; quality: string }[] }[]
}

export function createOverviewViewModel(system: AquaponicsSystem, devices: Device[], latest: MonitoringLatest | undefined, alerts: Alert[]): AquaponicsSystemOverviewViewModel {
  const latestDevices = latest?.devices ?? []
  const onlineDevices = latestDevices.filter((device) => device.connection_status === "ONLINE").length
  const sensorCount = devices.reduce((total, device) => total + device.sensors.length, 0)
  const actuatorCount = devices.reduce((total, device) => total + device.actuators.length, 0)
  const reportingSensors = latestDevices.reduce((total, device) => total + device.sensors.filter((sensor) => sensor.latest?.value !== null && sensor.latest?.value !== undefined).length, 0)
  const sensors = latestDevices.flatMap((device) => device.sensors)
  const grouped = new Map<string, { name: string; value: number; freshness: string; quality: string }[]>()
  sensors.forEach((sensor) => { if (sensor.latest?.value === null || sensor.latest?.value === undefined) return; const values = grouped.get(sensor.unit) ?? []; values.push({ name: sensor.name, value: sensor.latest.value, freshness: sensor.latest.freshness ?? sensor.data_status, quality: sensor.latest.quality ?? "UNVALIDATED" }); grouped.set(sensor.unit, values) })
  return { system, devices, latest, alerts, deviceCount: devices.length, onlineDevices, sensorCount, reportingSensors, actuatorCount, activeAlerts: alerts.filter((alert) => alert.status !== "RESOLVED").length, criticalAlerts: alerts.filter((alert) => alert.severity === "CRITICAL" && alert.status !== "RESOLVED").length, staleSensors: sensors.filter((sensor) => (sensor.latest?.freshness ?? sensor.data_status) === "STALE").length, noDataSensors: sensors.filter((sensor) => !sensor.latest || sensor.latest.value === null || sensor.data_status === "NO_DATA").length, outOfSyncActuators: latestDevices.flatMap((device) => device.actuators).filter((actuator) => actuator.synchronization_status === "OUT_OF_SYNC").length, measurements: [...grouped.entries()].map(([unit, values]) => ({ unit, count: values.length, values })) }
}

export function OverviewDashboard({ model }: { model: AquaponicsSystemOverviewViewModel }) {
  const latestByDevice = new Map((model.latest?.devices ?? []).map((device) => [device.id, device]))
  const cards = [
    { label: "Thiết bị", value: model.deviceCount, detail: `${model.onlineDevices} đang trực tuyến`, icon: Cpu },
    { label: "Sensor", value: model.sensorCount, detail: `${model.reportingSensors} đang có dữ liệu`, icon: Activity },
    { label: "Actuator", value: model.actuatorCount, detail: "Thiết bị hỗn hợp được hỗ trợ", icon: Radio },
    { label: "Cảnh báo đang mở", value: model.activeAlerts, detail: `${model.criticalAlerts} mức nghiêm trọng`, icon: TriangleAlert },
  ]
  return <div className="space-y-6">
    <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">{cards.map(({ label, value, detail, icon: Icon }) => <Card key={label}><CardContent className="flex items-start justify-between p-5"><div><p className="text-sm text-muted-foreground">{label}</p><p className="mt-2 text-3xl font-semibold tracking-tight">{value}</p><p className="mt-1 text-xs text-muted-foreground">{detail}</p></div><div className="rounded-xl bg-primary/10 p-3 text-primary"><Icon className="size-5" aria-hidden="true" /></div></CardContent></Card>)}</div>
    {(model.staleSensors || model.noDataSensors || model.outOfSyncActuators) ? <Card className="border-amber-500/40"><CardContent className="flex flex-wrap gap-4 p-4 text-sm"><span className="font-medium">Chất lượng vận hành cần chú ý:</span>{model.staleSensors ? <span>{model.staleSensors} Sensor cũ</span> : null}{model.noDataSensors ? <span>{model.noDataSensors} Sensor chưa có dữ liệu</span> : null}{model.outOfSyncActuators ? <span>{model.outOfSyncActuators} Actuator lệch trạng thái</span> : null}</CardContent></Card> : null}
    <div className="grid gap-6 xl:grid-cols-[1.3fr_0.7fr]">
      <Card><CardHeader><CardTitle className="flex items-center gap-2"><Gauge className="size-5 text-primary" aria-hidden="true" />Tình trạng thiết bị</CardTitle></CardHeader><CardContent className="space-y-3">{model.devices.length ? model.devices.map((device) => { const current = latestByDevice.get(device.id); return <div key={device.id} className="flex flex-wrap items-center justify-between gap-3 rounded-xl border p-4"><div><p className="font-medium">{device.name}</p><p className="text-sm text-muted-foreground">{device.code} · {device.sensors.length} Sensor · {device.actuators.length} Actuator</p></div><div className="flex items-center gap-2"><StatusBadge value={current?.connection_status ?? device.status} /><span className="text-xs text-muted-foreground">{device.location ?? "Chưa đặt vị trí"}</span></div></div> }) : <EmptyState icon={Cpu} title="Chưa có thiết bị" description="Thêm thiết bị để bắt đầu theo dõi hệ thống." />}</CardContent></Card>
      <Card><CardHeader><CardTitle className="flex items-center gap-2"><AlertTriangle className="size-5 text-amber-600" aria-hidden="true" />Cần chú ý</CardTitle></CardHeader><CardContent className="space-y-3">{model.alerts.filter((alert) => alert.status !== "RESOLVED").length ? model.alerts.filter((alert) => alert.status !== "RESOLVED").slice(0, 5).map((alert) => <div key={alert.id} className="rounded-xl border p-3"><div className="flex items-center justify-between gap-2"><Badge variant={alert.severity === "CRITICAL" ? "destructive" : "warning"}>{alert.severity === "CRITICAL" ? "Nghiêm trọng" : "Cảnh báo"}</Badge><span className="text-xs text-muted-foreground">{new Date(alert.started_at).toLocaleString("vi-VN")}</span></div><p className="mt-2 text-sm font-medium">{alert.message}</p><p className="mt-1 text-xs text-muted-foreground">{alert.metric} · {alert.actual_value ?? "Chưa có giá trị"}</p></div>) : <EmptyState icon={AlertTriangle} title="Không có cảnh báo" description="Hệ thống chưa ghi nhận cảnh báo cần xử lý." />}</CardContent></Card>
    </div>
    <Card><CardHeader><CardTitle>Nhóm phép đo mới nhất</CardTitle></CardHeader><CardContent>{model.measurements.length ? <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">{model.measurements.map((group) => <div key={group.unit} className="rounded-xl border p-4"><div className="flex items-center justify-between"><p className="font-medium">Đơn vị {group.unit}</p><Badge variant="secondary">{group.count}</Badge></div><div className="mt-3 space-y-2">{group.values.slice(0, 4).map((reading) => <div key={reading.name} className="flex items-center justify-between gap-2 text-sm"><span className="truncate text-muted-foreground">{reading.name}</span><span className="whitespace-nowrap font-medium">{reading.value} {group.unit} · {reading.freshness} · {reading.quality}</span></div>)}</div></div>)}</div> : <p className="text-sm text-muted-foreground">Chưa có phép đo; giá trị thiếu không được thay bằng 0.</p>}</CardContent></Card>
  </div>
}
