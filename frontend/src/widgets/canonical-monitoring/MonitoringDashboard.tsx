import { useState } from "react"
import { Activity, AlertTriangle, Radio } from "lucide-react"
import type { MonitoringLatest, MonitoringRange, MonitoringSeriesRead } from "@/api/contracts"
import { CanonicalDeviceMonitoringDialog } from "@/features/view-device-monitoring-history/ui/CanonicalDeviceMonitoringDialog"
import { Badge } from "@/shared/ui/badge"
import { Card, CardContent, CardHeader, CardTitle } from "@/shared/ui/card"
import { StatusBadge } from "@/shared/ui/status-badge"
import { MonitoringChart } from "./MonitoringChart"

export function MonitoringDashboard({ latest, series, range }: { latest: MonitoringLatest; series: MonitoringSeriesRead; range: MonitoringRange }) {
  const [selectedDeviceId, setSelectedDeviceId] = useState<number | null>(null)
  const sensors = latest.devices.flatMap((device) => device.sensors.map((sensor) => ({ ...sensor, device })))
  const actuators = latest.devices.flatMap((device) => device.actuators.map((actuator) => ({ ...actuator, device })))
  const reporting = sensors.filter((sensor) => sensor.latest?.value !== null && sensor.latest?.value !== undefined).length
  return <div className="space-y-6">
    <div className="grid gap-4 sm:grid-cols-3"><Metric icon={Activity} label="Sensor đang báo" value={`${reporting}/${sensors.length}`} /><Metric icon={Radio} label="Actuator" value={String(actuators.length)} /><Metric icon={AlertTriangle} label="Thiết bị" value={String(latest.devices.length)} /></div>
    <Card><CardHeader><CardTitle>Device monitoring</CardTitle></CardHeader><CardContent className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">{latest.devices.map((device) => <button type="button" key={device.id} className="rounded-xl border p-4 text-left transition-colors hover:border-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring" onClick={() => setSelectedDeviceId(device.id)}><div className="flex items-center justify-between gap-2"><span className="font-medium">{device.name}</span><StatusBadge value={device.connection_status} /></div><p className="mt-2 text-xs text-muted-foreground">{device.sensors.length} Sensor · {device.actuators.length} Actuator · {device.last_seen_at ? new Date(device.last_seen_at).toLocaleString("vi-VN") : "Chưa kết nối"}</p></button>)}{!latest.devices.length ? <p className="text-sm text-muted-foreground">Hệ thống chưa có Device.</p> : null}</CardContent></Card>
    <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">{sensors.map((sensor) => <Card key={sensor.id}><CardContent className="p-4"><div className="flex items-start justify-between gap-2"><div><p className="font-medium">{sensor.name}</p><p className="text-xs text-muted-foreground">{sensor.device.name} · {sensor.code}</p></div><StatusBadge value={sensor.latest?.freshness ?? sensor.data_status} /></div><p className="mt-5 text-3xl font-semibold">{sensor.latest?.value ?? "—"}<span className="ml-1 text-sm font-normal text-muted-foreground">{sensor.unit}</span></p><div className="mt-3 flex flex-wrap gap-2 text-xs text-muted-foreground"><span>Quality: {sensor.latest?.quality ?? "NO_DATA"}</span><span>Ngưỡng dưới: {sensor.lower_threshold ?? "—"}</span><span>Ngưỡng trên: {sensor.upper_threshold ?? "—"}</span></div></CardContent></Card>)}</div>
    {actuators.length ? <Card><CardHeader><CardTitle>Trạng thái Actuator</CardTitle></CardHeader><CardContent className="grid gap-3 sm:grid-cols-2">{actuators.map((actuator) => <div key={actuator.id} className="flex items-center justify-between gap-3 rounded-xl border p-4"><div><p className="font-medium">{actuator.name}</p><p className="text-xs text-muted-foreground">{actuator.device.name} · {actuator.actuator_model ?? "Chưa có model"}</p>{actuator.active_alert ? <p className="mt-1 text-xs text-destructive">{actuator.active_alert.condition_summary}</p> : null}</div><div className="text-right"><Badge variant={actuator.reported_state === true ? "success" : "secondary"}>{actuator.reported_state === null ? "CHƯA BÁO VỀ" : actuator.reported_state ? "ĐANG BẬT" : "ĐANG TẮT"}</Badge><p className="mt-1 text-xs text-muted-foreground">{actuator.synchronization_status}</p></div></div>)}</CardContent></Card> : null}
    <div className="grid gap-4 xl:grid-cols-2">{series.series.map((item) => <MonitoringChart key={item.sensor_id} series={item} />)}</div>
    <CanonicalDeviceMonitoringDialog device={latest.devices.find((device) => device.id === selectedDeviceId) ?? null} series={series} range={range} open={selectedDeviceId !== null} onOpenChange={(open) => { if (!open) setSelectedDeviceId(null) }} />
  </div>
}

function Metric({ icon: Icon, label, value }: { icon: typeof Activity; label: string; value: string }) {
  return <Card><CardContent className="flex items-center gap-3 p-4"><div className="rounded-xl bg-primary/10 p-3 text-primary"><Icon className="size-5" aria-hidden="true" /></div><div><p className="text-xs text-muted-foreground">{label}</p><p className="text-xl font-semibold">{value}</p></div></CardContent></Card>
}
