import { useState } from "react"
import { useMutation, useQueryClient } from "@tanstack/react-query"
import { toast } from "sonner"
import { sensorApi } from "@/entities/sensor/api/sensor-api"
import type { Sensor } from "@/entities/sensor/model/types"
import { useProtectedQueryScope } from "@/features/auth/model/use-protected-query-scope"
import { invalidateQueries } from "@/shared/api/query-invalidation"
import { Button } from "@/shared/ui/button"
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle, DialogTrigger } from "@/shared/ui/dialog"
import { Input } from "@/shared/ui/input"
import { Label } from "@/shared/ui/label"
import { Textarea } from "@/shared/ui/textarea"

export function EditSensorDialog({ sensor, projectId }: { sensor: Sensor; projectId: number }) {
  const [open, setOpen] = useState(false)
  const [name, setName] = useState(sensor.name)
  const [location, setLocation] = useState(sensor.installation_location ?? "")
  const [description, setDescription] = useState(sensor.description ?? "")
  const [lower, setLower] = useState(sensor.lower_threshold?.toString() ?? "")
  const [upper, setUpper] = useState(sensor.upper_threshold?.toString() ?? "")
  const client = useQueryClient()
  const { queryScope } = useProtectedQueryScope()
  const mutation = useMutation({
    mutationFn: () => sensorApi.updateInProject(projectId, sensor.device_id, sensor.id, {
      name, installation_location: location, description,
      lower_threshold: lower === "" ? null : Number(lower),
      upper_threshold: upper === "" ? null : Number(upper),
    }),
    onSuccess: async () => {
      await invalidateQueries.sensors(client, queryScope, projectId, sensor.device_id, sensor.id)
      setOpen(false)
      toast.success("Đã cập nhật cảm biến")
    },
    onError: () => toast.error("Không thể cập nhật cảm biến"),
  })
  const invalid = lower !== "" && upper !== "" && (!Number.isFinite(Number(lower)) || !Number.isFinite(Number(upper)) || Number(lower) >= Number(upper))
  return <Dialog open={open} onOpenChange={setOpen}><DialogTrigger asChild><Button variant="outline" size="sm">Sửa</Button></DialogTrigger><DialogContent><DialogHeader><DialogTitle>Sửa cảm biến</DialogTitle><DialogDescription>Mã cảm biến và Device được giữ nguyên để bảo toàn lịch sử telemetry.</DialogDescription></DialogHeader><div className="flex flex-col gap-4"><div className="flex flex-col gap-2"><Label htmlFor={`sensor-name-${sensor.id}`}>Tên hiển thị</Label><Input id={`sensor-name-${sensor.id}`} value={name} onChange={(event) => setName(event.target.value)} /></div><div className="grid gap-4 sm:grid-cols-2"><div className="flex flex-col gap-2"><Label htmlFor={`sensor-lower-${sensor.id}`}>Ngưỡng dưới</Label><Input id={`sensor-lower-${sensor.id}`} type="number" value={lower} onChange={(event) => setLower(event.target.value)} /></div><div className="flex flex-col gap-2"><Label htmlFor={`sensor-upper-${sensor.id}`}>Ngưỡng trên</Label><Input id={`sensor-upper-${sensor.id}`} type="number" value={upper} onChange={(event) => setUpper(event.target.value)} /></div></div>{invalid ? <p className="text-sm text-destructive">Ngưỡng dưới phải nhỏ hơn ngưỡng trên và là số hữu hạn.</p> : null}<div className="flex flex-col gap-2"><Label htmlFor={`sensor-location-${sensor.id}`}>Vị trí lắp đặt</Label><Input id={`sensor-location-${sensor.id}`} value={location} onChange={(event) => setLocation(event.target.value)} /></div><div className="flex flex-col gap-2"><Label htmlFor={`sensor-description-${sensor.id}`}>Ghi chú</Label><Textarea id={`sensor-description-${sensor.id}`} value={description} onChange={(event) => setDescription(event.target.value)} /></div></div><DialogFooter><Button variant="outline" onClick={() => setOpen(false)}>Hủy</Button><Button disabled={!name.trim() || invalid || mutation.isPending} onClick={() => mutation.mutate()}>{mutation.isPending ? "Đang lưu…" : "Lưu thay đổi"}</Button></DialogFooter></DialogContent></Dialog>
}
