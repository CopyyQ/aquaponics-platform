import { useEffect, useState } from "react"
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { toast } from "sonner"

import { actuatorApi } from "@/entities/actuator/api/actuator-api"
import type { Actuator, ActuatorFeedbackRole } from "@/entities/actuator/model/types"
import { formatBackendError } from "@/shared/api/backend-error"
import { invalidateQueries } from "@/shared/api/query-invalidation"
import { Button } from "@/shared/ui/button"
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/shared/ui/dialog"
import { Input } from "@/shared/ui/input"
import { Label } from "@/shared/ui/label"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/shared/ui/select"

const roleMeta = {
  SUPPLY_VOLTAGE: { label: "Điện áp", unit: "V", key: "voltage_v" },
  RUNNING_CURRENT: { label: "Dòng điện", unit: "A", key: "current_a" },
} as const

export function ActuatorFeedbackDialog({ actuator, projectId, open, onOpenChange }: { actuator: Actuator; projectId: number; open: boolean; onOpenChange: (open: boolean) => void }) {
  return <Dialog open={open} onOpenChange={onOpenChange}>
    <DialogContent className="max-h-[90vh] overflow-y-auto sm:max-w-2xl">
      <DialogHeader><DialogTitle>Sửa cơ cấu chấp hành</DialogTitle><DialogDescription>Cập nhật nguồn cảm biến và ngưỡng cảnh báo điện cho cơ cấu chấp hành vật lý.</DialogDescription></DialogHeader>
      <section className="grid gap-3 rounded-lg bg-muted/40 p-4" aria-labelledby={`actuator-information-${actuator.id}`}>
        <h3 id={`actuator-information-${actuator.id}`} className="font-medium">Thông tin cơ cấu chấp hành</h3>
        <dl className="grid gap-2 text-sm sm:grid-cols-2"><div><dt className="text-muted-foreground">Tên</dt><dd className="font-medium">{actuator.name}</dd></div><div><dt className="text-muted-foreground">Mã</dt><dd className="break-all font-mono">{actuator.code}</dd></div><div><dt className="text-muted-foreground">Mẫu</dt><dd>{actuator.actuator_model?.name ?? "Chưa gắn mẫu"}</dd></div><div><dt className="text-muted-foreground">Vị trí</dt><dd>{actuator.location ?? "Chưa cấu hình"}</dd></div><div><dt className="text-muted-foreground">Trạng thái</dt><dd>{actuator.is_enabled ? "Đang sử dụng" : "Đã vô hiệu hóa"}</dd></div></dl>
      </section>
      <h3 className="font-medium">Giám sát điện</h3>
      <div className="grid gap-4">
        <RoleBindingEditor role="SUPPLY_VOLTAGE" actuator={actuator} projectId={projectId} enabled={open} />
        <RoleBindingEditor role="RUNNING_CURRENT" actuator={actuator} projectId={projectId} enabled={open} />
      </div>
      <DialogFooter><Button type="button" variant="outline" onClick={() => onOpenChange(false)}>Đóng</Button></DialogFooter>
    </DialogContent>
  </Dialog>
}

function RoleBindingEditor({ role, actuator, projectId, enabled }: { role: ActuatorFeedbackRole; actuator: Actuator; projectId: number; enabled: boolean }) {
  const meta = roleMeta[role]
  const client = useQueryClient()
  const [sensorId, setSensorId] = useState("")
  const [valueKey, setValueKey] = useState<string>(meta.key)
  const [lower, setLower] = useState("")
  const [upper, setUpper] = useState("")
  const binding = useQuery({ queryKey: ["actuator-feedback-binding", projectId, actuator.device_id, actuator.id, role], queryFn: () => actuatorApi.getFeedbackBinding(projectId, actuator.device_id, actuator.id, role), enabled })
  const sensors = useQuery({ queryKey: ["actuator-feedback-sensors", projectId, actuator.device_id, actuator.id, role], queryFn: () => actuatorApi.listFeedbackSensors(projectId, actuator.device_id, actuator.id, role), enabled })
  useEffect(() => {
    if (binding.data) {
      setSensorId(String(binding.data.sensor_id)); setValueKey(binding.data.value_key)
      setLower(binding.data.lower_threshold === null ? "" : String(binding.data.lower_threshold))
      setUpper(binding.data.upper_threshold === null ? "" : String(binding.data.upper_threshold))
    } else if (binding.isFetched) {
      setSensorId(""); setValueKey(meta.key); setLower(""); setUpper("")
    }
  }, [binding.data, binding.isFetched, meta.key])
  const refresh = async () => {
    await Promise.all([client.invalidateQueries({ queryKey: ["actuator-feedback-binding", projectId, actuator.device_id, actuator.id, role] }), invalidateQueries.devices(client, [], projectId, actuator.device_id)])
  }
  const save = useMutation({ mutationFn: ({ reset = false }: { reset?: boolean } = {}) => actuatorApi.setFeedbackBinding(projectId, actuator.device_id, actuator.id, { sensor_id: Number(sensorId), feedback_role: role, value_key: valueKey.trim(), lower_threshold: reset || lower === "" ? null : Number(lower), upper_threshold: reset || upper === "" ? null : Number(upper) }), onSuccess: async () => { await refresh(); toast.success(`Đã lưu nguồn dữ liệu ${meta.label.toLowerCase()}`) }, onError: error => toast.error(formatBackendError(error, "Không thể lưu nguồn dữ liệu")) })
  const remove = useMutation({ mutationFn: () => actuatorApi.removeFeedbackBinding(projectId, actuator.device_id, actuator.id, role), onSuccess: async () => { await refresh(); toast.success(`Đã gỡ nguồn dữ liệu ${meta.label.toLowerCase()}`) }, onError: error => toast.error(formatBackendError(error, "Không thể gỡ nguồn dữ liệu")) })
  const selected = sensors.data?.find(sensor => sensor.id === Number(sensorId))
  const thresholdsValid = lower === "" || upper === "" || Number(lower) < Number(upper)
  const valid = Boolean(sensorId && /^[a-z][a-z0-9_]{1,79}$/.test(valueKey.trim()) && thresholdsValid)
  const prefix = `feedback-${actuator.id}-${role.toLowerCase()}`
  const defaultThreshold = binding.data?.default_lower_threshold === null && binding.data?.default_upper_threshold === null ? "Chưa cấu hình" : `${binding.data?.default_lower_threshold ?? "—"}–${binding.data?.default_upper_threshold ?? "—"} ${meta.unit}`
  const sourceLabel = binding.data?.threshold_source === "ACTUATOR_OVERRIDE" ? "Tùy chỉnh cho cơ cấu chấp hành" : binding.data?.threshold_source === "MODEL_DEFAULT" ? "Mặc định từ mẫu" : "Chưa cấu hình"
  return <fieldset className="grid gap-4 rounded-lg border p-4" aria-busy={binding.isLoading || sensors.isLoading || save.isPending}>
    <legend className="px-1 font-medium">{meta.label}</legend>
    <div className="grid gap-2"><Label htmlFor={`${prefix}-source`}>Nguồn dữ liệu *</Label><Select value={sensorId} onValueChange={setSensorId}><SelectTrigger id={`${prefix}-source`}><SelectValue placeholder={`Chọn cảm biến ${meta.unit}`} /></SelectTrigger><SelectContent>{sensors.data?.map(sensor => <SelectItem key={sensor.id} value={String(sensor.id)}>{sensor.name} · {sensor.device_name} · {sensor.sensor_model_code}</SelectItem>)}</SelectContent></Select>{!sensors.isLoading && !sensors.data?.length ? <p className="text-sm text-muted-foreground">Dự án chưa có cảm biến số thực dạng số đo tức thời, đơn vị {meta.unit}.</p> : null}</div>
    <div className="grid gap-2"><Label htmlFor={`${prefix}-key`}>Giá trị dữ liệu *</Label><Input id={`${prefix}-key`} value={valueKey} onChange={event => setValueKey(event.target.value)} pattern="[a-z][a-z0-9_]*" aria-describedby={`${prefix}-hint`} /><p id={`${prefix}-hint`} className="text-xs text-muted-foreground">Khóa dữ liệu mà firmware gửi lên, ví dụ: {meta.key}. Dữ liệu MQTT vẫn dùng mã cảm biến và giá trị đo theo cấu trúc chuẩn.</p></div>
    {binding.data ? <div className="rounded-md bg-muted/50 p-3 text-sm"><p>Ngưỡng mặc định: <span className="font-medium">{defaultThreshold}</span></p><p className="text-muted-foreground">Nguồn ngưỡng hiện tại: {sourceLabel}</p></div> : null}
    <div className="grid gap-4 sm:grid-cols-3"><div className="grid gap-2"><Label htmlFor={`${prefix}-unit`}>Đơn vị</Label><Input id={`${prefix}-unit`} value={selected?.unit ?? binding.data?.unit ?? meta.unit} disabled /></div><div className="grid gap-2"><Label htmlFor={`${prefix}-lower`}>Ngưỡng dưới</Label><Input id={`${prefix}-lower`} type="number" step="any" value={lower} placeholder={binding.data?.default_lower_threshold === null || binding.data?.default_lower_threshold === undefined ? "Không đặt" : `Mặc định ${binding.data.default_lower_threshold}`} onChange={event => setLower(event.target.value)} aria-invalid={!thresholdsValid} aria-describedby={!thresholdsValid ? `${prefix}-threshold-error` : undefined} /></div><div className="grid gap-2"><Label htmlFor={`${prefix}-upper`}>Ngưỡng trên</Label><Input id={`${prefix}-upper`} type="number" step="any" value={upper} placeholder={binding.data?.default_upper_threshold === null || binding.data?.default_upper_threshold === undefined ? "Không đặt" : `Mặc định ${binding.data.default_upper_threshold}`} onChange={event => setUpper(event.target.value)} aria-invalid={!thresholdsValid} aria-describedby={!thresholdsValid ? `${prefix}-threshold-error` : undefined} /></div></div>
    {!thresholdsValid ? <p id={`${prefix}-threshold-error`} role="alert" className="text-sm text-destructive">Ngưỡng dưới phải nhỏ hơn ngưỡng trên.</p> : null}
    <div className="flex flex-wrap justify-end gap-2">{binding.data ? <Button type="button" variant="ghost" disabled={remove.isPending} onClick={() => remove.mutate()}>Gỡ cấu hình</Button> : null}{binding.data && (binding.data.lower_threshold !== null || binding.data.upper_threshold !== null) ? <Button type="button" variant="outline" disabled={save.isPending} onClick={() => save.mutate({ reset: true })}>Sử dụng ngưỡng mặc định</Button> : null}<Button type="button" disabled={!valid || save.isPending} onClick={() => save.mutate({})}>{save.isPending ? "Đang lưu…" : `Lưu ${meta.label.toLowerCase()}`}</Button></div>
  </fieldset>
}
