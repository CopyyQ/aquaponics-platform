import { Link } from "react-router-dom"
import { ArrowRight, Cpu, MapPin } from "lucide-react"
import type { Device } from "@/entities/device/model/types"
import { formatRelative } from "@/shared/lib/date"
import { Card, CardContent, CardHeader, CardTitle } from "@/shared/ui/card"
import { StatusBadge } from "@/shared/ui/status-badge"
import { Button } from "@/shared/ui/button"

export function DeviceCard({ device, sensorCount, admin = false }: { device: Device; sensorCount?: number; admin?: boolean }) {
  return <Card className="group overflow-hidden transition-all hover:-translate-y-0.5 hover:shadow-lg"><div className="h-1 bg-primary" /><CardHeader className="flex-row items-start justify-between"><div className="flex items-start gap-3"><div className="rounded-xl bg-primary/10 p-3 text-primary"><Cpu className="size-5" /></div><div><CardTitle>{device.name}</CardTitle><p className="mt-1 font-mono text-xs text-muted-foreground">{device.code}</p></div></div><StatusBadge value={device.status} /></CardHeader><CardContent><div className="min-h-10 text-sm text-muted-foreground"><MapPin className="mr-1 inline size-4" />{device.description || "Chưa có mô tả vị trí"}</div><div className="mt-5 flex items-end justify-between border-t pt-4"><div><div className="text-xs text-muted-foreground">Cảm biến</div><div className="text-lg font-semibold">{sensorCount ?? "—"}</div><div className="mt-1 text-xs text-muted-foreground">Hoạt động {formatRelative(device.last_seen_at)}</div></div><Button asChild variant="ghost" size="sm" className="group-hover:bg-primary group-hover:text-primary-foreground"><Link to={`${admin ? "/admin" : ""}/projects/${device.project_id}/devices/${device.id}`}>Chi tiết <ArrowRight /></Link></Button></div></CardContent></Card>
}
