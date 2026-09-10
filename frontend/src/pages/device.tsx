import { useState, type FormEvent } from "react"
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { Link, useParams } from "react-router-dom"
import { createActuator, createCommand, createSensor, getDevice, listActuatorModels, listSensorModels } from "@/api/resources"
import { errorMessage } from "@/api/client"
import { useAuth } from "@/app/auth"

export function DevicePage() {
  const params = useParams(); const systemId = params.systemId ?? ""; const deviceId = params.deviceId ?? ""; const queryClient = useQueryClient(); const { has } = useAuth()
  const device = useQuery({ queryKey: ["device", systemId, deviceId], queryFn: () => getDevice(systemId, deviceId), enabled: Boolean(systemId && deviceId) })
  const sensorModels = useQuery({ queryKey: ["sensor-models"], queryFn: listSensorModels, enabled: has("sensors.create") })
  const actuatorModels = useQuery({ queryKey: ["actuator-models"], queryFn: listActuatorModels, enabled: has("actuators.create") })
  const [sensor, setSensor] = useState({ code: "", name: "", model: "" }); const [actuator, setActuator] = useState({ code: "", name: "", model: "" })
  const refresh = async () => queryClient.invalidateQueries({ queryKey: ["device", systemId, deviceId] })
  const addSensor = useMutation({ mutationFn: () => createSensor(systemId, deviceId, { sensor_model_id: Number(sensor.model), code: sensor.code.trim().toUpperCase(), name: sensor.name.trim() }), onSuccess: refresh })
  const addActuator = useMutation({ mutationFn: () => createActuator(systemId, deviceId, { actuator_model_id: Number(actuator.model), code: actuator.code.trim().toUpperCase(), name: actuator.name.trim() }), onSuccess: refresh })
  const command = useMutation({ mutationFn: ({ id, state }: { id: string; state: boolean }) => createCommand(systemId, deviceId, id, { desired_state: state }), onSuccess: refresh })
  if (device.isLoading) return <p>Đang tải…</p>
  if (!device.data) return <p className="text-destructive">{errorMessage(device.error)}</p>
  return <section className="space-y-6"><div><Link className="text-sm text-primary" to={`/aquaponics-systems/${systemId}`}>← Hệ thống Aquaponics</Link><h1 className="text-3xl font-bold">{device.data.name}</h1><p className="text-muted-foreground">{device.data.code} · {device.data.status}</p></div><div className="grid gap-6 lg:grid-cols-2"><ResourceSection title="Sensors" form={has("sensors.create") ? <CreateForm kind="Sensor" values={sensor} setValues={setSensor} models={sensorModels.data || []} onSubmit={(event) => { event.preventDefault(); addSensor.mutate() }} /> : null}>{device.data.sensors.map((item) => <article className="rounded border p-3" key={item.id}><strong>{item.name}</strong><p className="text-sm text-muted-foreground">{item.code} · Model #{item.sensor_model_id}</p></article>)}</ResourceSection><ResourceSection title="Actuators" form={has("actuators.create") ? <CreateForm kind="Actuator" values={actuator} setValues={setActuator} models={actuatorModels.data || []} onSubmit={(event) => { event.preventDefault(); addActuator.mutate() }} /> : null}>{device.data.actuators.map((item) => <article className="rounded border p-3" key={item.id}><div className="flex justify-between"><div><strong>{item.name}</strong><p className="text-sm text-muted-foreground">{item.code} · Yêu cầu: {stateText(item.desired_state)} · Báo về: {stateText(item.reported_state)}</p><p className="text-sm">{item.voltage_v ?? "—"} V · {item.current_a ?? "—"} A</p></div>{has("actuators.commands.create") && <div className="flex gap-1"><button className="rounded border px-2" onClick={() => command.mutate({ id: item.id, state: true })}>Bật</button><button className="rounded border px-2" onClick={() => command.mutate({ id: item.id, state: false })}>Tắt</button></div>}</div></article>)}</ResourceSection></div></section>
}

function stateText(value: boolean | null) { return value === null ? "—" : value ? "Bật" : "Tắt" }

function ResourceSection({ title, form, children }: { title: string; form: React.ReactNode; children: React.ReactNode }) {
  return <section className="space-y-3 rounded-xl border bg-card p-4"><h2 className="text-xl font-semibold">{title}</h2>{form}{children}</section>
}

function CreateForm({ kind, values, setValues, models, onSubmit }: { kind: string; values: { code: string; name: string; model: string }; setValues: (value: { code: string; name: string; model: string }) => void; models: { id: number; name: string }[]; onSubmit: (event: FormEvent) => void }) {
  return <form className="grid gap-2 rounded bg-muted p-3" onSubmit={onSubmit}><input className="rounded border bg-background p-2" placeholder={`Mã ${kind}`} value={values.code} onChange={(event) => setValues({ ...values, code: event.target.value })} required /><input className="rounded border bg-background p-2" placeholder={`Tên ${kind}`} value={values.name} onChange={(event) => setValues({ ...values, name: event.target.value })} required /><select className="rounded border bg-background p-2" value={values.model} onChange={(event) => setValues({ ...values, model: event.target.value })} required><option value="">Chọn model</option>{models.map((model) => <option key={model.id} value={model.id}>{model.name}</option>)}</select><button className="rounded bg-primary p-2 text-primary-foreground">Thêm {kind}</button></form>
}
