import { useState } from "react"
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { Activity, Save, Trash2 } from "lucide-react"
import { Link, useParams } from "react-router-dom"
import { deleteSensorThreshold, getSensor, getSensorTelemetry, getSensorThreshold, saveSensorThreshold, updateSensorThreshold } from "@/api/resources"
import type { ThresholdAlertConfigInput } from "@/api/contracts"
import { useAuth } from "@/app/auth"
import { MonitoringChart } from "@/widgets/canonical-monitoring/MonitoringChart"
import { Button } from "@/shared/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/shared/ui/card"
import { EmptyState } from "@/shared/ui/empty-state"
import { Input } from "@/shared/ui/input"
import { Label } from "@/shared/ui/label"
import { Skeleton } from "@/shared/ui/skeleton"
import { StatusBadge } from "@/shared/ui/status-badge"
import { errorMessage } from "@/api/client"

export function SensorDetailPage() {
  const systemId = Number(useParams().systemId); const deviceId = Number(useParams().deviceId); const sensorId = Number(useParams().sensorId); const { can } = useAuth(); const client = useQueryClient()
  const sensor = useQuery({ queryKey: ["sensor", systemId, deviceId, sensorId], queryFn: () => getSensor(systemId, deviceId, sensorId), enabled: sensorId > 0 })
  const threshold = useQuery({ queryKey: ["sensor-threshold", systemId, deviceId, sensorId], queryFn: () => getSensorThreshold(systemId, deviceId, sensorId), enabled: sensorId > 0 && can("sensors.thresholds.read") })
  const telemetry = useQuery({ queryKey: ["sensor-telemetry", systemId, deviceId, sensorId], queryFn: () => getSensorTelemetry(systemId, deviceId, sensorId, { limit: 200 }), enabled: sensorId > 0 && can("sensors.telemetry.read") })
  const [draft, setDraft] = useState<ThresholdAlertConfigInput | null>(null)
  const config = draft ?? (threshold.data ? { enabled: threshold.data.enabled, lower_threshold: threshold.data.lower_threshold, upper_threshold: threshold.data.upper_threshold, below_risk_level: threshold.data.below_risk_level, above_risk_level: threshold.data.above_risk_level, below_message: threshold.data.below_message, above_message: threshold.data.above_message } : { enabled: true, lower_threshold: null, upper_threshold: null })
  const save = useMutation({ mutationFn: () => threshold.data ? updateSensorThreshold(systemId, deviceId, sensorId, config) : saveSensorThreshold(systemId, deviceId, sensorId, config), onSuccess: () => { setDraft(null); void client.invalidateQueries({ queryKey: ["sensor-threshold", systemId, deviceId, sensorId] }) } })
  const remove = useMutation({ mutationFn: () => deleteSensorThreshold(systemId, deviceId, sensorId), onSuccess: () => void client.invalidateQueries({ queryKey: ["sensor-threshold", systemId, deviceId, sensorId] }) })
  if (sensor.isLoading) return <Skeleton className="h-96" />
  if (sensor.isError || !sensor.data) return <EmptyState icon={Activity} title="Không thể tải Sensor" description={errorMessage(sensor.error)} />
  const value = sensor.data; const chart = telemetry.data ? { sensor_id: value.id, unit: "", points: telemetry.data.map((item) => ({ recorded_at: item.recorded_at, value: item.value })), gaps: [] } : null
  return <div className="space-y-6"><div><p className="text-sm text-muted-foreground"><Link className="text-primary hover:underline" to={`/aquaponics-systems/${systemId}/devices/${deviceId}`}>Device</Link> / Sensor</p><div className="mt-1 flex flex-wrap items-center gap-3"><h2 className="text-2xl font-semibold">{value.name}</h2><StatusBadge value={value.status} /></div><p className="mt-1 text-sm text-muted-foreground">{value.code} · {value.description ?? "Không có mô tả"}</p></div><div className="grid gap-4 sm:grid-cols-3"><Info label="Sensor ID" value={String(value.id)} /><Info label="SensorModel" value={String(value.sensor_model_id)} /><Info label="Vị trí" value={value.installation_location ?? "Chưa đặt vị trí"} /></div>{chart ? <MonitoringChart series={chart} /> : <EmptyState icon={Activity} title="Chưa có telemetry" description="Không có dữ liệu trong khoảng truy vấn hiện tại." />}{can("sensors.thresholds.read") ? <Card><CardHeader><CardTitle>Threshold Alert</CardTitle></CardHeader><CardContent className="space-y-4">{threshold.isLoading ? <Skeleton className="h-20" /> : threshold.data || draft ? <div className="grid gap-4 sm:grid-cols-3"><Field label="Ngưỡng dưới" value={config.lower_threshold ?? ""} onChange={(value) => setDraft({ ...config, lower_threshold: value === "" ? null : Number(value) })} /><Field label="Ngưỡng trên" value={config.upper_threshold ?? ""} onChange={(value) => setDraft({ ...config, upper_threshold: value === "" ? null : Number(value) })} /><label className="flex items-center gap-2 text-sm"><input type="checkbox" checked={config.enabled ?? true} onChange={(event) => setDraft({ ...config, enabled: event.target.checked })} />Bật cảnh báo</label></div> : <p className="text-sm text-muted-foreground">Chưa cấu hình.</p>}{can("sensors.thresholds.create") || can("sensors.thresholds.update") ? <div className="flex flex-wrap gap-2"><Button onClick={() => { setDraft(config); save.mutate() }} disabled={save.isPending}><Save />{threshold.data ? "Cập nhật" : "Tạo cấu hình"}</Button>{threshold.data && can("sensors.thresholds.delete") ? <Button variant="outline" onClick={() => remove.mutate()} disabled={remove.isPending}><Trash2 />Xoá cấu hình</Button> : null}</div> : null}</CardContent></Card> : null}</div>
}
function Info({ label, value }: { label: string; value: string }) { return <Card><CardContent className="p-4"><p className="text-xs text-muted-foreground">{label}</p><p className="mt-1 font-semibold">{value}</p></CardContent></Card> }
function Field({ label, value, onChange }: { label: string; value: number | string; onChange: (value: string) => void }) { return <div><Label>{label}</Label><Input className="mt-1" type="number" value={value} onChange={(event) => onChange(event.target.value)} /></div> }
