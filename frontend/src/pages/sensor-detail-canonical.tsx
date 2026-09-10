import { useEffect, useMemo, useState } from "react"
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { Activity, Pencil, Save, Trash2 } from "lucide-react"
import { Link, useNavigate, useParams, useSearchParams } from "react-router-dom"
import { toast } from "sonner"
import {
  deleteSensor, deleteSensorThreshold, getSensor, getSensorModel, getSensorTelemetry, getSensorThreshold,
  queryKeys, saveSensorThreshold, updateSensor, updateSensorThreshold,
} from "@/api/resources"
import type { MonitoringRange, RiskLevel, SensorUpdate, ThresholdAlertConfigInput } from "@/api/contracts"
import { errorMessage } from "@/api/client"
import { useAuth } from "@/app/auth"
import { buildMonitoringWindow, monitoringExpectedInterval, monitoringRangeLabel } from "@/entities/telemetry/lib/monitoring-range"
import { SensorChartRenderer } from "@/features/sensor-monitoring/components/SensorChartRenderer"
import { MonitoringRangeSelector } from "@/features/view-device-monitoring-history/ui/MonitoringRangeSelector"
import {
  AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription,
  AlertDialogFooter, AlertDialogHeader, AlertDialogTitle, AlertDialogTrigger,
} from "@/shared/ui/alert-dialog"
import { Button } from "@/shared/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/shared/ui/card"
import { EmptyState } from "@/shared/ui/empty-state"
import { Input } from "@/shared/ui/input"
import { Label } from "@/shared/ui/label"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/shared/ui/select"
import { Skeleton } from "@/shared/ui/skeleton"
import { StatusBadge } from "@/shared/ui/status-badge"
import { Switch } from "@/shared/ui/switch"
import { Textarea } from "@/shared/ui/textarea"

const ranges: readonly MonitoringRange[] = ["1h", "6h", "12h", "24h", "30d"]
const riskLevels: readonly RiskLevel[] = ["LOW", "LOW_MEDIUM", "MEDIUM", "HIGH", "VERY_HIGH", "EXTREME"]

function isMonitoringRange(value: string | null): value is MonitoringRange {
  return value !== null && ranges.some((range) => range === value)
}

function isRiskLevel(value: string): value is RiskLevel {
  return riskLevels.some((level) => level === value)
}

const emptyThreshold: ThresholdAlertConfigInput = {
  enabled: false,
  lower_threshold: null,
  upper_threshold: null,
  below_risk_level: null,
  above_risk_level: null,
  below_message: null,
  above_message: null,
  below_consequence: null,
  above_consequence: null,
  below_recommended_actions: null,
  above_recommended_actions: null,
}

export function thresholdDraftFromResponse(config: ThresholdAlertConfigInput): ThresholdAlertConfigInput {
  return {
    enabled: config.enabled,
    lower_threshold: config.lower_threshold,
    upper_threshold: config.upper_threshold,
    below_risk_level: config.below_risk_level,
    above_risk_level: config.above_risk_level,
    below_message: config.below_message,
    above_message: config.above_message,
    below_consequence: config.below_consequence,
    above_consequence: config.above_consequence,
    below_recommended_actions: config.below_recommended_actions,
    above_recommended_actions: config.above_recommended_actions,
    delay_seconds: config.delay_seconds,
  }
}

export function SensorDetailPage() {
  const params = useParams()
  const systemId = params.systemId ?? ""
  const deviceId = params.deviceId ?? ""
  const sensorId = params.sensorId ?? ""
  const validIds = Boolean(systemId && deviceId && sensorId)
  const { can } = useAuth()
  const client = useQueryClient()
  const navigate = useNavigate()
  const [searchParams, setSearchParams] = useSearchParams()
  const rangeParam = searchParams.get("range")
  const range: MonitoringRange = isMonitoringRange(rangeParam) ? rangeParam : "24h"
  const telemetryWindow = useMemo(() => buildMonitoringWindow(range), [range])
  const start = telemetryWindow.start.toISOString()
  const end = telemetryWindow.end.toISOString()

  const sensor = useQuery({ queryKey: queryKeys.sensor(systemId, deviceId, sensorId), queryFn: () => getSensor(systemId, deviceId, sensorId), enabled: validIds })
  const modelId = sensor.data?.sensor_model_id ?? 0
  const model = useQuery({ queryKey: queryKeys.sensorModel(modelId), queryFn: () => getSensorModel(modelId), enabled: modelId > 0 })
  const threshold = useQuery({ queryKey: queryKeys.sensorThreshold(systemId, deviceId, sensorId), queryFn: () => getSensorThreshold(systemId, deviceId, sensorId), enabled: validIds && can("sensors.thresholds.read") })
  const telemetry = useQuery({ queryKey: queryKeys.sensorTelemetry(systemId, deviceId, sensorId, start, end, 1000), queryFn: () => getSensorTelemetry(systemId, deviceId, sensorId, { start, end, limit: 1000 }), enabled: validIds && can("sensors.telemetry.read") })

  const [thresholdDraft, setThresholdDraft] = useState<ThresholdAlertConfigInput>(emptyThreshold)
  const [editing, setEditing] = useState(false)
  const [editDraft, setEditDraft] = useState<SensorUpdate>({})
  useEffect(() => {
    if (!threshold.data) return setThresholdDraft(emptyThreshold)
    setThresholdDraft(thresholdDraftFromResponse(threshold.data))
  }, [threshold.data])
  useEffect(() => {
    if (!sensor.data) return
    setEditDraft({ name: sensor.data.name, code: sensor.data.code, installation_location: sensor.data.installation_location, description: sensor.data.description, is_enabled: sensor.data.is_enabled })
  }, [sensor.data])

  const refreshSensor = async () => {
    await Promise.all([
      client.invalidateQueries({ queryKey: queryKeys.sensor(systemId, deviceId, sensorId) }),
      client.invalidateQueries({ queryKey: queryKeys.device(systemId, deviceId) }),
      client.invalidateQueries({ queryKey: queryKeys.devices(systemId) }),
      client.invalidateQueries({ queryKey: queryKeys.monitoringLatest(systemId) }),
    ])
  }
  const refreshThresholdViews = async () => {
    await Promise.all([
      client.invalidateQueries({ queryKey: queryKeys.sensorThreshold(systemId, deviceId, sensorId) }),
      client.invalidateQueries({ queryKey: queryKeys.monitoringLatest(systemId) }),
      client.invalidateQueries({ queryKey: queryKeys.alerts(systemId) }),
      client.invalidateQueries({ queryKey: queryKeys.deliveryHistory(systemId) }),
    ])
  }
  const saveThreshold = useMutation({ mutationFn: () => {
    return threshold.data ? updateSensorThreshold(systemId, deviceId, sensorId, thresholdDraft) : saveSensorThreshold(systemId, deviceId, sensorId, thresholdDraft)
  }, onSuccess: async (canonicalConfig) => {
    client.setQueryData(queryKeys.sensorThreshold(systemId, deviceId, sensorId), canonicalConfig)
    setThresholdDraft(thresholdDraftFromResponse(canonicalConfig))
    await refreshThresholdViews()
    toast.success("Đã cập nhật Threshold Alert thành công.")
  }, onError: (error) => toast.error(errorMessage(error)) })
  const removeThreshold = useMutation({ mutationFn: () => deleteSensorThreshold(systemId, deviceId, sensorId), onSuccess: refreshThresholdViews })
  const saveSensor = useMutation({ mutationFn: () => updateSensor(systemId, deviceId, sensorId, editDraft), onSuccess: async () => { await refreshSensor(); setEditing(false) } })
  const removeSensor = useMutation({ mutationFn: () => deleteSensor(systemId, deviceId, sensorId), onSuccess: async () => { await client.invalidateQueries({ queryKey: queryKeys.device(systemId, deviceId) }); navigate(`/aquaponics-systems/${systemId}/devices/${deviceId}`) } })

  if (!validIds) return <EmptyState icon={Activity} title="Đường dẫn Sensor không hợp lệ" description="System, Device và Sensor ID phải là số nguyên dương." />
  if (sensor.isLoading) return <Skeleton className="h-96" />
  if (sensor.isError || !sensor.data) return <EmptyState icon={Activity} title="Không thể tải Sensor" description={errorMessage(sensor.error)} />

  const value = sensor.data
  const orderedTelemetry = [...(telemetry.data ?? [])].sort((left, right) => Date.parse(left.recorded_at) - Date.parse(right.recorded_at))
  const thresholdInvalid = thresholdDraft.lower_threshold !== null && thresholdDraft.lower_threshold !== undefined
    && thresholdDraft.upper_threshold !== null && thresholdDraft.upper_threshold !== undefined
    && thresholdDraft.lower_threshold >= thresholdDraft.upper_threshold
  const thresholdFormInvalid = thresholdInvalid || thresholdDraft.delay_seconds === undefined

  return <div className="space-y-6">
    <div className="flex flex-wrap items-start justify-between gap-3">
      <div><p className="text-sm text-muted-foreground"><Link className="text-primary hover:underline" to={`/aquaponics-systems/${systemId}/devices/${deviceId}`}>Device</Link> / Sensor</p><div className="mt-1 flex flex-wrap items-center gap-3"><h2 className="text-2xl font-semibold">{value.name}</h2><StatusBadge value={value.status} /></div><p className="mt-1 text-sm text-muted-foreground">{value.code} · {value.description ?? "Không có mô tả"}</p></div>
      <div className="flex flex-wrap gap-2">{can("sensors.update") ? <Button variant="outline" onClick={() => setEditing((current) => !current)}><Pencil />Chỉnh sửa</Button> : null}{can("sensors.delete") ? <AlertDialog><AlertDialogTrigger asChild><Button variant="destructive"><Trash2 />Xoá Sensor</Button></AlertDialogTrigger><AlertDialogContent><AlertDialogHeader><AlertDialogTitle>Xoá {value.name}?</AlertDialogTitle><AlertDialogDescription>Sensor sẽ bị xoá khỏi Device hiện tại. Backend vẫn kiểm tra quyền và ràng buộc dữ liệu.</AlertDialogDescription></AlertDialogHeader><AlertDialogFooter><AlertDialogCancel>Huỷ</AlertDialogCancel><AlertDialogAction variant="destructive" onClick={() => removeSensor.mutate()}>Xoá</AlertDialogAction></AlertDialogFooter></AlertDialogContent></AlertDialog> : null}</div>
    </div>

    {editing ? <form className="grid gap-4 rounded-xl border bg-card p-5 sm:grid-cols-2" onSubmit={(event) => { event.preventDefault(); saveSensor.mutate() }}>
      <TextField id="sensor-name" label="Tên Sensor" value={editDraft.name ?? ""} onChange={(name) => setEditDraft((current) => ({ ...current, name }))} />
      <TextField id="sensor-code" label="Mã Sensor" value={editDraft.code ?? ""} onChange={(code) => setEditDraft((current) => ({ ...current, code: code.toUpperCase() }))} />
      <TextField id="sensor-location" label="Vị trí lắp đặt" value={editDraft.installation_location ?? ""} onChange={(installation_location) => setEditDraft((current) => ({ ...current, installation_location }))} />
      <TextField id="sensor-description" label="Mô tả" value={editDraft.description ?? ""} onChange={(description) => setEditDraft((current) => ({ ...current, description }))} />
      <label className="flex items-center gap-3 text-sm"><Switch checked={editDraft.is_enabled ?? value.is_enabled} onCheckedChange={(is_enabled) => setEditDraft((current) => ({ ...current, is_enabled }))} />Sensor hoạt động</label>
      <div className="flex items-center justify-end gap-2"><Button type="button" variant="ghost" onClick={() => setEditing(false)}>Huỷ</Button><Button type="submit" disabled={saveSensor.isPending}><Save />Lưu Sensor</Button></div>
      {saveSensor.isError ? <p role="alert" className="text-sm text-destructive sm:col-span-2">{errorMessage(saveSensor.error)}</p> : null}
    </form> : null}

    <div className="grid gap-4 sm:grid-cols-4"><Info label="Sensor ID" value={String(value.id)} /><Info label="SensorModel" value={model.data?.name ?? `#${value.sensor_model_id}`} /><Info label="Đơn vị" value={model.data?.unit ?? "—"} /><Info label="Vị trí" value={value.installation_location ?? "Chưa đặt vị trí"} /></div>

    <Card><CardHeader><div className="flex flex-wrap items-center justify-between gap-3"><CardTitle>Telemetry · {monitoringRangeLabel(range)}</CardTitle><MonitoringRangeSelector range={range} onRangeChange={(next) => setSearchParams({ range: next }, { replace: true })} /></div></CardHeader><CardContent>{telemetry.isLoading ? <Skeleton className="h-72" /> : telemetry.isError ? <EmptyState icon={Activity} title="Không thể tải telemetry" description={errorMessage(telemetry.error)} /> : orderedTelemetry.length ? <SensorChartRenderer modelCode={model.data?.code} data={orderedTelemetry.map((item) => ({ timestamp: item.recorded_at, value: item.value }))} unit={model.data?.unit} lastUpdatedAt={orderedTelemetry.at(-1)?.recorded_at} rangeLabel={monitoringRangeLabel(range)} expectedIntervalMs={monitoringExpectedInterval(range)} /> : <EmptyState icon={Activity} title="Chưa có telemetry" description="Không có dữ liệu trong khoảng truy vấn hiện tại." />}</CardContent></Card>

    {can("sensors.thresholds.read") ? <Card><CardHeader><CardTitle>Threshold Alert</CardTitle></CardHeader><CardContent className="space-y-4">{threshold.isLoading ? <Skeleton className="h-28" /> : threshold.isError ? <p role="alert" className="text-sm text-destructive">{errorMessage(threshold.error)}</p> : <ThresholdFields value={thresholdDraft} onChange={setThresholdDraft} />}{thresholdInvalid ? <p id="threshold-order-error" role="alert" className="text-sm text-destructive">Ngưỡng dưới phải nhỏ hơn ngưỡng trên.</p> : null}{thresholdDraft.delay_seconds === undefined ? <p role="alert" className="text-sm text-destructive">Vui lòng nhập thời gian xác nhận.</p> : null}{saveThreshold.isError || removeThreshold.isError ? <p role="alert" className="text-sm text-destructive">{errorMessage(saveThreshold.error ?? removeThreshold.error)}</p> : null}<div className="flex flex-wrap gap-2">{((threshold.data && can("sensors.thresholds.update")) || (!threshold.data && can("sensors.thresholds.create"))) ? <Button onClick={() => saveThreshold.mutate()} disabled={thresholdFormInvalid || saveThreshold.isPending} aria-busy={saveThreshold.isPending}><Save />{saveThreshold.isPending ? "Đang lưu…" : threshold.data ? "Cập nhật" : "Tạo cấu hình"}</Button> : null}{threshold.data && can("sensors.thresholds.delete") ? <Button variant="outline" onClick={() => removeThreshold.mutate()} disabled={removeThreshold.isPending}><Trash2 />Xoá cấu hình</Button> : null}</div></CardContent></Card> : null}
  </div>
}

function Info({ label, value }: { label: string; value: string }) { return <Card><CardContent className="p-4"><p className="text-xs text-muted-foreground">{label}</p><p className="mt-1 font-semibold">{value}</p></CardContent></Card> }

function TextField({ id, label, value, onChange }: { id: string; label: string; value: string; onChange: (value: string) => void }) { return <div><Label htmlFor={id}>{label}</Label><Input id={id} className="mt-1" value={value} onChange={(event) => onChange(event.target.value)} required /></div> }

function ThresholdFields({ value, onChange }: { value: ThresholdAlertConfigInput; onChange: (value: ThresholdAlertConfigInput) => void }) {
  const setNumber = (key: "lower_threshold" | "upper_threshold", raw: string) => onChange({ ...value, [key]: raw === "" ? null : Number(raw) })
  const setRisk = (key: "below_risk_level" | "above_risk_level", raw: string) => onChange({ ...value, [key]: isRiskLevel(raw) ? raw : null })
  const setContent = (key: "below_message" | "above_message" | "below_consequence" | "above_consequence" | "below_recommended_actions" | "above_recommended_actions", raw: string) => onChange({ ...value, [key]: raw || null })
  const direction = (side: "below" | "above", title: string) => {
    const lower = side === "below"
    const prefix = `threshold-${side}`
    return <section className="space-y-4 rounded-lg border p-4" aria-labelledby={`${prefix}-title`}><h3 id={`${prefix}-title`} className="font-semibold">{title}</h3><div><Label htmlFor={`${prefix}-value`}>{lower ? "Ngưỡng dưới" : "Ngưỡng trên"}</Label><Input id={`${prefix}-value`} className="mt-1" type="number" step="any" aria-invalid={thresholdInvalid(value)} aria-describedby={thresholdInvalid(value) ? "threshold-order-error" : undefined} value={(lower ? value.lower_threshold : value.upper_threshold) ?? ""} onChange={(event) => setNumber(lower ? "lower_threshold" : "upper_threshold", event.target.value)} /></div><div><Label htmlFor={`${prefix}-risk`}>{lower ? "Mức rủi ro dưới" : "Mức rủi ro trên"}</Label><Select value={(lower ? value.below_risk_level : value.above_risk_level) ?? "UNSET"} onValueChange={(raw) => setRisk(lower ? "below_risk_level" : "above_risk_level", raw)}><SelectTrigger id={`${prefix}-risk`} className="mt-1"><SelectValue /></SelectTrigger><SelectContent><SelectItem value="UNSET">Chưa cấu hình</SelectItem>{riskLevels.map((level) => <SelectItem key={level} value={level}>{level}</SelectItem>)}</SelectContent></Select></div><ContentField id={`${prefix}-message`} label={lower ? "Thông báo dưới ngưỡng" : "Thông báo trên ngưỡng"} value={(lower ? value.below_message : value.above_message) ?? ""} onChange={(raw) => setContent(lower ? "below_message" : "above_message", raw)} /><ContentField id={`${prefix}-consequence`} label={lower ? "Ảnh hưởng dưới ngưỡng" : "Ảnh hưởng trên ngưỡng"} value={(lower ? value.below_consequence : value.above_consequence) ?? ""} onChange={(raw) => setContent(lower ? "below_consequence" : "above_consequence", raw)} /><ContentField id={`${prefix}-actions`} label={lower ? "Khuyến nghị dưới ngưỡng" : "Khuyến nghị trên ngưỡng"} value={(lower ? value.below_recommended_actions : value.above_recommended_actions) ?? ""} onChange={(raw) => setContent(lower ? "below_recommended_actions" : "above_recommended_actions", raw)} /></section>
  }
  return <div className="space-y-4"><div className="grid gap-4 lg:grid-cols-2">{direction("below", "DƯỚI NGƯỠNG")}{direction("above", "TRÊN NGƯỠNG")}</div><div><Label htmlFor="threshold-delay">Thời gian xác nhận (giây)</Label><Input id="threshold-delay" className="mt-1 max-w-xs" type="number" min={0} step={1} aria-invalid={value.delay_seconds === undefined} value={value.delay_seconds ?? ""} onChange={(event) => onChange({ ...value, delay_seconds: event.target.value === "" ? undefined : Number(event.target.value) })} /><p className="mt-1 text-xs text-muted-foreground">Giữ điều kiện bất thường liên tục trong khoảng này trước khi mở cảnh báo.</p></div><label className="flex items-center gap-3 text-sm"><Switch checked={value.enabled ?? false} onCheckedChange={(enabled) => onChange({ ...value, enabled })} />Bật đánh giá ngưỡng</label></div>
}

function thresholdInvalid(value: ThresholdAlertConfigInput): boolean {
  return value.lower_threshold != null && value.upper_threshold != null
    && value.lower_threshold >= value.upper_threshold
}

function ContentField({ id, label, value, onChange }: { id: string; label: string; value: string; onChange: (value: string) => void }) {
  return <div><Label htmlFor={id}>{label}</Label><Textarea id={id} className="mt-1" value={value} onChange={(event) => onChange(event.target.value)} /></div>
}
