import { useEffect, useState, type ReactNode } from "react"
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { Pencil, Plus, Trash2 } from "lucide-react"
import { toast } from "sonner"

import { actuatorModelApi } from "@/entities/actuator-model/api/actuator-model-api"
import type { ActuatorModel, ActuatorModelFeedbackInput, ActuatorModelInput } from "@/entities/actuator-model/model/types"
import { sensorModelApi } from "@/entities/sensor-model/api/sensor-model-api"
import type { SensorModel } from "@/entities/sensor-model/model/types"
import { formatBackendError } from "@/shared/api/backend-error"
import { queryKeys } from "@/shared/api/query-keys"
import { Button } from "@/shared/ui/button"
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle, DialogTrigger } from "@/shared/ui/dialog"
import { Input } from "@/shared/ui/input"
import { Label } from "@/shared/ui/label"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/shared/ui/select"
import { Switch } from "@/shared/ui/switch"
import { Textarea } from "@/shared/ui/textarea"

type FeedbackDraft = Omit<ActuatorModelFeedbackInput, "sensor_model_id" | "unit"> & { sensor_model_id: number | null; unit: string }
const feedbackLabels = { SUPPLY_VOLTAGE: "Điện áp cấp", RUNNING_CURRENT: "Dòng điện hoạt động" } as const
const defaultKey = { SUPPLY_VOLTAGE: "voltage_v", RUNNING_CURRENT: "current_a" } as const

export function compatibleFeedbackSensorModels(models: SensorModel[], role: keyof typeof feedbackLabels) {
  const unit = role === "SUPPLY_VOLTAGE" ? "V" : "A"
  return models.filter(item => item.is_active && item.unit === unit && item.value_type === "NUMBER" && item.measurement_semantics === "GAUGE")
}

function initialFeedbacks(model?: ActuatorModel): FeedbackDraft[] {
  return (model?.feedbacks ?? []).map(({ feedback_role, sensor_model_id, value_key, unit, data_type, default_lower_threshold, default_upper_threshold, is_required, is_enabled, display_order }) => ({ feedback_role, sensor_model_id, value_key, unit, data_type, default_lower_threshold, default_upper_threshold, is_required, is_enabled, display_order }))
}

function defaultElectricalFeedbacks(models: SensorModel[]): FeedbackDraft[] {
  return (["SUPPLY_VOLTAGE", "RUNNING_CURRENT"] as const).flatMap((role, index) => {
    const sensor = compatibleFeedbackSensorModels(models, role).find(item => item.code === (role === "SUPPLY_VOLTAGE" ? "OUTPUT_VOLTAGE_V" : "LOAD_CURRENT_A"))
    return sensor ? [{ feedback_role: role, sensor_model_id: sensor.id, value_key: defaultKey[role], unit: role === "SUPPLY_VOLTAGE" ? "V" : "A", data_type: "FLOAT", default_lower_threshold: null, default_upper_threshold: null, is_required: true, is_enabled: true, display_order: index }] : []
  })
}

export function ActuatorModelDialog({ model }: { model?: ActuatorModel }) {
  const [open, setOpen] = useState(false)
  const [code, setCode] = useState(model?.code ?? "")
  const [name, setName] = useState(model?.name ?? "")
  const [description, setDescription] = useState(model?.description ?? "")
  const [defaultState, setDefaultState] = useState(model?.default_state ?? false)
  const [active, setActive] = useState(model?.is_active ?? true)
  const [feedbacks, setFeedbacks] = useState<FeedbackDraft[]>(() => initialFeedbacks(model))
  const client = useQueryClient()
  const sensorModels = useQuery({ queryKey: queryKeys.sensorModels.list([]), queryFn: sensorModelApi.list, enabled: open })
  useEffect(() => {
    if (open && !model && feedbacks.length === 0 && sensorModels.data) setFeedbacks(defaultElectricalFeedbacks(sensorModels.data))
  }, [open, model, feedbacks.length, sensorModels.data])

  const updateFeedback = (index: number, patch: Partial<FeedbackDraft>) => setFeedbacks(current => current.map((item, row) => row === index ? { ...item, ...patch } : item))
  const addFeedback = () => {
    const role = feedbacks.some(item => item.feedback_role === "SUPPLY_VOLTAGE") ? "RUNNING_CURRENT" : "SUPPLY_VOLTAGE"
    setFeedbacks(current => [...current, { feedback_role: role, sensor_model_id: null, value_key: defaultKey[role], unit: role === "SUPPLY_VOLTAGE" ? "V" : "A", data_type: "FLOAT", default_lower_threshold: null, default_upper_threshold: null, is_required: true, is_enabled: true, display_order: current.length }])
  }
  const payload = (): ActuatorModelInput => ({
    code: code.trim().toUpperCase(), name: name.trim(), description: description.trim() || undefined,
    data_type: "BOOLEAN", default_state: defaultState, is_active: active,
    feedbacks: feedbacks.map((item, index) => ({ ...item, sensor_model_id: item.sensor_model_id!, display_order: index })),
  })
  const mutation = useMutation({
    mutationFn: () => model ? actuatorModelApi.update(model.id, payload()) : actuatorModelApi.create(payload()),
    onSuccess: async () => { await client.invalidateQueries({ queryKey: queryKeys.actuatorModels.all }); setOpen(false); toast.success(model ? "Đã cập nhật mẫu cơ cấu chấp hành" : "Đã tạo mẫu cơ cấu chấp hành") },
    onError: (error) => toast.error(formatBackendError(error, "Không thể lưu mẫu cơ cấu chấp hành")),
  })
  const rolesUnique = new Set(feedbacks.map(item => item.feedback_role)).size === feedbacks.length
  const feedbacksValid = feedbacks.every(item => item.sensor_model_id && /^[a-z][a-z0-9_]{1,79}$/.test(item.value_key.trim()) && (item.default_lower_threshold === null || item.default_upper_threshold === null || item.default_lower_threshold < item.default_upper_threshold))
  const valid = Boolean(/^[A-Z][A-Z0-9_]{1,79}$/.test(code.trim().toUpperCase()) && name.trim().length >= 2 && rolesUnique && feedbacksValid)
  return <Dialog open={open} onOpenChange={setOpen}>
    <DialogTrigger asChild>{model ? <Button variant="ghost" size="icon" aria-label={`Chỉnh sửa ${model.name}`}><Pencil aria-hidden="true" /></Button> : <Button className="w-full sm:w-auto"><Plus data-icon="inline-start" aria-hidden="true" />Thêm mẫu cơ cấu chấp hành</Button>}</DialogTrigger>
    <DialogContent className="max-h-[90vh] overflow-y-auto sm:max-w-3xl">
      <DialogHeader><DialogTitle>{model ? "Chỉnh sửa mẫu cơ cấu chấp hành" : "Thêm mẫu cơ cấu chấp hành"}</DialogTitle><DialogDescription>Cấu hình khả năng giám sát điện mặc định; số đo thực tế chỉ được tạo khi cơ cấu được lắp vào thiết bị.</DialogDescription></DialogHeader>
      <form className="grid gap-4" aria-busy={mutation.isPending} onSubmit={(event) => { event.preventDefault(); mutation.mutate() }}>
        <div className="grid gap-4 sm:grid-cols-2"><Field label="Mã *" id={`actuator-model-code-${model?.id ?? "new"}`}><Input id={`actuator-model-code-${model?.id ?? "new"}`} required disabled={Boolean(model)} value={code} onChange={(event) => setCode(event.target.value.toUpperCase())} /></Field><Field label="Tên mẫu *" id={`actuator-model-name-${model?.id ?? "new"}`}><Input id={`actuator-model-name-${model?.id ?? "new"}`} required value={name} onChange={(event) => setName(event.target.value)} /></Field></div>
        <Field label="Mô tả" id={`actuator-model-description-${model?.id ?? "new"}`}><Textarea id={`actuator-model-description-${model?.id ?? "new"}`} value={description} onChange={(event) => setDescription(event.target.value)} /></Field>
        <section className="grid gap-3" aria-labelledby={`feedback-title-${model?.id ?? "new"}`}>
          <div className="flex flex-wrap items-center justify-between gap-2"><div><h3 id={`feedback-title-${model?.id ?? "new"}`} className="font-medium">Giám sát điện</h3><p className="text-sm text-muted-foreground">Mặc định mới theo dõi điện áp cấp và dòng điện hoạt động.</p></div><Button type="button" variant="outline" size="sm" disabled={feedbacks.length >= 2} onClick={addFeedback}><Plus aria-hidden="true" />Thêm khả năng giám sát</Button></div>
          {!feedbacks.length ? <p className="rounded-lg border border-dashed p-4 text-sm text-muted-foreground">Không hỗ trợ giám sát điện cho mẫu này.</p> : null}
          {feedbacks.map((feedback, index) => {
            const unit = feedback.feedback_role === "SUPPLY_VOLTAGE" ? "V" : "A"
            const compatible = compatibleFeedbackSensorModels(sensorModels.data ?? [], feedback.feedback_role)
            const prefix = `model-feedback-${model?.id ?? "new"}-${index}`
            return <fieldset key={`${feedback.feedback_role}-${index}`} className="grid gap-4 rounded-lg border p-4 sm:grid-cols-2">
              <legend className="px-1 font-medium">{feedbackLabels[feedback.feedback_role]}</legend>
              <Field label="Loại phản hồi *" id={`${prefix}-role`}><Select value={feedback.feedback_role} onValueChange={(value: keyof typeof feedbackLabels) => updateFeedback(index, { feedback_role: value, sensor_model_id: null, value_key: defaultKey[value], unit: value === "SUPPLY_VOLTAGE" ? "V" : "A" })}><SelectTrigger id={`${prefix}-role`}><SelectValue /></SelectTrigger><SelectContent>{Object.entries(feedbackLabels).map(([value, label]) => <SelectItem key={value} value={value} disabled={feedbacks.some((item, row) => row !== index && item.feedback_role === value)}>{label}</SelectItem>)}</SelectContent></Select></Field>
              <Field label="Mẫu cảm biến *" id={`${prefix}-sensor`}><Select value={feedback.sensor_model_id ? String(feedback.sensor_model_id) : ""} onValueChange={(value) => updateFeedback(index, { sensor_model_id: Number(value), unit })}><SelectTrigger id={`${prefix}-sensor`}><SelectValue placeholder={`Chọn mẫu cảm biến ${unit}`} /></SelectTrigger><SelectContent>{compatible.map(item => <SelectItem key={item.id} value={String(item.id)}>{item.name} · {item.code}</SelectItem>)}</SelectContent></Select></Field>
              <Field label="Giá trị dữ liệu *" id={`${prefix}-key`}><Input id={`${prefix}-key`} required value={feedback.value_key} onChange={(event) => updateFeedback(index, { value_key: event.target.value })} pattern="[a-z][a-z0-9_]*" aria-describedby={`${prefix}-key-hint`} /><p id={`${prefix}-key-hint`} className="text-xs text-muted-foreground">Khóa dữ liệu mà firmware gửi lên, ví dụ: {defaultKey[feedback.feedback_role]}.</p></Field>
              <Field label="Đơn vị *" id={`${prefix}-unit`}><Input id={`${prefix}-unit`} value={unit} disabled /></Field><Field label="Kiểu dữ liệu *" id={`${prefix}-type`}><Input id={`${prefix}-type`} value="Số thực" disabled /></Field>
              <ThresholdField id={`${prefix}-lower`} label={`Ngưỡng dưới (${unit})`} value={feedback.default_lower_threshold} onChange={value => updateFeedback(index, { default_lower_threshold: value })} />
              <ThresholdField id={`${prefix}-upper`} label={`Ngưỡng trên (${unit})`} value={feedback.default_upper_threshold} onChange={value => updateFeedback(index, { default_upper_threshold: value })} />
              <Setting label="Bắt buộc" description={feedback.is_required ? "Phải được provision" : "Không bắt buộc"} checked={feedback.is_required} onChange={checked => updateFeedback(index, { is_required: checked })} />
              <Setting label="Trạng thái" description={feedback.is_enabled ? "Đang sử dụng" : "Đã vô hiệu hóa"} checked={feedback.is_enabled} onChange={checked => updateFeedback(index, { is_enabled: checked })} />
              <div className="flex justify-end sm:col-span-2"><Button type="button" variant="ghost" size="sm" onClick={() => setFeedbacks(current => current.filter((_, row) => row !== index))}><Trash2 aria-hidden="true" />Xóa dữ liệu phản hồi</Button></div>
            </fieldset>
          })}
        </section>
        <div className="grid gap-3 sm:grid-cols-2"><Setting label="Trạng thái mặc định" description={defaultState ? "Bật" : "Tắt"} checked={defaultState} onChange={setDefaultState} /><Setting label="Trạng thái danh mục" description={active ? "Đang sử dụng" : "Đã vô hiệu hóa"} checked={active} onChange={setActive} /></div>
        {!rolesUnique ? <p role="alert" className="text-sm text-destructive">Mỗi loại phản hồi chỉ được cấu hình một lần.</p> : null}
        <DialogFooter><Button type="button" variant="outline" onClick={() => setOpen(false)}>Hủy</Button><Button type="submit" disabled={!valid || mutation.isPending}>{mutation.isPending ? "Đang lưu…" : "Lưu"}</Button></DialogFooter>
      </form>
    </DialogContent>
  </Dialog>
}

function Field({ label, id, children }: { label: string; id?: string; children: ReactNode }) { return <div className="grid gap-2"><Label htmlFor={id}>{label}</Label>{children}</div> }
function ThresholdField({ id, label, value, onChange }: { id: string; label: string; value: number | null; onChange: (value: number | null) => void }) { return <Field label={label} id={id}><Input id={id} type="number" step="any" value={value ?? ""} placeholder="Chưa cấu hình" onChange={event => onChange(event.target.value === "" ? null : Number(event.target.value))} /></Field> }
function Setting({ label, description, checked, onChange }: { label: string; description: string; checked: boolean; onChange: (checked: boolean) => void }) { return <div className="flex items-center justify-between gap-4 rounded-lg border p-3"><div><p className="font-medium">{label}</p><p className="text-xs text-muted-foreground">{description}</p></div><Switch checked={checked} onCheckedChange={onChange} aria-label={label} /></div> }
