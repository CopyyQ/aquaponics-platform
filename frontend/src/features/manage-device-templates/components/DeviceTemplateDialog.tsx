import { useEffect, useState } from "react"
import { useMutation, useQueryClient } from "@tanstack/react-query"
import { Copy, Pencil, Plus } from "lucide-react"
import { toast } from "sonner"
import { deviceTemplateApi } from "@/entities/device-template/api/device-template-api"
import type { DeviceTemplate, DeviceTemplateInput, DeviceTemplateList } from "@/entities/device-template/model/types"
import { invalidateQueries } from "@/shared/api/query-invalidation"
import { queryKeys } from "@/shared/api/query-keys"
import { Button } from "@/shared/ui/button"
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle, DialogTrigger } from "@/shared/ui/dialog"
import { Input } from "@/shared/ui/input"
import { Label } from "@/shared/ui/label"
import { Select, SelectContent, SelectGroup, SelectItem, SelectTrigger, SelectValue } from "@/shared/ui/select"
import { Textarea } from "@/shared/ui/textarea"

export function DeviceTemplateDialog({ template, duplicate = false }: { template?: DeviceTemplate; duplicate?: boolean }) {
  const [open, setOpen] = useState(false)
  const [form, setForm] = useState<DeviceTemplateInput>({ code: "", name: "", description: "", notes: "", device_kind: "GENERIC", is_active: true })
  const client = useQueryClient()
  useEffect(() => {
    if (!open) return
    setForm(template ? { code: duplicate ? `${template.code}-COPY` : template.code, name: duplicate ? `${template.name} (bản sao)` : template.name, description: template.description ?? "", notes: template.notes ?? "", device_kind: template.device_kind, nominal_output_voltage_v: template.nominal_output_voltage_v ?? undefined, is_active: duplicate ? false : template.is_active } : { code: "", name: "", description: "", notes: "", device_kind: "GENERIC", is_active: true })
  }, [open, template, duplicate])
  const mutation = useMutation({
    mutationFn: async () => {
      if (template && !duplicate) return deviceTemplateApi.update(template.id, form)
      if (form.device_kind !== "ENERGY_MONITOR") return deviceTemplateApi.create(form)
      const created = await deviceTemplateApi.create({ ...form, is_active: false })
      const configured = await deviceTemplateApi.addEnergyDefaults(created.id)
      return form.is_active ? deviceTemplateApi.update(configured.id, { is_active: true }) : configured
    },
    onSuccess: async (savedTemplate) => {
      client.setQueriesData<DeviceTemplateList>({ queryKey: queryKeys.deviceTemplates.all }, (current) => {
        if (!current) return current
        const exists = current.items.some((item) => item.id === savedTemplate.id)
        return { ...current, items: exists ? current.items.map((item) => item.id === savedTemplate.id ? savedTemplate : item) : [savedTemplate, ...current.items], total: exists ? current.total : current.total + 1 }
      })
      await invalidateQueries.deviceTemplates(client)
      setOpen(false)
      toast.success(template && !duplicate ? "Đã cập nhật mẫu thiết bị" : "Đã tạo mẫu thiết bị")
    },
    onError: () => toast.error("Không thể lưu mẫu thiết bị"),
  })
  const title = template && !duplicate ? "Sửa mẫu thiết bị" : duplicate ? "Nhân bản mẫu thiết bị" : "Tạo mẫu thiết bị"
  return <Dialog open={open} onOpenChange={setOpen}>
    <DialogTrigger asChild><Button variant={template ? "outline" : "default"} size={template ? "sm" : "default"}>{duplicate ? <Copy data-icon="inline-start" /> : template ? <Pencil data-icon="inline-start" /> : <Plus data-icon="inline-start" />}{title}</Button></DialogTrigger>
    <DialogContent><DialogHeader><DialogTitle>{title}</DialogTitle><DialogDescription>Mẫu chỉ là catalog dùng chung, chưa thuộc dự án và không tạo kết nối MQTT.</DialogDescription></DialogHeader>
      <form className="flex flex-col gap-4" onSubmit={(event) => { event.preventDefault(); mutation.mutate() }}>
        <div className="grid gap-4 sm:grid-cols-2"><div className="flex flex-col gap-2"><Label htmlFor="template-code">Mã mẫu</Label><Input id="template-code" required pattern="[A-Z0-9_-]+" value={form.code} onChange={(event) => setForm({ ...form, code: event.target.value.toUpperCase() })} /></div><div className="flex flex-col gap-2"><Label htmlFor="template-name">Tên mẫu</Label><Input id="template-name" required value={form.name} onChange={(event) => setForm({ ...form, name: event.target.value })} /></div></div>
        <div className="grid gap-4 sm:grid-cols-2">
          <div className="flex flex-col gap-2"><Label>Loại thiết bị</Label><Select value={form.device_kind ?? "GENERIC"} onValueChange={(value) => setForm({ ...form, device_kind: value as "GENERIC" | "ENERGY_MONITOR", nominal_output_voltage_v: value === "ENERGY_MONITOR" ? form.nominal_output_voltage_v ?? 12 : undefined })}><SelectTrigger><SelectValue /></SelectTrigger><SelectContent><SelectGroup><SelectItem value="GENERIC">Thiết bị thông thường</SelectItem><SelectItem value="ENERGY_MONITOR">Thiết bị năng lượng</SelectItem></SelectGroup></SelectContent></Select></div>
          <div className="flex flex-col gap-2"><Label htmlFor="template-voltage">Điện áp đầu ra danh định (V)</Label><Input id="template-voltage" type="number" min="0.01" step="0.01" disabled={form.device_kind !== "ENERGY_MONITOR"} value={form.nominal_output_voltage_v ?? ""} onChange={(event) => setForm({ ...form, nominal_output_voltage_v: event.target.value ? Number(event.target.value) : undefined })} /></div>
        </div>
        <div className="flex flex-col gap-2"><Label>Trạng thái</Label><Select value={form.is_active ? "ACTIVE" : "INACTIVE"} onValueChange={(value) => setForm({ ...form, is_active: value === "ACTIVE" })}><SelectTrigger><SelectValue /></SelectTrigger><SelectContent><SelectGroup><SelectItem value="ACTIVE">Khả dụng</SelectItem><SelectItem value="INACTIVE">Vô hiệu hóa</SelectItem></SelectGroup></SelectContent></Select></div>
        <div className="flex flex-col gap-2"><Label htmlFor="template-description">Mô tả</Label><Textarea id="template-description" value={form.description} onChange={(event) => setForm({ ...form, description: event.target.value })} /></div>
        <div className="flex flex-col gap-2"><Label htmlFor="template-notes">Ghi chú</Label><Textarea id="template-notes" value={form.notes} onChange={(event) => setForm({ ...form, notes: event.target.value })} /></div>
        <DialogFooter><Button type="button" variant="outline" onClick={() => setOpen(false)}>Hủy</Button><Button type="submit" disabled={mutation.isPending}>{mutation.isPending ? "Đang lưu…" : "Lưu mẫu"}</Button></DialogFooter>
      </form>
    </DialogContent>
  </Dialog>
}
