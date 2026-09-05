import { useState } from "react"
import { useMutation, useQueryClient } from "@tanstack/react-query"
import { Pencil } from "lucide-react"
import { toast } from "sonner"
import { deviceTemplateApi } from "@/entities/device-template/api/device-template-api"
import type { TemplateSensor } from "@/entities/device-template/model/types"
import { invalidateQueries } from "@/shared/api/query-invalidation"
import { Button } from "@/shared/ui/button"
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle, DialogTrigger } from "@/shared/ui/dialog"
import { Input } from "@/shared/ui/input"
import { Label } from "@/shared/ui/label"
import { Switch } from "@/shared/ui/switch"
import { Textarea } from "@/shared/ui/textarea"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/shared/ui/select"

export function EditTemplateSensorDialog({ templateId, sensor, requiredLocked }: { templateId: number; sensor: TemplateSensor; requiredLocked: boolean }) {
  const [open, setOpen] = useState(false)
  const [name, setName] = useState(sensor.display_name ?? "")
  const [location, setLocation] = useState(sensor.default_location ?? "")
  const [lower, setLower] = useState(sensor.default_lower_threshold?.toString() ?? "")
  const [upper, setUpper] = useState(sensor.default_upper_threshold?.toString() ?? "")
  const [required, setRequired] = useState(sensor.is_required)
  const [belowMessage, setBelowMessage] = useState(sensor.default_below_threshold_message ?? "")
  const [aboveMessage, setAboveMessage] = useState(sensor.default_above_threshold_message ?? "")
  const [risk, setRisk] = useState(sensor.default_alert_risk_level ?? "DEFAULT")
  const [alertsEnabled, setAlertsEnabled] = useState(sensor.default_warning_enabled ?? true)
  const client = useQueryClient()
  const mutation = useMutation({
    mutationFn: () => deviceTemplateApi.updateSensor(templateId, sensor.id, {
      display_name: name || undefined,
      default_location: location || undefined,
      default_lower_threshold: lower === "" ? null : Number(lower),
      default_upper_threshold: upper === "" ? null : Number(upper),
      default_below_threshold_message: belowMessage.trim() || null,
      default_above_threshold_message: aboveMessage.trim() || null,
      default_alert_risk_level: risk === "DEFAULT" ? null : risk as Exclude<typeof sensor.default_alert_risk_level, null>,
      default_warning_enabled: alertsEnabled,
      is_required: requiredLocked ? true : required,
    }),
    onSuccess: async () => { await invalidateQueries.deviceTemplates(client); setOpen(false); toast.success("Đã cập nhật cấu hình cảm biến") },
    onError: () => toast.error("Không thể cập nhật cấu hình cảm biến"),
  })
  return <Dialog open={open} onOpenChange={setOpen}>
    <DialogTrigger asChild><Button variant="ghost" size="icon" aria-label={`Sửa ${sensor.model_name}`}><Pencil /></Button></DialogTrigger>
    <DialogContent><DialogHeader><DialogTitle>Sửa cấu hình cảm biến</DialogTitle><DialogDescription>{sensor.model_name} · {sensor.model_code} · {sensor.unit} · {sensor.measurement_semantics}</DialogDescription></DialogHeader>
      <form className="flex flex-col gap-4" onSubmit={(event) => { event.preventDefault(); mutation.mutate() }}>
        <div className="flex flex-col gap-2"><Label htmlFor={`mapping-name-${sensor.id}`}>Tên hiển thị</Label><Input id={`mapping-name-${sensor.id}`} value={name} disabled={requiredLocked} onChange={(event) => setName(event.target.value)} />{requiredLocked ? <p className="text-xs text-muted-foreground">Tên và thứ tự của phép đo chuẩn Energy Monitor được khóa theo giao thức.</p> : null}</div>
        <div className="flex flex-col gap-2"><Label htmlFor={`mapping-location-${sensor.id}`}>Vị trí mặc định</Label><Input id={`mapping-location-${sensor.id}`} value={location} onChange={(event) => setLocation(event.target.value)} /></div>
        <div className="grid gap-4 sm:grid-cols-2"><div className="flex flex-col gap-2"><Label htmlFor={`mapping-lower-${sensor.id}`}>Ngưỡng dưới</Label><Input id={`mapping-lower-${sensor.id}`} type="number" step="any" value={lower} onChange={(event) => setLower(event.target.value)} /></div><div className="flex flex-col gap-2"><Label htmlFor={`mapping-upper-${sensor.id}`}>Ngưỡng trên</Label><Input id={`mapping-upper-${sensor.id}`} type="number" step="any" value={upper} onChange={(event) => setUpper(event.target.value)} /></div></div>
        <div className="flex items-center justify-between gap-3"><div><Label htmlFor={`mapping-alerts-enabled-${sensor.id}`}>Bật cảnh báo mặc định</Label><p className="text-xs text-muted-foreground">Áp dụng khi Sensor mới được provision từ mẫu này.</p></div><Switch id={`mapping-alerts-enabled-${sensor.id}`} checked={alertsEnabled} onCheckedChange={setAlertsEnabled} /></div>
        <div className="flex flex-col gap-2"><Label htmlFor={`mapping-below-message-${sensor.id}`}>Nội dung khi thấp hơn ngưỡng</Label><Textarea id={`mapping-below-message-${sensor.id}`} value={belowMessage} onChange={(event) => setBelowMessage(event.target.value)} placeholder="Để trống để dùng câu mặc định" /></div>
        <div className="flex flex-col gap-2"><Label htmlFor={`mapping-above-message-${sensor.id}`}>Nội dung khi cao hơn ngưỡng</Label><Textarea id={`mapping-above-message-${sensor.id}`} value={aboveMessage} onChange={(event) => setAboveMessage(event.target.value)} placeholder="Để trống để dùng câu mặc định" /></div>
        <div className="flex flex-col gap-2"><Label htmlFor={`mapping-risk-${sensor.id}`}>Mức rủi ro mặc định</Label><Select value={risk} onValueChange={setRisk}><SelectTrigger id={`mapping-risk-${sensor.id}`}><SelectValue /></SelectTrigger><SelectContent><SelectItem value="DEFAULT">Theo Sensor Model</SelectItem><SelectItem value="EXTREME">Cực cao</SelectItem><SelectItem value="VERY_HIGH">Rất cao</SelectItem><SelectItem value="HIGH">Cao</SelectItem><SelectItem value="MEDIUM">Trung bình</SelectItem><SelectItem value="LOW_MEDIUM">Thấp – trung bình</SelectItem><SelectItem value="LOW">Thấp</SelectItem></SelectContent></Select></div>
        <div className="flex items-center justify-between gap-3"><div><Label htmlFor={`mapping-required-${sensor.id}`}>Bắt buộc</Label>{requiredLocked ? <p className="text-xs text-muted-foreground">Phép đo chuẩn Energy Monitor luôn bắt buộc.</p> : null}</div><Switch id={`mapping-required-${sensor.id}`} checked={requiredLocked ? true : required} disabled={requiredLocked} onCheckedChange={setRequired} /></div>
        <DialogFooter><Button type="button" variant="outline" onClick={() => setOpen(false)}>Hủy</Button><Button type="submit" disabled={mutation.isPending}>{mutation.isPending ? "Đang lưu…" : "Lưu"}</Button></DialogFooter>
      </form>
    </DialogContent>
  </Dialog>
}
