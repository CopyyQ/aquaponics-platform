import { useMemo, useState } from "react"
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { Plus } from "lucide-react"
import { toast } from "sonner"
import { sensorModelApi } from "@/entities/sensor-model/api/sensor-model-api"
import { deviceTemplateApi } from "@/entities/device-template/api/device-template-api"
import { invalidateQueries } from "@/shared/api/query-invalidation"
import { queryKeys } from "@/shared/api/query-keys"
import { Button } from "@/shared/ui/button"
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle, DialogTrigger } from "@/shared/ui/dialog"
import { Input } from "@/shared/ui/input"
import { Label } from "@/shared/ui/label"
import { Select, SelectContent, SelectGroup, SelectItem, SelectTrigger, SelectValue } from "@/shared/ui/select"
import { Switch } from "@/shared/ui/switch"
import { Textarea } from "@/shared/ui/textarea"
import { formatBackendError } from "@/shared/api/backend-error"

type Props = {
  templateId: number
  nextOrder: number
  mappedModelIds: number[]
}

export function AddTemplateSensorDialog({ templateId, nextOrder, mappedModelIds }: Props) {
  const [open, setOpen] = useState(false)
  const [search, setSearch] = useState("")
  const [modelId, setModelId] = useState("")
  const [required, setRequired] = useState(false)
  const [order, setOrder] = useState(nextOrder + 1)
  const [lower, setLower] = useState("")
  const [upper, setUpper] = useState("")
  const [alertsEnabled, setAlertsEnabled] = useState(true)
  const [belowMessage, setBelowMessage] = useState("")
  const [aboveMessage, setAboveMessage] = useState("")
  const models = useQuery({ queryKey: queryKeys.sensorModels.list([]), queryFn: sensorModelApi.list, enabled: open })
  const client = useQueryClient()
  const available = useMemo(() => {
    const term = search.trim().toLocaleLowerCase("vi")
    return (models.data ?? []).filter((model) => model.is_active && !mappedModelIds.includes(model.id) && (!term || `${model.name} ${model.code} ${model.unit}`.toLocaleLowerCase("vi").includes(term)))
  }, [mappedModelIds, models.data, search])
  const invalidThresholds = lower !== "" && upper !== "" && (!Number.isFinite(Number(lower)) || !Number.isFinite(Number(upper)) || Number(lower) >= Number(upper))
  const mutation = useMutation({
    mutationFn: () => deviceTemplateApi.addSensor(templateId, {
      sensor_model_id: Number(modelId), sort_order: Math.max(0, order), is_required: required,
      default_lower_threshold: lower === "" ? null : Number(lower),
      default_upper_threshold: upper === "" ? null : Number(upper),
      default_warning_enabled: alertsEnabled,
      default_below_threshold_message: belowMessage.trim() || null,
      default_above_threshold_message: aboveMessage.trim() || null,
    }),
    onSuccess: async () => {
      await invalidateQueries.deviceTemplates(client)
      setSearch(""); setModelId(""); setRequired(false); setOrder(nextOrder + 1); setLower(""); setUpper(""); setAlertsEnabled(true); setBelowMessage(""); setAboveMessage(""); setOpen(false)
      toast.success("Đã thêm cảm biến vào mẫu")
    },
    onError: (error) => toast.error(formatBackendError(error, "Không thể thêm cảm biến vào mẫu")),
  })
  return <Dialog open={open} onOpenChange={setOpen}>
    <DialogTrigger asChild><Button variant="outline" size="sm" data-testid="add-template-sensor"><Plus data-icon="inline-start" />Thêm cảm biến</Button></DialogTrigger>
    <DialogContent>
      <DialogHeader><DialogTitle>Thêm cảm biến vào mẫu</DialogTitle><DialogDescription>Chọn Sensor Model từ catalog backend. Thao tác không thay đổi Sensor đã materialize.</DialogDescription></DialogHeader>
      <form className="flex flex-col gap-4" onSubmit={(event) => { event.preventDefault(); mutation.mutate() }}>
        <div className="flex flex-col gap-2"><Label htmlFor={`sensor-search-${templateId}`}>Tìm Sensor Model</Label><Input id={`sensor-search-${templateId}`} value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Tên, code hoặc đơn vị" /></div>
        <div className="flex flex-col gap-2"><Label>Sensor Model *</Label><Select value={modelId} onValueChange={setModelId} required><SelectTrigger aria-label="Sensor Model"><SelectValue placeholder={models.isLoading ? "Đang tải…" : "Chọn Sensor Model"} /></SelectTrigger><SelectContent><SelectGroup>{available.map((model) => <SelectItem key={model.id} value={String(model.id)}><span className="flex flex-col"><span>{model.name} · {model.code}</span><span className="text-xs text-muted-foreground">{model.unit} · {model.value_type} · {model.measurement_semantics}</span></span></SelectItem>)}</SelectGroup></SelectContent></Select>{!models.isLoading && available.length === 0 ? <p className="text-sm text-muted-foreground">Không còn Sensor Model phù hợp để thêm.</p> : null}</div>
        <div className="flex items-center justify-between gap-3"><Label htmlFor={`required-${templateId}`}>Bắt buộc</Label><Switch id={`required-${templateId}`} checked={required} onCheckedChange={setRequired} /></div>
        <div className="flex flex-col gap-2"><Label htmlFor={`order-${templateId}`}>Thứ tự hiển thị</Label><Input id={`order-${templateId}`} type="number" min="0" value={order} onChange={(event) => setOrder(Number(event.target.value))} /></div>
        <fieldset className="flex flex-col gap-4 rounded-md border p-4"><legend className="px-1 text-sm font-medium">Giám sát ngưỡng mặc định</legend><div className="flex items-center justify-between gap-3"><div><Label htmlFor={`alerts-enabled-${templateId}`}>Bật cảnh báo</Label><p className="text-xs text-muted-foreground">Áp dụng cho Sensor mới được provision từ mẫu này.</p></div><Switch id={`alerts-enabled-${templateId}`} checked={alertsEnabled} onCheckedChange={setAlertsEnabled} /></div><div className="grid gap-4 sm:grid-cols-2"><div className="flex flex-col gap-2"><Label htmlFor={`lower-${templateId}`}>Ngưỡng dưới</Label><Input id={`lower-${templateId}`} type="number" step="any" value={lower} onChange={(event) => setLower(event.target.value)} /></div><div className="flex flex-col gap-2"><Label htmlFor={`upper-${templateId}`}>Ngưỡng trên</Label><Input id={`upper-${templateId}`} type="number" step="any" aria-invalid={invalidThresholds} aria-describedby={invalidThresholds ? `threshold-error-${templateId}` : undefined} value={upper} onChange={(event) => setUpper(event.target.value)} /></div></div>{invalidThresholds ? <p id={`threshold-error-${templateId}`} className="text-sm text-destructive" aria-live="polite">Ngưỡng dưới phải nhỏ hơn ngưỡng trên.</p> : null}<div className="flex flex-col gap-2"><Label htmlFor={`below-message-${templateId}`}>Nội dung khi thấp hơn ngưỡng</Label><Textarea id={`below-message-${templateId}`} value={belowMessage} onChange={(event) => setBelowMessage(event.target.value)} /></div><div className="flex flex-col gap-2"><Label htmlFor={`above-message-${templateId}`}>Nội dung khi cao hơn ngưỡng</Label><Textarea id={`above-message-${templateId}`} value={aboveMessage} onChange={(event) => setAboveMessage(event.target.value)} /></div></fieldset>
        <DialogFooter><Button type="button" variant="outline" onClick={() => setOpen(false)}>Hủy</Button><Button type="submit" disabled={!modelId || invalidThresholds || mutation.isPending}>{mutation.isPending ? "Đang lưu…" : "Lưu"}</Button></DialogFooter>
      </form>
    </DialogContent>
  </Dialog>
}
