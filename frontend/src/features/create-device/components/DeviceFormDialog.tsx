import { useMemo, useState } from "react"
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { Boxes, Plus, Search } from "lucide-react"
import { toast } from "sonner"
import { projectApi } from "@/entities/project/api/project-api"
import type { ProjectDeviceList } from "@/entities/project/model/types"
import { useProtectedQueryScope } from "@/features/auth/model/use-protected-query-scope"
import { invalidateQueries } from "@/shared/api/query-invalidation"
import { queryKeys } from "@/shared/api/query-keys"
import { deviceTemplateApi } from "@/entities/device-template/api/device-template-api"
import { Button } from "@/shared/ui/button"
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle, DialogTrigger } from "@/shared/ui/dialog"
import { EmptyState } from "@/shared/ui/empty-state"
import { Input } from "@/shared/ui/input"
import { Label } from "@/shared/ui/label"
import { Select, SelectContent, SelectGroup, SelectItem, SelectTrigger, SelectValue } from "@/shared/ui/select"
import { Skeleton } from "@/shared/ui/skeleton"

export function DeviceFormDialog({ projectId, projectName }: { projectId: number; projectName: string }) {
  const [open, setOpen] = useState(false)
  const [templateId, setTemplateId] = useState("")
  const [search, setSearch] = useState("")
  const [details, setDetails] = useState({ code: "", name: "", location: "", description: "" })
  const client = useQueryClient()
  const { queryScope } = useProtectedQueryScope()
  const templates = useQuery({ queryKey: queryKeys.deviceTemplates.list(...queryScope, "", "ACTIVE", 1), queryFn: () => deviceTemplateApi.list("", "ACTIVE"), enabled: open })
  const options = useMemo(() => {
    const keyword = search.trim().toLocaleLowerCase("vi")
    return (templates.data?.items ?? []).filter((item) => !keyword || `${item.code} ${item.name}`.toLocaleLowerCase("vi").includes(keyword))
  }, [search, templates.data])
  const mutation = useMutation({
    mutationFn: () => projectApi.createDeviceFromTemplate(projectId, Number(templateId), {
      code: details.code.trim() || undefined,
      name: details.name.trim() || undefined,
      location: details.location.trim() || undefined,
      description: details.description.trim() || undefined,
    }),
    onSuccess: async (device) => {
      client.setQueryData<ProjectDeviceList>(queryKeys.projects.devices(queryScope, projectId), (current) => current ? { ...current, items: [device, ...current.items.filter((item) => item.id !== device.id)], total: current.items.some((item) => item.id === device.id) ? current.total : current.total + 1 } : current)
      await invalidateQueries.devices(client, queryScope, projectId, device.id)
      setTemplateId("")
      setSearch("")
      setDetails({ code: "", name: "", location: "", description: "" })
      setOpen(false)
      toast.success(`Đã thêm ${device.name} vào dự án`)
    },
    onError: () => toast.error("Không thể thêm thiết bị từ mẫu đã chọn"),
  })
  return <Dialog open={open} onOpenChange={setOpen}>
    <DialogTrigger asChild><Button><Plus data-icon="inline-start" />Thêm thiết bị</Button></DialogTrigger>
    <DialogContent>
      <DialogHeader><DialogTitle>Thêm thiết bị vào dự án</DialogTitle><DialogDescription>Chọn một mẫu đang khả dụng cho dự án “{projectName}”. Mã thiết bị và cảm biến được Backend tự sinh.</DialogDescription></DialogHeader>
      <form className="flex flex-col gap-4" onSubmit={(event) => { event.preventDefault(); if (templateId) mutation.mutate() }}>
        <div className="flex flex-col gap-2"><Label htmlFor="device-template-search">Tìm mẫu thiết bị</Label><div className="relative"><Search className="pointer-events-none absolute left-3 top-2.5 text-muted-foreground" /><Input id="device-template-search" className="pl-9" value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Nhập mã hoặc tên mẫu" /></div></div>
        {templates.isLoading ? <Skeleton className="h-10" /> : templates.isError ? <EmptyState icon={Boxes} title="Không thể tải danh sách mẫu thiết bị" description="Vui lòng thử lại." action={<Button type="button" variant="outline" onClick={() => void templates.refetch()}>Thử lại</Button>} /> : options.length ? <div className="flex flex-col gap-2"><Label>Chọn mẫu thiết bị</Label><Select value={templateId} onValueChange={setTemplateId}><SelectTrigger aria-invalid={!templateId}><SelectValue placeholder="Chọn một mẫu" /></SelectTrigger><SelectContent><SelectGroup>{options.map((template) => <SelectItem key={template.id} value={String(template.id)}>{template.code} · {template.name} ({template.sensors.length} cảm biến · {template.actuators.length} cơ cấu)</SelectItem>)}</SelectGroup></SelectContent></Select></div> : <EmptyState icon={Boxes} title="Không có mẫu phù hợp" description="Không có mẫu đang hoạt động khớp từ khóa." />}
        <div className="grid gap-4 sm:grid-cols-2"><div className="flex flex-col gap-2"><Label htmlFor="device-code">Mã thiết bị</Label><Input id="device-code" pattern="[A-Z0-9_-]+" value={details.code} onChange={(event) => setDetails({ ...details, code: event.target.value.toUpperCase() })} placeholder="Để trống để Backend tự sinh" /></div><div className="flex flex-col gap-2"><Label htmlFor="device-name">Tên thiết bị</Label><Input id="device-name" value={details.name} onChange={(event) => setDetails({ ...details, name: event.target.value })} placeholder="Mặc định theo tên mẫu" /></div></div>
        <div className="grid gap-4 sm:grid-cols-2"><div className="flex flex-col gap-2"><Label htmlFor="device-location">Vị trí</Label><Input id="device-location" value={details.location} onChange={(event) => setDetails({ ...details, location: event.target.value })} /></div><div className="flex flex-col gap-2"><Label htmlFor="device-description">Mô tả</Label><Input id="device-description" value={details.description} onChange={(event) => setDetails({ ...details, description: event.target.value })} /></div></div>
        <DialogFooter><Button type="button" variant="outline" onClick={() => setOpen(false)}>Hủy</Button><Button type="submit" disabled={!templateId || mutation.isPending}>{mutation.isPending ? "Đang thêm…" : "Thêm thiết bị"}</Button></DialogFooter>
      </form>
    </DialogContent>
  </Dialog>
}
