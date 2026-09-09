import { useQuery } from "@tanstack/react-query"
import { Link, useParams } from "react-router-dom"
import { listDevices, queryKeys } from "@/api/resources"
import { EmptyState } from "@/shared/ui/empty-state"
import { Skeleton } from "@/shared/ui/skeleton"
import { StatusBadge } from "@/shared/ui/status-badge"
import { Card, CardContent } from "@/shared/ui/card"
import { Wrench } from "lucide-react"
import { errorMessage } from "@/api/client"

export function DevicesPage() {
  const systemId = Number(useParams().systemId)
  const devices = useQuery({ queryKey: queryKeys.devices(systemId), queryFn: () => listDevices(systemId) })
  if (devices.isLoading) return <Skeleton className="h-96" />
  if (devices.isError) return <EmptyState icon={Wrench} title="Không thể tải thiết bị" description={errorMessage(devices.error)} />
  return <div className="space-y-5"><div><h2 className="text-xl font-semibold">Thiết bị runtime</h2><p className="text-sm text-muted-foreground">Mỗi Device có thể chứa đồng thời Sensor và Actuator.</p></div>{devices.data?.length ? <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">{devices.data.map((device) => <Link key={device.id} to={`/aquaponics-systems/${systemId}/devices/${device.id}`}><Card className="h-full transition-colors hover:border-primary"><CardContent className="p-5"><div className="flex items-start justify-between gap-3"><div><p className="font-semibold">{device.name}</p><p className="text-sm text-muted-foreground">{device.code}</p></div><StatusBadge value={device.status} /></div><div className="mt-5 grid grid-cols-2 gap-3 text-sm"><div className="rounded-lg bg-muted/60 p-3"><p className="text-xs text-muted-foreground">Sensor</p><p className="mt-1 text-lg font-semibold">{device.sensors.length}</p></div><div className="rounded-lg bg-muted/60 p-3"><p className="text-xs text-muted-foreground">Actuator</p><p className="mt-1 text-lg font-semibold">{device.actuators.length}</p></div></div><p className="mt-4 text-xs text-muted-foreground">{device.location ?? "Chưa đặt vị trí"}</p></CardContent></Card></Link>)}</div> : <EmptyState icon={Wrench} title="Chưa có thiết bị" description="Thiết bị được tạo trong phạm vi hệ thống Aquaponics." />}</div>
}
