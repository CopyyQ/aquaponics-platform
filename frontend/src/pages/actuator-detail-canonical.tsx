import { useEffect, useState } from "react"
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { CheckCircle2, CirclePower, Clock3, Gauge, Pencil, Save, Trash2 } from "lucide-react"
import { Link, useNavigate, useParams } from "react-router-dom"
import {
  createCommand, deleteActuator, deleteActuatorThreshold, getActuator, getActuatorThreshold,
  listActuatorCommands, listActuatorReadings, queryKeys, saveActuatorThreshold, updateActuator,
  updateActuatorThreshold,
} from "@/api/resources"
import type { ActuatorThresholdMetric, ActuatorUpdate, ThresholdAlertConfig, ThresholdAlertConfigInput } from "@/api/contracts"
import { errorMessage } from "@/api/client"
import { useAuth } from "@/app/auth"
import {
  AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription,
  AlertDialogFooter, AlertDialogHeader, AlertDialogTitle, AlertDialogTrigger,
} from "@/shared/ui/alert-dialog"
import { Button } from "@/shared/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/shared/ui/card"
import { EmptyState } from "@/shared/ui/empty-state"
import { Input } from "@/shared/ui/input"
import { Label } from "@/shared/ui/label"
import { Skeleton } from "@/shared/ui/skeleton"
import { StatusBadge } from "@/shared/ui/status-badge"
import { Switch } from "@/shared/ui/switch"
import { Textarea } from "@/shared/ui/textarea"

export function ActuatorDetailPage() {
  const params = useParams()
  const systemId = Number(params.systemId)
  const deviceId = Number(params.deviceId)
  const actuatorId = Number(params.actuatorId)
  const validIds = systemId > 0 && deviceId > 0 && actuatorId > 0
  const { can } = useAuth()
  const client = useQueryClient()
  const navigate = useNavigate()
  const [editing, setEditing] = useState(false)
  const [editDraft, setEditDraft] = useState<ActuatorUpdate>({})

  const actuator = useQuery({ queryKey: queryKeys.actuator(systemId, deviceId, actuatorId), queryFn: () => getActuator(systemId, deviceId, actuatorId), enabled: validIds, refetchInterval: 10_000 })
  const readings = useQuery({ queryKey: queryKeys.actuatorReadings(systemId, deviceId, actuatorId, 50), queryFn: () => listActuatorReadings(systemId, deviceId, actuatorId, 50), enabled: validIds && can("actuators.readings.read"), refetchInterval: 15_000 })
  const commands = useQuery({ queryKey: queryKeys.actuatorCommands(systemId, deviceId, actuatorId, 20), queryFn: () => listActuatorCommands(systemId, deviceId, actuatorId, 20), enabled: validIds && can("actuators.commands.read"), refetchInterval: 5_000 })
  const voltage = useQuery({ queryKey: queryKeys.actuatorThreshold(systemId, deviceId, actuatorId, "VOLTAGE"), queryFn: () => getActuatorThreshold(systemId, deviceId, actuatorId, "VOLTAGE"), enabled: validIds && can("actuators.thresholds.read") })
  const current = useQuery({ queryKey: queryKeys.actuatorThreshold(systemId, deviceId, actuatorId, "CURRENT"), queryFn: () => getActuatorThreshold(systemId, deviceId, actuatorId, "CURRENT"), enabled: validIds && can("actuators.thresholds.read") })

  useEffect(() => {
    if (!actuator.data) return
    setEditDraft({ name: actuator.data.name, code: actuator.data.code, location: actuator.data.location, notes: actuator.data.notes, is_enabled: actuator.data.is_enabled })
  }, [actuator.data])

  const refreshRuntime = async () => {
    await Promise.all([
      client.invalidateQueries({ queryKey: queryKeys.actuator(systemId, deviceId, actuatorId) }),
      client.invalidateQueries({ queryKey: queryKeys.actuatorCommands(systemId, deviceId, actuatorId, 20) }),
      client.invalidateQueries({ queryKey: queryKeys.device(systemId, deviceId) }),
      client.invalidateQueries({ queryKey: queryKeys.monitoringLatest(systemId) }),
      client.invalidateQueries({ queryKey: queryKeys.scada(systemId) }),
    ])
  }
  const command = useMutation({ mutationFn: (desired_state: boolean) => createCommand(systemId, deviceId, actuatorId, { desired_state }), onSuccess: refreshRuntime })
  const saveActuator = useMutation({ mutationFn: () => updateActuator(systemId, deviceId, actuatorId, editDraft), onSuccess: async () => { await refreshRuntime(); setEditing(false) } })
  const removeActuator = useMutation({ mutationFn: () => deleteActuator(systemId, deviceId, actuatorId), onSuccess: async () => { await client.invalidateQueries({ queryKey: queryKeys.device(systemId, deviceId) }); navigate(`/aquaponics-systems/${systemId}/devices/${deviceId}`) } })

  if (!validIds) return <EmptyState icon={CirclePower} title="Đường dẫn Actuator không hợp lệ" description="System, Device và Actuator ID phải là số nguyên dương." />
  if (actuator.isLoading) return <Skeleton className="h-96" />
  if (actuator.isError || !actuator.data) return <EmptyState icon={CirclePower} title="Không thể tải Actuator" description={errorMessage(actuator.error)} />

  const value = actuator.data
  const latestCommand = commands.data?.[0]
  const outOfSync = value.desired_state !== null && value.reported_state !== null && value.desired_state !== value.reported_state

  return <div className="space-y-6">
    <div className="flex flex-wrap items-start justify-between gap-3"><div><p className="text-sm text-muted-foreground"><Link className="text-primary hover:underline" to={`/aquaponics-systems/${systemId}/devices/${deviceId}`}>Device</Link> / Actuator</p><div className="mt-1 flex flex-wrap items-center gap-3"><h2 className="text-2xl font-semibold">{value.name}</h2><StatusBadge value={value.is_enabled ? "ACTIVE" : "DISABLED"} />{outOfSync ? <StatusBadge value="OUT_OF_SYNC" /> : null}</div><p className="mt-1 text-sm text-muted-foreground">{value.code} · {value.location ?? "Chưa đặt vị trí"}</p></div><div className="flex flex-wrap gap-2">{can("actuators.update") ? <Button variant="outline" onClick={() => setEditing((current) => !current)}><Pencil />Chỉnh sửa</Button> : null}{can("actuators.delete") ? <AlertDialog><AlertDialogTrigger asChild><Button variant="destructive"><Trash2 />Xoá Actuator</Button></AlertDialogTrigger><AlertDialogContent><AlertDialogHeader><AlertDialogTitle>Xoá {value.name}?</AlertDialogTitle><AlertDialogDescription>Actuator sẽ bị xoá khỏi Device hiện tại. Backend vẫn kiểm tra quyền và ràng buộc dữ liệu.</AlertDialogDescription></AlertDialogHeader><AlertDialogFooter><AlertDialogCancel>Huỷ</AlertDialogCancel><AlertDialogAction variant="destructive" onClick={() => removeActuator.mutate()}>Xoá</AlertDialogAction></AlertDialogFooter></AlertDialogContent></AlertDialog> : null}</div></div>

    {editing ? <form className="grid gap-4 rounded-xl border bg-card p-5 sm:grid-cols-2" onSubmit={(event) => { event.preventDefault(); saveActuator.mutate() }}><TextField id="actuator-name" label="Tên Actuator" value={editDraft.name ?? ""} onChange={(name) => setEditDraft((currentValue) => ({ ...currentValue, name }))} /><TextField id="actuator-code" label="Mã Actuator" value={editDraft.code ?? ""} onChange={(code) => setEditDraft((currentValue) => ({ ...currentValue, code: code.toUpperCase() }))} /><TextField id="actuator-location" label="Vị trí" value={editDraft.location ?? ""} onChange={(location) => setEditDraft((currentValue) => ({ ...currentValue, location }))} /><div><Label htmlFor="actuator-notes">Ghi chú</Label><Textarea id="actuator-notes" className="mt-1" value={editDraft.notes ?? ""} onChange={(event) => setEditDraft((currentValue) => ({ ...currentValue, notes: event.target.value }))} /></div><label className="flex items-center gap-3 text-sm"><Switch checked={editDraft.is_enabled ?? value.is_enabled} onCheckedChange={(is_enabled) => setEditDraft((currentValue) => ({ ...currentValue, is_enabled }))} />Actuator hoạt động</label><div className="flex items-center justify-end gap-2"><Button type="button" variant="ghost" onClick={() => setEditing(false)}>Huỷ</Button><Button type="submit" disabled={saveActuator.isPending}><Save />Lưu Actuator</Button></div>{saveActuator.isError ? <p role="alert" className="text-sm text-destructive sm:col-span-2">{errorMessage(saveActuator.error)}</p> : null}</form> : null}

    <div className="grid gap-4 sm:grid-cols-5"><Info label="Model" value={value.actuator_model_id ? String(value.actuator_model_id) : "—"} /><Info label="Desired state" value={stateText(value.desired_state)} /><Info label="Reported state" value={stateText(value.reported_state)} /><Info label="Command" value={latestCommand?.status ?? "Chưa có"} /><Info label="Điện áp / dòng" value={`${value.voltage_v ?? "—"} V · ${value.current_a ?? "—"} A`} /></div>

    {can("actuators.commands.create") ? <Card><CardHeader><CardTitle className="flex items-center gap-2"><CirclePower className="size-5 text-primary" />Điều khiển vận hành</CardTitle></CardHeader><CardContent className="space-y-3"><div className="flex flex-wrap items-center gap-3"><Button onClick={() => command.mutate(true)} disabled={command.isPending}><CheckCircle2 />Bật</Button><Button variant="outline" onClick={() => command.mutate(false)} disabled={command.isPending}>Tắt</Button><span className="text-sm text-muted-foreground">Desired state chỉ đổi khi backend nhận lệnh; reported state vẫn là trạng thái thiết bị báo về.</span></div>{command.isError ? <p role="alert" className="text-sm text-destructive">{errorMessage(command.error)}</p> : null}</CardContent></Card> : null}

    <div className="grid gap-5 xl:grid-cols-2"><HistoryCard title="Command history" icon={Clock3}>{commands.isError ? <p className="text-sm text-destructive">{errorMessage(commands.error)}</p> : commands.data?.length ? commands.data.map((item) => <div key={item.command_id} className="flex items-center justify-between gap-3 border-b py-3 last:border-0"><div><p>{item.desired_state ? "Bật" : "Tắt"}</p><p className="text-xs text-muted-foreground">Reported: {stateText(item.reported_state)}</p></div><div className="text-right"><StatusBadge value={item.status} /><p className="mt-1 text-xs text-muted-foreground">{new Date(item.requested_at).toLocaleString("vi-VN")}</p></div></div>) : <p className="text-sm text-muted-foreground">Chưa có lịch sử command.</p>}</HistoryCard><HistoryCard title="Electrical readings" icon={Gauge}>{readings.isError ? <p className="text-sm text-destructive">{errorMessage(readings.error)}</p> : readings.data?.length ? readings.data.map((item) => <div key={item.id} className="flex items-center justify-between gap-3 border-b py-3 last:border-0"><div><p>{item.voltage_v ?? "—"} V · {item.current_a ?? "—"} A</p><p className="text-xs text-muted-foreground">Quality: {item.quality || "—"}</p></div><span className="text-xs text-muted-foreground">{new Date(item.recorded_at).toLocaleString("vi-VN")}</span></div>) : <p className="text-sm text-muted-foreground">Chưa có reading.</p>}</HistoryCard></div>

    {can("actuators.thresholds.read") ? <div className="grid gap-5 md:grid-cols-2"><ThresholdCard metric="VOLTAGE" config={voltage.data ?? null} loading={voltage.isLoading} systemId={systemId} deviceId={deviceId} actuatorId={actuatorId} canCreate={can("actuators.thresholds.create")} canUpdate={can("actuators.thresholds.update")} canDelete={can("actuators.thresholds.delete")} /><ThresholdCard metric="CURRENT" config={current.data ?? null} loading={current.isLoading} systemId={systemId} deviceId={deviceId} actuatorId={actuatorId} canCreate={can("actuators.thresholds.create")} canUpdate={can("actuators.thresholds.update")} canDelete={can("actuators.thresholds.delete")} /></div> : null}
  </div>
}

function stateText(value: boolean | null) { return value === null ? "Chưa báo về" : value ? "Bật" : "Tắt" }
function Info({ label, value }: { label: string; value: string }) { return <Card><CardContent className="p-4"><p className="text-xs text-muted-foreground">{label}</p><p className="mt-1 font-semibold">{value}</p></CardContent></Card> }
function HistoryCard({ title, icon: Icon, children }: { title: string; icon: typeof Clock3; children: React.ReactNode }) { return <Card><CardHeader><CardTitle className="flex items-center gap-2"><Icon className="size-5 text-primary" />{title}</CardTitle></CardHeader><CardContent>{children}</CardContent></Card> }
function TextField({ id, label, value, onChange }: { id: string; label: string; value: string; onChange: (value: string) => void }) { return <div><Label htmlFor={id}>{label}</Label><Input id={id} className="mt-1" value={value} onChange={(event) => onChange(event.target.value)} required /></div> }

function ThresholdCard({ metric, config, loading, canCreate, canUpdate, canDelete, systemId, deviceId, actuatorId }: { metric: ActuatorThresholdMetric; config: ThresholdAlertConfig | null; loading: boolean; canCreate: boolean; canUpdate: boolean; canDelete: boolean; systemId: number; deviceId: number; actuatorId: number }) {
  const client = useQueryClient()
  const [draft, setDraft] = useState<ThresholdAlertConfigInput>({ enabled: true, lower_threshold: null, upper_threshold: null })
  useEffect(() => { setDraft(config ? { enabled: config.enabled, lower_threshold: config.lower_threshold, upper_threshold: config.upper_threshold, below_risk_level: config.below_risk_level, above_risk_level: config.above_risk_level, below_message: config.below_message, above_message: config.above_message } : { enabled: true, lower_threshold: null, upper_threshold: null }) }, [config])
  const key = queryKeys.actuatorThreshold(systemId, deviceId, actuatorId, metric)
  const save = useMutation({ mutationFn: () => config ? updateActuatorThreshold(systemId, deviceId, actuatorId, metric, draft) : saveActuatorThreshold(systemId, deviceId, actuatorId, metric, draft), onSuccess: () => client.invalidateQueries({ queryKey: key }) })
  const remove = useMutation({ mutationFn: () => deleteActuatorThreshold(systemId, deviceId, actuatorId, metric), onSuccess: () => client.invalidateQueries({ queryKey: key }) })
  const invalid = draft.lower_threshold !== null && draft.lower_threshold !== undefined && draft.upper_threshold !== null && draft.upper_threshold !== undefined && draft.lower_threshold > draft.upper_threshold
  const canSave = config ? canUpdate : canCreate
  return <Card><CardHeader><CardTitle>{metric === "VOLTAGE" ? "Voltage Alert threshold" : "Current Alert threshold"}</CardTitle></CardHeader><CardContent className="space-y-3">{loading ? <Skeleton className="h-24" /> : <><div className="grid grid-cols-2 gap-3"><div><Label htmlFor={`${metric}-min`}>Min</Label><Input id={`${metric}-min`} className="mt-1" type="number" step="any" value={draft.lower_threshold ?? ""} onChange={(event) => setDraft((currentValue) => ({ ...currentValue, lower_threshold: event.target.value === "" ? null : Number(event.target.value) }))} /></div><div><Label htmlFor={`${metric}-max`}>Max</Label><Input id={`${metric}-max`} className="mt-1" type="number" step="any" value={draft.upper_threshold ?? ""} onChange={(event) => setDraft((currentValue) => ({ ...currentValue, upper_threshold: event.target.value === "" ? null : Number(event.target.value) }))} /></div></div><label className="flex items-center gap-3 text-sm"><Switch checked={draft.enabled ?? true} onCheckedChange={(enabled) => setDraft((currentValue) => ({ ...currentValue, enabled }))} />Bật Alert threshold</label>{invalid ? <p role="alert" className="text-sm text-destructive">Min không được lớn hơn Max.</p> : null}<div className="flex flex-wrap gap-2">{canSave ? <Button size="sm" onClick={() => save.mutate()} disabled={invalid || save.isPending}><Save />{config ? "Cập nhật" : "Tạo cấu hình"}</Button> : null}{config && canDelete ? <Button size="sm" variant="outline" onClick={() => remove.mutate()} disabled={remove.isPending}><Trash2 />Xoá</Button> : null}</div>{save.isError || remove.isError ? <p role="alert" className="text-sm text-destructive">{errorMessage(save.error ?? remove.error)}</p> : null}</>}</CardContent></Card>
}
