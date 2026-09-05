import { useState } from "react"
import { useMutation, useQueryClient } from "@tanstack/react-query"
import { toast } from "sonner"
import { deviceApi } from "@/entities/device/api/device-api"
import type { Device } from "@/entities/device/model/types"
import { useProtectedQueryScope } from "@/features/auth/model/use-protected-query-scope"
import { invalidateQueries } from "@/shared/api/query-invalidation"
import { Button } from "@/shared/ui/button"
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle, DialogTrigger } from "@/shared/ui/dialog"
import { Input } from "@/shared/ui/input"
import { Label } from "@/shared/ui/label"
import { Textarea } from "@/shared/ui/textarea"

export function EditDeviceDialog({ device, projectId }: { device: Device; projectId: number }) {
  const [open, setOpen] = useState(false)
  const [name, setName] = useState(device.name)
  const [location, setLocation] = useState(device.location ?? "")
  const [description, setDescription] = useState(device.description ?? "")
  const client = useQueryClient()
  const { queryScope } = useProtectedQueryScope()
  const mutation = useMutation({
    mutationFn: () => deviceApi.updateInProject(projectId, device.id, { name, location, description }),
    onSuccess: async (updated) => {
      client.setQueryData(["device", ...queryScope, projectId, device.id], (current: unknown) =>
        current && typeof current === "object" && "device" in current ? { ...(current as { device: Device }), device: updated } : current,
      )
      await invalidateQueries.devices(client, queryScope, projectId, device.id)
      setOpen(false)
      toast.success("Đã cập nhật Device")
    },
    onError: () => toast.error("Không thể cập nhật Device"),
  })
  return <Dialog open={open} onOpenChange={setOpen}><DialogTrigger asChild><Button variant="outline" size="sm">Sửa</Button></DialogTrigger><DialogContent><DialogHeader><DialogTitle>Sửa Device</DialogTitle><DialogDescription>Mã kỹ thuật và Project không thể sửa sau khi phát sinh dữ liệu.</DialogDescription></DialogHeader><div className="flex flex-col gap-4"><div className="flex flex-col gap-2"><Label htmlFor={`device-name-${device.id}`}>Tên Device</Label><Input id={`device-name-${device.id}`} value={name} onChange={(event) => setName(event.target.value)} /></div><div className="flex flex-col gap-2"><Label htmlFor={`device-location-${device.id}`}>Vị trí lắp đặt</Label><Input id={`device-location-${device.id}`} value={location} onChange={(event) => setLocation(event.target.value)} /></div><div className="flex flex-col gap-2"><Label htmlFor={`device-description-${device.id}`}>Ghi chú</Label><Textarea id={`device-description-${device.id}`} value={description} onChange={(event) => setDescription(event.target.value)} /></div></div><DialogFooter><Button variant="outline" onClick={() => setOpen(false)}>Hủy</Button><Button disabled={!name.trim() || mutation.isPending} onClick={() => mutation.mutate()}>{mutation.isPending ? "Đang lưu…" : "Lưu thay đổi"}</Button></DialogFooter></DialogContent></Dialog>
}
