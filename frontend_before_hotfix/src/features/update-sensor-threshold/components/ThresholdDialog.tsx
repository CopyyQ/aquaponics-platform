import { useState } from "react"
import { useForm } from "react-hook-form"
import { zodResolver } from "@hookform/resolvers/zod"
import { z } from "zod"
import { useMutation, useQueryClient } from "@tanstack/react-query"
import { SlidersHorizontal } from "lucide-react"
import { toast } from "sonner"
import type { Sensor } from "@/entities/sensor/model/types"
import { sensorApi } from "@/entities/sensor/api/sensor-api"
import { useProtectedQueryScope } from "@/features/auth/model/use-protected-query-scope"
import { invalidateQueries } from "@/shared/api/query-invalidation"
import { Button } from "@/shared/ui/button"
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle, DialogTrigger } from "@/shared/ui/dialog"
import { Input } from "@/shared/ui/input"
import { Label } from "@/shared/ui/label"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/shared/ui/select"
import { Switch } from "@/shared/ui/switch"
import { Textarea } from "@/shared/ui/textarea"

const risks = ["EXTREME", "VERY_HIGH", "HIGH", "MEDIUM", "LOW_MEDIUM", "LOW"] as const
const labels: Record<(typeof risks)[number], string> = { EXTREME: "Cực cao", VERY_HIGH: "Rất cao", HIGH: "Cao", MEDIUM: "Trung bình", LOW_MEDIUM: "Thấp – trung bình", LOW: "Thấp" }
const schema = z.object({ warning_enabled: z.boolean(), lower_threshold: z.number().nullable(), upper_threshold: z.number().nullable(), alert_delay_seconds: z.number().int().min(0).max(86400), below_threshold_message: z.string().nullable(), above_threshold_message: z.string().nullable(), alert_risk_level: z.enum(risks).nullable() }).refine((v) => v.lower_threshold === null || v.upper_threshold === null || v.lower_threshold < v.upper_threshold, { message: "Ngưỡng dưới phải nhỏ hơn ngưỡng trên", path: ["upper_threshold"] })
type Values = z.infer<typeof schema>

export function ThresholdDialog({ sensor }: { sensor: Sensor }) {
  const [open, setOpen] = useState(false)
  const client = useQueryClient()
  const { queryScope } = useProtectedQueryScope()
  const form = useForm<Values>({ resolver: zodResolver(schema), defaultValues: { warning_enabled: sensor.warning_enabled, lower_threshold: sensor.lower_threshold, upper_threshold: sensor.upper_threshold, alert_delay_seconds: sensor.alert_delay_seconds, below_threshold_message: sensor.below_threshold_message, above_threshold_message: sensor.above_threshold_message, alert_risk_level: sensor.alert_risk_level } })
  const mutation = useMutation({ mutationFn: (values: Values) => sensorApi.updateThresholds(sensor.id, values), retry: false, onSuccess: async () => { await invalidateQueries.sensors(client, queryScope, undefined, sensor.device_id, sensor.id); setOpen(false); toast.success("Đã cập nhật giám sát ngưỡng") }, onError: () => toast.error("Không thể lưu cấu hình ngưỡng") })
  const fieldId = (field: string) => `${field}-${sensor.id}`
  return <Dialog open={open} onOpenChange={setOpen}><DialogTrigger asChild><Button><SlidersHorizontal /> Chỉnh ngưỡng</Button></DialogTrigger><DialogContent><DialogHeader><DialogTitle>Giám sát ngưỡng · {sensor.name}</DialogTitle><DialogDescription>Ngưỡng, mức rủi ro và nội dung cảnh báo của cảm biến được lưu cùng một nơi.</DialogDescription></DialogHeader><form className="space-y-5" onSubmit={form.handleSubmit((values) => mutation.mutate(values))}><div className="flex items-center justify-between rounded-lg border p-4"><div><div className="font-medium">Bật cảnh báo</div><div className="text-sm text-muted-foreground">Chỉ đánh giá dữ liệu mới và hợp lệ.</div></div><Switch aria-label="Bật cảnh báo ngưỡng" checked={form.watch("warning_enabled")} onCheckedChange={(checked) => form.setValue("warning_enabled", checked)} /></div><div className="grid gap-4 sm:grid-cols-2"><div className="space-y-2"><Label htmlFor={fieldId("lower")}>Ngưỡng dưới</Label><Input id={fieldId("lower")} type="number" step="any" {...form.register("lower_threshold", { setValueAs: (value) => value === "" ? null : Number(value) })} /></div><div className="space-y-2"><Label htmlFor={fieldId("upper")}>Ngưỡng trên</Label><Input id={fieldId("upper")} type="number" step="any" aria-invalid={Boolean(form.formState.errors.upper_threshold)} aria-describedby={form.formState.errors.upper_threshold ? fieldId("upper-error") : undefined} {...form.register("upper_threshold", { setValueAs: (value) => value === "" ? null : Number(value) })} />{form.formState.errors.upper_threshold && <p id={fieldId("upper-error")} className="text-xs text-destructive" aria-live="polite">{form.formState.errors.upper_threshold.message}</p>}</div></div><div className="space-y-2"><Label htmlFor={fieldId("below-message")}>Khi thấp hơn ngưỡng</Label><Textarea id={fieldId("below-message")} placeholder={`${sensor.name} thấp hơn ngưỡng cho phép`} {...form.register("below_threshold_message", { setValueAs: (value) => value.trim() || null })} /></div><div className="space-y-2"><Label htmlFor={fieldId("above-message")}>Khi cao hơn ngưỡng</Label><Textarea id={fieldId("above-message")} placeholder={`${sensor.name} cao hơn ngưỡng cho phép`} {...form.register("above_threshold_message", { setValueAs: (value) => value.trim() || null })} /></div><div className="grid gap-4 sm:grid-cols-2"><div className="space-y-2"><Label htmlFor={fieldId("risk")}>Mức rủi ro</Label><Select value={form.watch("alert_risk_level") ?? "DEFAULT"} onValueChange={(value) => form.setValue("alert_risk_level", value === "DEFAULT" ? null : value as Values["alert_risk_level"])}><SelectTrigger id={fieldId("risk")}><SelectValue /></SelectTrigger><SelectContent><SelectItem value="DEFAULT">Theo mẫu cảm biến</SelectItem>{risks.map((risk) => <SelectItem key={risk} value={risk}>{labels[risk]}</SelectItem>)}</SelectContent></Select></div><div className="space-y-2"><Label htmlFor={fieldId("delay")}>Thời gian trì hoãn (giây)</Label><Input id={fieldId("delay")} type="number" min="0" {...form.register("alert_delay_seconds", { valueAsNumber: true })} /></div></div><DialogFooter><Button type="button" variant="outline" onClick={() => setOpen(false)}>Hủy</Button><Button type="submit" disabled={mutation.isPending}>{mutation.isPending ? "Đang lưu…" : "Lưu giám sát"}</Button></DialogFooter></form></DialogContent></Dialog>
}
