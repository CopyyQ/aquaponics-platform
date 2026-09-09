import { useEffect, useState } from "react"
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { Activity, Cpu, Download, Pencil, Plus, Radio, Save, Trash2 } from "lucide-react"
import { Link, useNavigate, useParams } from "react-router-dom"
import {
  createActuator, createSensor, deleteDevice, exportMqttConfig, getDevice, getMonitoringLatest,
  listActuatorModels, listSensorModels, queryKeys, updateDevice,
} from "@/api/resources"
import type { ActuatorInput, ActuatorModel, DeviceUpdate, SensorInput, SensorModel } from "@/api/contracts"
import { errorMessage } from "@/api/client"
import { useAuth } from "@/app/auth"
import {
  AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription,
  AlertDialogFooter, AlertDialogHeader, AlertDialogTitle, AlertDialogTrigger,
} from "@/shared/ui/alert-dialog"
import { Button } from "@/shared/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/shared/ui/card"
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle, DialogTrigger } from "@/shared/ui/dialog"
import { EmptyState } from "@/shared/ui/empty-state"
import { Input } from "@/shared/ui/input"
import { Label } from "@/shared/ui/label"
import { Skeleton } from "@/shared/ui/skeleton"
import { StatusBadge } from "@/shared/ui/status-badge"
import { Switch } from "@/shared/ui/switch"
import { Textarea } from "@/shared/ui/textarea"

export function DeviceDetailCanonicalPage() {
  const params = useParams()
  const systemId = Number(params.systemId)
  const deviceId = Number(params.deviceId)
  const validIds = systemId > 0 && deviceId > 0
  const { can } = useAuth()
  const client = useQueryClient()
  const navigate = useNavigate()
  const [editing, setEditing] = useState(false)
  const [editDraft, setEditDraft] = useState<DeviceUpdate>({})
  const [sensorOpen, setSensorOpen] = useState(false)
  const [actuatorOpen, setActuatorOpen] = useState(false)

  const device = useQuery({ queryKey: queryKeys.device(systemId, deviceId), queryFn: () => getDevice(systemId, deviceId), enabled: validIds })
  const monitoring = useQuery({ queryKey: queryKeys.monitoringLatest(systemId), queryFn: () => getMonitoringLatest(systemId), enabled: validIds && can("monitoring.read") })
  const sensorModels = useQuery({ queryKey: queryKeys.sensorModels, queryFn: listSensorModels, enabled: sensorOpen })
  const actuatorModels = useQuery({ queryKey: queryKeys.actuatorModels, queryFn: listActuatorModels, enabled: actuatorOpen })
  useEffect(() => {
    if (!device.data) return
    setEditDraft({ code: device.data.code, name: device.data.name, description: device.data.description, location: device.data.location, device_template_id: device.data.device_template_id, is_enabled: device.data.is_enabled })
  }, [device.data])

  const refresh = async () => {
    await Promise.all([
      client.invalidateQueries({ queryKey: queryKeys.device(systemId, deviceId) }),
      client.invalidateQueries({ queryKey: queryKeys.devices(systemId) }),
      client.invalidateQueries({ queryKey: queryKeys.monitoringLatest(systemId) }),
      client.invalidateQueries({ queryKey: queryKeys.scada(systemId) }),
    ])
  }
  const saveDevice = useMutation({ mutationFn: () => updateDevice(systemId, deviceId, editDraft), onSuccess: async () => { await refresh(); setEditing(false) } })
  const removeDevice = useMutation({ mutationFn: () => deleteDevice(systemId, deviceId), onSuccess: async () => { await client.invalidateQueries({ queryKey: queryKeys.devices(systemId) }); navigate(`/aquaponics-systems/${systemId}/devices`) } })
  const sensorCreation = useMutation({ mutationFn: (payload: SensorInput) => createSensor(systemId, deviceId, payload), onSuccess: async () => { await refresh(); setSensorOpen(false) } })
  const actuatorCreation = useMutation({ mutationFn: (payload: ActuatorInput) => createActuator(systemId, deviceId, payload), onSuccess: async () => { await refresh(); setActuatorOpen(false) } })
  const downloadMqtt = async () => {
    const payload = await exportMqttConfig(systemId)
    const url = URL.createObjectURL(new Blob([JSON.stringify(payload, null, 2)], { type: "application/json" }))
    const anchor = document.createElement("a")
    anchor.href = url
    anchor.download = `${payload.aquaponics_system.code}-mqtt-config.json`
    anchor.click()
    URL.revokeObjectURL(url)
  }

  if (!validIds) return <EmptyState icon={Cpu} title="Đường dẫn Device không hợp lệ" description="System và Device ID phải là số nguyên dương." />
  if (device.isLoading) return <div className="space-y-4"><Skeleton className="h-24" /><Skeleton className="h-96" /></div>
  if (device.isError || !device.data) return <EmptyState icon={Cpu} title="Không thể tải thiết bị" description={errorMessage(device.error)} />

  const value = device.data
  const monitored = monitoring.data?.devices.find((item) => item.id === deviceId)
  const measurementCards = monitored?.sensors.filter((sensor) => sensor.latest !== null) ?? []

  return <div className="space-y-6">
    <div className="flex flex-wrap items-start justify-between gap-3"><div><p className="text-sm text-muted-foreground"><Link className="text-primary hover:underline" to={`/aquaponics-systems/${systemId}/devices`}>Thiết bị</Link> / {value.code}</p><h2 className="mt-1 text-2xl font-semibold">{value.name}</h2><p className="mt-1 text-sm text-muted-foreground">{value.description ?? "Không có mô tả"} · {value.location ?? "Chưa đặt vị trí"}</p></div><div className="flex flex-wrap items-center gap-2"><StatusBadge value={value.status} />{can("mqtt_config.export") ? <Button variant="outline" onClick={() => void downloadMqtt()}><Download />MQTT config</Button> : null}{can("devices.update") ? <Button variant="outline" onClick={() => setEditing((current) => !current)}><Pencil />Chỉnh sửa</Button> : null}{can("devices.delete") ? <AlertDialog><AlertDialogTrigger asChild><Button variant="destructive"><Trash2 />Xoá Device</Button></AlertDialogTrigger><AlertDialogContent><AlertDialogHeader><AlertDialogTitle>Xoá {value.name}?</AlertDialogTitle><AlertDialogDescription>Device cùng các runtime resource liên quan sẽ được xử lý theo ràng buộc canonical backend.</AlertDialogDescription></AlertDialogHeader><AlertDialogFooter><AlertDialogCancel>Huỷ</AlertDialogCancel><AlertDialogAction variant="destructive" onClick={() => removeDevice.mutate()}>Xoá</AlertDialogAction></AlertDialogFooter></AlertDialogContent></AlertDialog> : null}</div></div>

    {editing ? <form className="grid gap-4 rounded-xl border bg-card p-5 sm:grid-cols-2" onSubmit={(event) => { event.preventDefault(); saveDevice.mutate() }}><TextField id="edit-device-code" label="Mã Device" value={editDraft.code ?? ""} onChange={(code) => setEditDraft((current) => ({ ...current, code: code.toUpperCase() }))} /><TextField id="edit-device-name" label="Tên Device" value={editDraft.name ?? ""} onChange={(name) => setEditDraft((current) => ({ ...current, name }))} /><TextField id="edit-device-location" label="Vị trí" required={false} value={editDraft.location ?? ""} onChange={(location) => setEditDraft((current) => ({ ...current, location }))} /><div><Label htmlFor="edit-device-description">Mô tả</Label><Textarea id="edit-device-description" className="mt-1" value={editDraft.description ?? ""} onChange={(event) => setEditDraft((current) => ({ ...current, description: event.target.value }))} /></div><label className="flex items-center gap-3 text-sm"><Switch checked={editDraft.is_enabled ?? value.is_enabled} onCheckedChange={(is_enabled) => setEditDraft((current) => ({ ...current, is_enabled }))} />Device hoạt động</label><div className="flex items-center justify-end gap-2"><Button type="button" variant="ghost" onClick={() => setEditing(false)}>Huỷ</Button><Button type="submit" disabled={saveDevice.isPending}><Save />Lưu Device</Button></div>{saveDevice.isError ? <p role="alert" className="text-sm text-destructive sm:col-span-2">{errorMessage(saveDevice.error)}</p> : null}</form> : null}

    <div className="grid gap-4 sm:grid-cols-4"><Info label="Mã Device" value={value.code} /><Info label="Sensor" value={String(value.sensors.length)} /><Info label="Actuator" value={String(value.actuators.length)} /><Info label="Template" value={value.device_template_id ? `#${value.device_template_id}` : "Không dùng"} /></div>

    {measurementCards.length ? <Card><CardHeader><CardTitle>Measurements mới nhất</CardTitle></CardHeader><CardContent className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">{measurementCards.map((sensor) => <Link key={sensor.id} className="rounded-xl border p-4 hover:border-primary" to={`/aquaponics-systems/${systemId}/devices/${deviceId}/sensors/${sensor.id}`}><p className="text-sm text-muted-foreground">{sensor.name}</p><p className="mt-1 text-xl font-semibold">{sensor.latest?.value ?? "—"} {sensor.unit}</p><p className="mt-1 text-xs text-muted-foreground">{sensor.latest?.recorded_at ? new Date(sensor.latest.recorded_at).toLocaleString("vi-VN") : "Chưa có dữ liệu"}</p></Link>)}</CardContent></Card> : null}

    <div className="grid gap-6 xl:grid-cols-2"><ResourceCard title="Sensors" icon={Activity} action={can("sensors.create") ? <Dialog open={sensorOpen} onOpenChange={setSensorOpen}><DialogTrigger asChild><Button size="sm"><Plus />Thêm Sensor</Button></DialogTrigger><DialogContent><DialogHeader><DialogTitle>Tạo Sensor</DialogTitle><DialogDescription>Gắn SensorModel canonical vào Device hiện tại.</DialogDescription></DialogHeader><SensorForm models={sensorModels.data ?? []} pending={sensorCreation.isPending} error={sensorCreation.error} onSubmit={(payload) => sensorCreation.mutate(payload)} /></DialogContent></Dialog> : null}>{value.sensors.length ? value.sensors.map((sensor) => <Link key={sensor.id} className="flex items-center justify-between rounded-xl border p-4 transition-colors hover:border-primary" to={`/aquaponics-systems/${systemId}/devices/${deviceId}/sensors/${sensor.id}`}><div><p className="font-medium">{sensor.name}</p><p className="text-xs text-muted-foreground">{sensor.code} · Model #{sensor.sensor_model_id}</p></div><StatusBadge value={sensor.status} /></Link>) : <EmptyState icon={Activity} title="Chưa có Sensor" description="Tạo Sensor từ một SensorModel đã có." />}</ResourceCard><ResourceCard title="Actuators" icon={Radio} action={can("actuators.create") ? <Dialog open={actuatorOpen} onOpenChange={setActuatorOpen}><DialogTrigger asChild><Button size="sm"><Plus />Thêm Actuator</Button></DialogTrigger><DialogContent><DialogHeader><DialogTitle>Tạo Actuator</DialogTitle><DialogDescription>Gắn ActuatorModel canonical vào Device hiện tại.</DialogDescription></DialogHeader><ActuatorForm models={actuatorModels.data ?? []} pending={actuatorCreation.isPending} error={actuatorCreation.error} onSubmit={(payload) => actuatorCreation.mutate(payload)} /></DialogContent></Dialog> : null}>{value.actuators.length ? value.actuators.map((actuator) => <Link key={actuator.id} className="flex items-center justify-between gap-3 rounded-xl border p-4 transition-colors hover:border-primary" to={`/aquaponics-systems/${systemId}/devices/${deviceId}/actuators/${actuator.id}`}><div><p className="font-medium">{actuator.name}</p><p className="text-xs text-muted-foreground">{actuator.code} · {actuator.actuator_model_id ? `Model #${actuator.actuator_model_id}` : "Chưa có model"}</p></div><div className="text-right"><StatusBadge value={actuator.is_enabled ? "ACTIVE" : "DISABLED"} /><p className="mt-1 text-xs text-muted-foreground">Desired {stateText(actuator.desired_state)} · Reported {stateText(actuator.reported_state)}</p></div></Link>) : <EmptyState icon={Radio} title="Chưa có Actuator" description="Tạo Actuator từ một ActuatorModel đã có." />}</ResourceCard></div>
  </div>
}

function Info({ label, value }: { label: string; value: string }) { return <Card><CardContent className="p-4"><p className="text-xs text-muted-foreground">{label}</p><p className="mt-1 font-semibold">{value}</p></CardContent></Card> }
function ResourceCard({ title, icon: Icon, action, children }: { title: string; icon: typeof Activity; action: React.ReactNode; children: React.ReactNode }) { return <Card><CardHeader className="flex-row items-center justify-between"><CardTitle className="flex items-center gap-2"><Icon className="size-5 text-primary" />{title}</CardTitle>{action}</CardHeader><CardContent className="space-y-3">{children}</CardContent></Card> }
function stateText(value: boolean | null) { return value === null ? "—" : value ? "Bật" : "Tắt" }
function TextField({ id, label, value, onChange, required = true }: { id: string; label: string; value: string; onChange: (value: string) => void; required?: boolean }) { return <div><Label htmlFor={id}>{label}</Label><Input id={id} className="mt-1" value={value} onChange={(event) => onChange(event.target.value)} required={required} /></div> }

function SensorForm({ models, pending, error, onSubmit }: { models: SensorModel[]; pending: boolean; error: Error | null; onSubmit: (payload: SensorInput) => void }) {
  const [draft, setDraft] = useState<SensorInput>({ sensor_model_id: 0, code: "", name: "", installation_location: null, description: null })
  return <form className="space-y-4" onSubmit={(event) => { event.preventDefault(); onSubmit({ ...draft, code: draft.code.trim().toUpperCase(), name: draft.name.trim() }) }}><div className="grid gap-4 sm:grid-cols-2"><TextField id="sensor-code" label="Mã Sensor" value={draft.code} onChange={(code) => setDraft((current) => ({ ...current, code }))} /><TextField id="sensor-name" label="Tên Sensor" value={draft.name} onChange={(name) => setDraft((current) => ({ ...current, name }))} /><div className="sm:col-span-2"><Label htmlFor="sensor-model">SensorModel</Label><select id="sensor-model" className="mt-1 h-9 w-full rounded-md border bg-background px-3 text-sm" value={draft.sensor_model_id || ""} onChange={(event) => setDraft((current) => ({ ...current, sensor_model_id: Number(event.target.value) }))} required><option value="">Chọn model</option>{models.filter((model) => model.is_active).map((model) => <option key={model.id} value={model.id}>{model.name} · {model.unit}</option>)}</select></div><TextField id="sensor-installation" label="Vị trí lắp đặt" required={false} value={draft.installation_location ?? ""} onChange={(installation_location) => setDraft((current) => ({ ...current, installation_location }))} /></div>{error ? <p role="alert" className="text-sm text-destructive">{errorMessage(error)}</p> : null}<DialogFooter><Button type="submit" disabled={pending || draft.sensor_model_id <= 0}>Tạo Sensor</Button></DialogFooter></form>
}

function ActuatorForm({ models, pending, error, onSubmit }: { models: ActuatorModel[]; pending: boolean; error: Error | null; onSubmit: (payload: ActuatorInput) => void }) {
  const [draft, setDraft] = useState<ActuatorInput>({ actuator_model_id: 0, code: "", name: "", location: null, notes: null })
  return <form className="space-y-4" onSubmit={(event) => { event.preventDefault(); onSubmit({ ...draft, code: draft.code.trim().toUpperCase(), name: draft.name.trim() }) }}><div className="grid gap-4 sm:grid-cols-2"><TextField id="actuator-code" label="Mã Actuator" value={draft.code} onChange={(code) => setDraft((current) => ({ ...current, code }))} /><TextField id="actuator-name" label="Tên Actuator" value={draft.name} onChange={(name) => setDraft((current) => ({ ...current, name }))} /><div className="sm:col-span-2"><Label htmlFor="actuator-model">ActuatorModel</Label><select id="actuator-model" className="mt-1 h-9 w-full rounded-md border bg-background px-3 text-sm" value={draft.actuator_model_id || ""} onChange={(event) => setDraft((current) => ({ ...current, actuator_model_id: Number(event.target.value) }))} required><option value="">Chọn model</option>{models.filter((model) => model.is_active).map((model) => <option key={model.id} value={model.id}>{model.name}</option>)}</select></div><TextField id="actuator-location" label="Vị trí" required={false} value={draft.location ?? ""} onChange={(location) => setDraft((current) => ({ ...current, location }))} /></div>{error ? <p role="alert" className="text-sm text-destructive">{errorMessage(error)}</p> : null}<DialogFooter><Button type="submit" disabled={pending || draft.actuator_model_id <= 0}>Tạo Actuator</Button></DialogFooter></form>
}
