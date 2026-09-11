import { useQuery } from "@tanstack/react-query"
import { AlertTriangle, BellRing, CircleAlert, Cpu, FolderKanban, RefreshCw, RadioTower, Users } from "lucide-react"
import { useNavigate } from "react-router-dom"
import { adminMonitoringApi } from "@/features/admin-monitoring/api/admin-monitoring-api"
import type { MonitoringFilters, MonitoringProject } from "@/features/admin-monitoring/model/types"
import { overviewApi } from "@/features/user-overview/api/overview.api"
import { useProtectedQueryScope } from "@/features/auth/model/use-protected-query-scope"
import { queryKeys } from "@/shared/api/query-keys"
import { formatDateTime } from "@/shared/lib/date"
import { Badge } from "@/shared/ui/badge"
import { Button } from "@/shared/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/shared/ui/card"
import { EmptyState } from "@/shared/ui/empty-state"
import { PageHeader } from "@/shared/ui/page-header"
import { Skeleton } from "@/shared/ui/skeleton"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/shared/ui/table"

const filters: MonitoringFilters = { q: "", health_status: "ALL", device_status: "ALL", stale_only: false, sort_by: "risk_score", sort_order: "desc", page: 1, page_size: 10 }
const healthLabels: Record<MonitoringProject["health_status"], string> = { HEALTHY: "Ổn định", ATTENTION: "Cần theo dõi", WARNING: "Cảnh báo", CRITICAL: "Nguy hiểm" }
const healthVariants: Record<MonitoringProject["health_status"], "success" | "secondary" | "warning" | "destructive"> = { HEALTHY: "success", ATTENTION: "secondary", WARNING: "warning", CRITICAL: "destructive" }

function Metric({ label, value, icon: Icon, onClick, danger = false }: { label: string; value: number; icon: typeof Users; onClick: () => void; danger?: boolean }) {
  return <button type="button" onClick={onClick} className="group flex min-h-32 flex-col justify-between gap-3 rounded-xl border bg-card p-4 text-left shadow-sm transition hover:-translate-y-0.5 hover:border-primary/40 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"><div className="flex items-start justify-between gap-3"><span className="text-sm font-medium text-muted-foreground">{label}</span><span className={danger ? "grid size-9 place-items-center rounded-lg bg-destructive/10 text-destructive" : "grid size-9 place-items-center rounded-lg bg-primary/10 text-primary"}><Icon aria-hidden="true" /></span></div><strong className="text-3xl">{value.toLocaleString("vi-VN")}</strong></button>
}

function ProjectHealthTable({ projects, onOpen }: { projects: MonitoringProject[]; onOpen: (id: number) => void }) {
  return <div className="overflow-x-auto"><Table><TableHeader><TableRow><TableHead>Ưu tiên</TableHead><TableHead>Dự án</TableHead><TableHead>Khách hàng</TableHead><TableHead>Tình trạng</TableHead><TableHead>Thiết bị</TableHead><TableHead>Cảm biến</TableHead><TableHead>Cảnh báo</TableHead><TableHead>Dữ liệu cuối</TableHead></TableRow></TableHeader><TableBody>{projects.map((project) => <TableRow key={project.id} tabIndex={0} className="cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-ring" onClick={() => onOpen(project.id)} onKeyDown={(event) => { if (event.key === "Enter") onOpen(project.id) }}><TableCell>{project.rank}</TableCell><TableCell><div className="font-semibold">{project.name}</div><div className="text-xs text-muted-foreground">{project.code}</div></TableCell><TableCell>{project.customer_name}</TableCell><TableCell><Badge variant={healthVariants[project.health_status]}>{healthLabels[project.health_status]} · {project.risk_score}</Badge></TableCell><TableCell>{project.online_device_count}/{project.device_count} online</TableCell><TableCell>{project.abnormal_sensor_count}</TableCell><TableCell><span className="text-destructive">{project.critical_alert_count}</span> / {project.warning_alert_count}</TableCell><TableCell className={project.stale ? "text-destructive" : "text-muted-foreground"}>{formatDateTime(project.last_telemetry_at)}</TableCell></TableRow>)}</TableBody></Table></div>
}

export function AdminProjectHealthBoard() {
  const navigate = useNavigate()
  const { active, queryScope } = useProtectedQueryScope()
  const overview = useQuery({ queryKey: queryKeys.adminOverview.detail(queryScope), queryFn: overviewApi.admin, enabled: active, staleTime: 15_000, refetchInterval: 30_000 })
  const monitoring = useQuery({ queryKey: queryKeys.adminMonitoringProjects.list(queryScope, filters), queryFn: () => adminMonitoringApi.projects(filters), enabled: active, staleTime: 10_000, refetchInterval: 15_000 })
  if (overview.isLoading || monitoring.isLoading) return <div className="flex flex-col gap-4"><Skeleton className="h-20" /><Skeleton className="h-32" /><Skeleton className="h-96" /></div>
  if (overview.isError || monitoring.isError || !overview.data || !monitoring.data) return <EmptyState icon={AlertTriangle} title="Không thể tải trung tâm vận hành" description="Kiểm tra kết nối Backend hoặc quyền truy cập." />
  const summary = overview.data.summary
  const projects = monitoring.data.items
  const metrics = [{ label: "Khách hàng", value: summary.total_customers, icon: Users, route: "/admin/users" }, { label: "Dự án", value: monitoring.data.total, icon: FolderKanban, route: "/monitoring" }, { label: "Thiết bị mất kết nối", value: summary.offline_devices, icon: Cpu, route: "/monitoring", danger: summary.offline_devices > 0 }, { label: "Cảm biến cần kiểm tra", value: summary.offline_sensors, icon: RadioTower, route: "/monitoring", danger: summary.offline_sensors > 0 }, { label: "Cảnh báo chưa xử lý", value: summary.open_alerts, icon: BellRing, route: "/admin/alerts", danger: summary.open_alerts > 0 }]
  return <div className="flex flex-col gap-6"><div className="flex flex-wrap items-start justify-between gap-4"><PageHeader title="Trung tâm vận hành Aquaponics" description="Giám sát toàn bộ khách hàng, dự án, thiết bị và cảnh báo." /><div className="flex items-center gap-3"><span className="hidden text-right text-xs text-muted-foreground sm:block">Dữ liệu nhận gần nhất<br /><strong className="text-sm text-foreground">{formatDateTime(summary.latest_received_at)}</strong></span><Button variant="outline" size="sm" onClick={() => { void Promise.all([overview.refetch(), monitoring.refetch()]) }}><RefreshCw data-icon="inline-start" />Làm mới</Button></div></div><div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-5">{metrics.map((metric) => <Metric key={metric.label} {...metric} onClick={() => navigate(metric.route)} />)}</div><Card><CardHeader><CardTitle>Dự án cần theo dõi</CardTitle></CardHeader><CardContent>{projects.length ? <ProjectHealthTable projects={projects} onOpen={(id) => navigate(`/admin/projects/${id}/overview`)} /> : <EmptyState icon={CircleAlert} title="Chưa có dự án" description="Tạo dự án để bắt đầu giám sát." />}</CardContent></Card></div>
}
