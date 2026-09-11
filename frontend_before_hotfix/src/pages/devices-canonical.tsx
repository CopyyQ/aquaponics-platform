import { useMemo, useState } from "react"
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { Plus, Search, Wrench } from "lucide-react"
import { Link, useParams } from "react-router-dom"
import { createDevice, listDevices, listDeviceTemplates, queryKeys } from "@/api/resources"
import type { DeviceInput } from "@/api/contracts"
import { errorMessage } from "@/api/client"
import { useAuth } from "@/app/auth"
import { Button } from "@/shared/ui/button"
import { Card, CardContent } from "@/shared/ui/card"
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle, DialogTrigger } from "@/shared/ui/dialog"
import { EmptyState } from "@/shared/ui/empty-state"
import { Input } from "@/shared/ui/input"
import { Label } from "@/shared/ui/label"
import { Skeleton } from "@/shared/ui/skeleton"
import { StatusBadge } from "@/shared/ui/status-badge"
import { Textarea } from "@/shared/ui/textarea"

const initialDraft: DeviceInput = { code: "", name: "", description: null, location: null, device_template_id: null }

export function DevicesPage() {
  const systemId = useParams().systemId ?? ""
  const validId = Boolean(systemId)
  const { can } = useAuth()
  const client = useQueryClient()
  const [queryText, setQueryText] = useState("")
  const [status, setStatus] = useState("ALL")
  const [dialogOpen, setDialogOpen] = useState(false)
  const [draft, setDraft] = useState<DeviceInput>(initialDraft)
  const devices = useQuery({ queryKey: queryKeys.devices(systemId), queryFn: () => listDevices(systemId), enabled: validId })
  const templates = useQuery({ queryKey: queryKeys.templates, queryFn: listDeviceTemplates, enabled: dialogOpen })
  const creation = useMutation({
    mutationFn: () => createDevice(systemId, { ...draft, code: draft.code.trim().toUpperCase(), name: draft.name.trim(), description: draft.description?.trim() || null, location: draft.location?.trim() || null }),
    onSuccess: async () => { await client.invalidateQueries({ queryKey: queryKeys.devices(systemId) }); setDraft(initialDraft); setDialogOpen(false) },
  })
  const filtered = useMemo(() => (devices.data ?? []).filter((device) => {
    const matchesText = `${device.name} ${device.code} ${device.location ?? ""}`.toLocaleLowerCase("vi").includes(queryText.toLocaleLowerCase("vi"))
    return matchesText && (status === "ALL" || device.status === status)
  }), [devices.data, queryText, status])

  if (!validId) return <EmptyState icon={Wrench} title="Đường dẫn hệ thống không hợp lệ" description="System ID phải là số nguyên dương." />
  if (devices.isLoading) return <Skeleton className="h-96" />
  if (devices.isError) return <EmptyState icon={Wrench} title="Không thể tải thiết bị" description={errorMessage(devices.error)} />

  return <div className="space-y-5">
    <div className="flex flex-wrap items-start justify-between gap-3"><div><h2 className="text-xl font-semibold">Thiết bị runtime</h2><p className="text-sm text-muted-foreground">Mỗi Device có thể chứa đồng thời Sensor và Actuator.</p></div>{can("devices.create") ? <Dialog open={dialogOpen} onOpenChange={setDialogOpen}><DialogTrigger asChild><Button><Plus />Thêm Device</Button></DialogTrigger><DialogContent><DialogHeader><DialogTitle>Tạo Device</DialogTitle><DialogDescription>Khởi tạo Device trong phạm vi hệ thống hiện tại, có thể từ một DeviceTemplate.</DialogDescription></DialogHeader><form className="space-y-4" onSubmit={(event) => { event.preventDefault(); creation.mutate() }}><div className="grid gap-4 sm:grid-cols-2"><TextField id="device-code" label="Mã Device" value={draft.code} onChange={(code) => setDraft((current) => ({ ...current, code }))} /><TextField id="device-name" label="Tên Device" value={draft.name} onChange={(name) => setDraft((current) => ({ ...current, name }))} /><div className="sm:col-span-2"><Label htmlFor="device-template">DeviceTemplate</Label><select id="device-template" className="mt-1 h-9 w-full rounded-md border bg-background px-3 text-sm" value={draft.device_template_id ?? ""} onChange={(event) => setDraft((current) => ({ ...current, device_template_id: event.target.value ? Number(event.target.value) : null }))}><option value="">Không dùng template</option>{templates.data?.filter((template) => template.is_active).map((template) => <option key={template.id} value={template.id}>{template.name} · {template.code}</option>)}</select></div><TextField id="device-location" label="Vị trí" required={false} value={draft.location ?? ""} onChange={(location) => setDraft((current) => ({ ...current, location }))} /><div><Label htmlFor="device-description">Mô tả</Label><Textarea id="device-description" className="mt-1" value={draft.description ?? ""} onChange={(event) => setDraft((current) => ({ ...current, description: event.target.value }))} /></div></div>{creation.isError ? <p role="alert" className="text-sm text-destructive">{errorMessage(creation.error)}</p> : null}<DialogFooter><Button type="button" variant="outline" onClick={() => setDialogOpen(false)}>Huỷ</Button><Button type="submit" disabled={creation.isPending}>Tạo Device</Button></DialogFooter></form></DialogContent></Dialog> : null}</div>
    <div className="grid gap-3 rounded-xl border bg-card p-4 sm:grid-cols-[minmax(0,1fr)_12rem]"><label className="relative"><span className="sr-only">Tìm Device</span><Search className="absolute left-3 top-2.5 size-4 text-muted-foreground" /><Input className="pl-9" placeholder="Tìm theo tên, mã hoặc vị trí" value={queryText} onChange={(event) => setQueryText(event.target.value)} /></label><select aria-label="Lọc trạng thái Device" className="h-9 rounded-md border bg-background px-3 text-sm" value={status} onChange={(event) => setStatus(event.target.value)}><option value="ALL">Tất cả trạng thái</option><option value="ONLINE">Online</option><option value="OFFLINE">Offline</option><option value="WAITING_CONNECTION">Chờ kết nối</option><option value="DISABLED">Vô hiệu</option></select></div>
    {filtered.length ? <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">{filtered.map((device) => <Link key={device.id} to={`/aquaponics-systems/${systemId}/devices/${device.id}`}><Card className="h-full transition-colors hover:border-primary"><CardContent className="p-5"><div className="flex items-start justify-between gap-3"><div><p className="font-semibold">{device.name}</p><p className="text-sm text-muted-foreground">{device.code}</p></div><StatusBadge value={device.status} /></div><div className="mt-5 grid grid-cols-2 gap-3 text-sm"><div className="rounded-lg bg-muted/60 p-3"><p className="text-xs text-muted-foreground">Sensor</p><p className="mt-1 text-lg font-semibold">{device.sensors.length}</p></div><div className="rounded-lg bg-muted/60 p-3"><p className="text-xs text-muted-foreground">Actuator</p><p className="mt-1 text-lg font-semibold">{device.actuators.length}</p></div></div><p className="mt-4 text-xs text-muted-foreground">{device.location ?? "Chưa đặt vị trí"}</p></CardContent></Card></Link>)}</div> : <EmptyState icon={Wrench} title={devices.data?.length ? "Không tìm thấy Device" : "Chưa có thiết bị"} description={devices.data?.length ? "Thử thay đổi bộ lọc hoặc từ khoá." : "Tạo Device trong phạm vi hệ thống Aquaponics."} />}
  </div>
}

function TextField({ id, label, value, onChange, required = true }: { id: string; label: string; value: string; onChange: (value: string) => void; required?: boolean }) { return <div><Label htmlFor={id}>{label}</Label><Input id={id} className="mt-1" value={value} onChange={(event) => onChange(event.target.value)} required={required} /></div> }
