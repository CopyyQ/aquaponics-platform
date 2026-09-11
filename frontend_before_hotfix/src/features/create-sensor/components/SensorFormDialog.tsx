import { useMemo, useState } from "react"
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { Plus, RadioTower, Search } from "lucide-react"
import { toast } from "sonner"
import { sensorApi } from "@/entities/sensor/api/sensor-api"
import { sensorModelApi } from "@/entities/sensor-model/api/sensor-model-api"
import { useProtectedQueryScope } from "@/features/auth/model/use-protected-query-scope"
import { getAvailableSensorModels } from "@/features/create-sensor/model/get-available-sensor-models"
import { invalidateQueries } from "@/shared/api/query-invalidation"
import { queryKeys } from "@/shared/api/query-keys"
import { Button } from "@/shared/ui/button"
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle, DialogTrigger } from "@/shared/ui/dialog"
import { EmptyState } from "@/shared/ui/empty-state"
import { Input } from "@/shared/ui/input"
import { Label } from "@/shared/ui/label"
import { Select, SelectContent, SelectGroup, SelectItem, SelectTrigger, SelectValue } from "@/shared/ui/select"
import { Skeleton } from "@/shared/ui/skeleton"

export function SensorFormDialog({ deviceId, projectId }: { deviceId: number; projectId?: number }) {
  const [open, setOpen] = useState(false)
  const [modelId, setModelId] = useState("")
  const [search, setSearch] = useState("")
  const queryClient = useQueryClient()
  const { queryScope } = useProtectedQueryScope()
  const models = useQuery({ queryKey: queryKeys.sensorModels.list(queryScope), queryFn: sensorModelApi.list, enabled: open })
  const sensors = useQuery({ queryKey: queryKeys.devices.sensors(queryScope, projectId ?? 0, deviceId), queryFn: () => sensorApi.listByDevice(deviceId, true), enabled: open })
  const existingModelIds = useMemo(() => new Set((sensors.data ?? []).map((sensor) => sensor.sensor_model_id)), [sensors.data])
  const options = useMemo(
    () => getAvailableSensorModels(models.data ?? [], existingModelIds, search),
    [existingModelIds, models.data, search],
  )
  const mutation = useMutation({
    mutationFn: () => sensorApi.createFromModel(deviceId, Number(modelId)),
    onSuccess: async (sensor) => {
      queryClient.setQueryData(queryKeys.sensors.detail(queryScope, projectId ?? 0, deviceId, sensor.id), sensor)
      queryClient.setQueryData<Awaited<ReturnType<typeof sensorApi.listByDevice>>>(queryKeys.devices.sensors(queryScope, projectId ?? 0, deviceId), (current) => current ? [sensor, ...current.filter((item) => item.id !== sensor.id)] : current)
      await invalidateQueries.sensors(queryClient, queryScope, projectId, deviceId, sensor.id)
      setModelId("")
      setSearch("")
      setOpen(false)
      toast.success("Đã thêm cảm biến từ mẫu")
    },
    onError: () => toast.error("Không thể thêm cảm biến từ mẫu đã chọn"),
  })
  return <Dialog open={open} onOpenChange={setOpen}><DialogTrigger asChild><Button><Plus data-icon="inline-start" />Thêm cảm biến</Button></DialogTrigger><DialogContent><DialogHeader><DialogTitle>Thêm cảm biến</DialogTitle><DialogDescription>Chọn mẫu cảm biến đang khả dụng. Backend tự sinh mã và sao chép ngưỡng mặc định.</DialogDescription></DialogHeader><form className="flex flex-col gap-4" onSubmit={(event) => { event.preventDefault(); if (modelId) mutation.mutate() }}><div className="flex flex-col gap-2"><Label htmlFor={`sensor-model-search-${deviceId}`}>Tìm mẫu cảm biến</Label><div className="relative"><Search className="pointer-events-none absolute left-3 top-2.5 text-muted-foreground" /><Input id={`sensor-model-search-${deviceId}`} className="pl-9" value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Nhập mã, tên hoặc đơn vị" /></div></div>{models.isLoading || sensors.isLoading ? <Skeleton className="h-10" /> : models.isError || sensors.isError ? <EmptyState icon={RadioTower} title="Không thể tải mẫu cảm biến" description="Vui lòng thử lại." /> : options.length ? <div className="flex flex-col gap-2"><Label>Chọn mẫu cảm biến</Label><Select value={modelId} onValueChange={setModelId}><SelectTrigger aria-invalid={!modelId}><SelectValue placeholder="Chọn một mẫu" /></SelectTrigger><SelectContent><SelectGroup>{options.map((model) => <SelectItem key={model.id} value={String(model.id)}>{model.code} · {model.name} ({model.unit})</SelectItem>)}</SelectGroup></SelectContent></Select></div> : <EmptyState icon={RadioTower} title="Không còn mẫu khả dụng" description="Thiết bị đã có tất cả mẫu phù hợp hoặc không có kết quả tìm kiếm." />}<DialogFooter><Button type="button" variant="outline" onClick={() => setOpen(false)}>Hủy</Button><Button type="submit" disabled={!modelId || mutation.isPending}>{mutation.isPending ? "Đang thêm…" : "Thêm cảm biến"}</Button></DialogFooter></form></DialogContent></Dialog>
}
