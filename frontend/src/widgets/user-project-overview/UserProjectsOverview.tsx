import { Activity, AlertTriangle, Boxes, Clock3, FolderKanban, RadioTower, WifiOff } from "lucide-react"
import { useNavigate } from "react-router-dom"
import type { UserOverview } from "@/features/user-overview/model/overview.types"
import type { UserRole } from "@/entities/user/model/types"
import { ProjectHealthBadge } from "@/entities/project/ui/project-health-badge"
import { formatDateTime } from "@/shared/lib/date"
import { Badge } from "@/shared/ui/badge"
import { Card, CardContent, CardHeader, CardTitle } from "@/shared/ui/card"
import { EmptyState } from "@/shared/ui/empty-state"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/shared/ui/table"

const roleLabel = { ADMIN: "Quản trị viên", OWNER: "Chủ dự án", VIEWER: "Người xem" } as const

export function UserProjectsOverview({ data, role }: { data: UserOverview; role: UserRole }) {
  const navigate = useNavigate()
  const summary = data.summary
  const metrics = [
    { label: "Tổng số dự án", value: summary.total_projects, note: `${summary.active_projects} đang hoạt động`, icon: FolderKanban },
    { label: "Dự án cần chú ý", value: summary.attention_projects, note: "Theo mức độ sức khỏe", icon: AlertTriangle },
    { label: "Thiết bị trực tuyến", value: summary.online_devices, note: `${summary.offline_devices} ngoại tuyến`, icon: Boxes },
    { label: "Cảm biến kết nối", value: summary.online_sensors, note: `${summary.offline_sensors} mất kết nối`, icon: RadioTower },
    { label: "Cảnh báo chưa xử lý", value: summary.open_alerts, note: "Trên mọi dự án", icon: Activity },
    { label: "Dữ liệu gần nhất", value: summary.latest_received_at ? "Đã nhận" : "Chưa có", note: formatDateTime(summary.latest_received_at), icon: Clock3 },
  ]
  const openProject = (projectId: number) => navigate(`/projects/${projectId}/overview`)

  return <div className="flex flex-col gap-5">
    <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3 2xl:grid-cols-6">
      {metrics.map(({ label, value, note, icon: Icon }) => <Card key={label}><CardHeader className="flex-row items-start justify-between gap-3 pb-3"><div><CardTitle className="text-sm text-muted-foreground">{label}</CardTitle><strong className="mt-2 block text-2xl">{value}</strong></div><Icon aria-hidden="true" /></CardHeader><CardContent className="text-xs text-muted-foreground">{note}</CardContent></Card>)}
    </div>
    {!data.projects.length ? <EmptyState icon={WifiOff} title="Bạn chưa có dự án nào" description={role === "VIEWER" ? "Bạn chưa được mời vào dự án nào." : "Liên hệ Quản trị viên để được cấp dự án."} /> : <>
      <Card className="hidden overflow-hidden md:block"><CardHeader><CardTitle>Danh sách dự án</CardTitle></CardHeader><CardContent className="overflow-x-auto p-0"><Table><TableHeader><TableRow><TableHead>Dự án</TableHead><TableHead>Vai trò</TableHead><TableHead>Địa điểm</TableHead><TableHead>Thiết bị</TableHead><TableHead>Cảm biến</TableHead><TableHead>Sức khỏe</TableHead><TableHead>Cảnh báo</TableHead><TableHead>Dữ liệu cuối</TableHead></TableRow></TableHeader><TableBody>{data.projects.map((project) => <TableRow key={project.id} role="link" tabIndex={0} className="cursor-pointer hover:bg-accent focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-ring" onClick={() => openProject(project.id)} onKeyDown={(event) => { if (event.key === "Enter" || event.key === " ") { event.preventDefault(); openProject(project.id) } }}><TableCell><div className="font-medium">{project.name}</div><div className="text-xs text-muted-foreground">{project.code}</div></TableCell><TableCell><Badge variant="outline">{roleLabel[project.access_role]}</Badge></TableCell><TableCell>{project.location || "Chưa cập nhật"}</TableCell><TableCell>{project.online_device_count}/{project.device_count}</TableCell><TableCell>{project.online_sensor_count}/{project.sensor_count}</TableCell><TableCell><ProjectHealthBadge status={project.health_status} /></TableCell><TableCell className={project.open_alert_count ? "font-semibold text-destructive" : undefined}>{project.open_alert_count}</TableCell><TableCell>{formatDateTime(project.last_telemetry_at)}</TableCell></TableRow>)}</TableBody></Table></CardContent></Card>
      <div className="grid gap-3 md:hidden">{data.projects.map((project) => <Card key={project.id} role="link" tabIndex={0} className="cursor-pointer focus-visible:ring-2 focus-visible:ring-ring" onClick={() => openProject(project.id)} onKeyDown={(event) => { if (event.key === "Enter") openProject(project.id) }}><CardHeader><div className="flex items-start justify-between gap-3"><div><CardTitle>{project.name}</CardTitle><p className="mt-1 text-xs text-muted-foreground">{project.code} · {project.location || "Chưa cập nhật"}</p></div><ProjectHealthBadge status={project.health_status} /></div></CardHeader><CardContent className="grid grid-cols-3 gap-3 text-sm"><div><span className="block text-xs text-muted-foreground">Vai trò</span>{roleLabel[project.access_role]}</div><div><span className="block text-xs text-muted-foreground">Thiết bị</span>{project.online_device_count}/{project.device_count}</div><div><span className="block text-xs text-muted-foreground">Cảnh báo</span>{project.open_alert_count}</div><div className="col-span-3 text-xs text-muted-foreground">Dữ liệu cuối: {formatDateTime(project.last_telemetry_at)}</div></CardContent></Card>)}</div>
    </>}
  </div>
}
