import { useEffect, useState } from "react"
import { useQuery } from "@tanstack/react-query"
import { RefreshCw, Search, X } from "lucide-react"
import { useNavigate } from "react-router-dom"
import { ProjectHealthBadge } from "@/entities/project/ui/project-health-badge"
import { useAuthStore } from "@/features/auth/model/auth-store"
import { useProtectedQueryScope } from "@/features/auth/model/use-protected-query-scope"
import { userMonitoringApi } from "@/features/user-monitoring/api/user-monitoring-api"
import type { UserMonitoringFilters, UserMonitoringSort } from "@/features/user-monitoring/model/types"
import { queryKeys } from "@/shared/api/query-keys"
import { formatDateTime } from "@/shared/lib/date"
import { Badge } from "@/shared/ui/badge"
import { Button } from "@/shared/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/shared/ui/card"
import { EmptyState } from "@/shared/ui/empty-state"
import { Input } from "@/shared/ui/input"
import { Select, SelectContent, SelectGroup, SelectItem, SelectTrigger, SelectValue } from "@/shared/ui/select"
import { Skeleton } from "@/shared/ui/skeleton"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/shared/ui/table"

const initialFilters: UserMonitoringFilters = {
  q: "", health_status: "ALL", device_status: "ALL", has_offline_sensors: undefined,
  has_out_of_range: undefined, sort_by: "risk_score", sort_order: "desc", page: 1, page_size: 20,
}
const roleLabel = { ADMIN: "Quản trị viên", OWNER: "Chủ dự án", VIEWER: "Người xem" } as const

export function UserMonitoringBoard() {
  const navigate = useNavigate()
  const role = useAuthStore((state) => state.user?.system_role ?? "VIEWER")
  const [search, setSearch] = useState("")
  const [filters, setFilters] = useState(initialFilters)
  const { active, queryScope } = useProtectedQueryScope()
  useEffect(() => {
    const timer = window.setTimeout(() => setFilters((current) => ({ ...current, q: search.trim(), page: 1 })), 275)
    return () => window.clearTimeout(timer)
  }, [search])
  const query = useQuery({ queryKey: queryKeys.user.monitoring(queryScope, filters), queryFn: () => userMonitoringApi.projects(filters), enabled: active, refetchInterval: 15_000 })
  const patch = (next: Partial<UserMonitoringFilters>) => setFilters((current) => ({ ...current, ...next, page: 1 }))
  const openProject = (id: number) => navigate(`/projects/${id}/monitoring`)
  const rows = query.data?.items ?? []

  return <div className="flex flex-col gap-5">
    <Card><CardContent className="grid gap-3 pt-5 md:grid-cols-2 xl:grid-cols-3 2xl:grid-cols-6">
      <div className="relative md:col-span-2 xl:col-span-1"><Search aria-hidden="true" className="pointer-events-none absolute left-3 top-2.5 size-4 text-muted-foreground" /><Input value={search} onChange={(event) => setSearch(event.target.value)} className="px-9" placeholder="Tên hoặc mã dự án…" aria-label="Tìm theo tên hoặc mã dự án" />{search ? <Button variant="ghost" size="icon" className="absolute right-0 top-0" aria-label="Xóa tìm kiếm" onClick={() => setSearch("")}><X /></Button> : null}</div>
      <Select value={filters.health_status} onValueChange={(value) => patch({ health_status: value })}><SelectTrigger aria-label="Trạng thái sức khỏe"><SelectValue /></SelectTrigger><SelectContent><SelectGroup><SelectItem value="ALL">Mọi sức khỏe</SelectItem><SelectItem value="CRITICAL">Nguy hiểm</SelectItem><SelectItem value="WARNING">Cảnh báo</SelectItem><SelectItem value="ATTENTION">Cần chú ý</SelectItem><SelectItem value="HEALTHY">Bình thường</SelectItem></SelectGroup></SelectContent></Select>
      <Select value={filters.device_status} onValueChange={(value) => patch({ device_status: value })}><SelectTrigger aria-label="Trạng thái thiết bị"><SelectValue /></SelectTrigger><SelectContent><SelectGroup><SelectItem value="ALL">Mọi thiết bị</SelectItem><SelectItem value="ONLINE">Tất cả trực tuyến</SelectItem><SelectItem value="OFFLINE">Có thiết bị ngoại tuyến</SelectItem></SelectGroup></SelectContent></Select>
      <Select value={filters.has_offline_sensors === undefined ? "ALL" : String(filters.has_offline_sensors)} onValueChange={(value) => patch({ has_offline_sensors: value === "ALL" ? undefined : value === "true" })}><SelectTrigger aria-label="Cảm biến mất kết nối"><SelectValue /></SelectTrigger><SelectContent><SelectGroup><SelectItem value="ALL">Mọi kết nối cảm biến</SelectItem><SelectItem value="true">Có cảm biến mất kết nối</SelectItem><SelectItem value="false">Không mất kết nối</SelectItem></SelectGroup></SelectContent></Select>
      <Select value={filters.has_out_of_range === undefined ? "ALL" : String(filters.has_out_of_range)} onValueChange={(value) => patch({ has_out_of_range: value === "ALL" ? undefined : value === "true" })}><SelectTrigger aria-label="Dữ liệu ngoài ngưỡng"><SelectValue /></SelectTrigger><SelectContent><SelectGroup><SelectItem value="ALL">Mọi trạng thái ngưỡng</SelectItem><SelectItem value="true">Có dữ liệu ngoài ngưỡng</SelectItem><SelectItem value="false">Không ngoài ngưỡng</SelectItem></SelectGroup></SelectContent></Select>
      <Select value={filters.sort_by} onValueChange={(value) => patch({ sort_by: value as UserMonitoringSort })}><SelectTrigger aria-label="Sắp xếp dự án"><SelectValue /></SelectTrigger><SelectContent><SelectGroup><SelectItem value="risk_score">Rủi ro cao đến thấp</SelectItem><SelectItem value="alerts">Nhiều cảnh báo nhất</SelectItem><SelectItem value="online_ratio">Tỷ lệ online</SelectItem><SelectItem value="last_telemetry_at">Dữ liệu mới nhất</SelectItem><SelectItem value="project_name">Tên dự án</SelectItem></SelectGroup></SelectContent></Select>
    </CardContent></Card>
    {query.isLoading ? <Skeleton className="h-[30rem]" /> : query.isError ? <EmptyState icon={RefreshCw} title="Không thể tải dữ liệu quan trắc" description="Kiểm tra kết nối và thử lại." action={<Button variant="outline" onClick={() => query.refetch()}>Thử lại</Button>} /> : !rows.length ? <EmptyState icon={Search} title={query.data?.total === 0 && !filters.q ? "Bạn chưa có dự án nào" : "Không có dự án phù hợp"} description={query.data?.total === 0 && !filters.q ? (role === "VIEWER" ? "Bạn chưa được mời vào dự án nào." : "Liên hệ Quản trị viên để được cấp dự án.") : "Hãy thay đổi bộ lọc hiện tại."} /> : <>
      <Card className="hidden overflow-hidden md:block"><CardHeader><CardTitle className="flex items-center justify-between gap-3">Ưu tiên theo mức rủi ro <span className="text-sm font-normal text-muted-foreground">{query.data?.total} dự án</span></CardTitle></CardHeader><CardContent className="overflow-x-auto p-0"><Table><TableHeader><TableRow><TableHead>Dự án</TableHead><TableHead>Vai trò</TableHead><TableHead>Địa điểm</TableHead><TableHead>Sức khỏe</TableHead><TableHead>Thiết bị online</TableHead><TableHead>Cảm biến mất kết nối</TableHead><TableHead>Ngoài ngưỡng</TableHead><TableHead>Cảnh báo mở</TableHead><TableHead>Dữ liệu cuối</TableHead></TableRow></TableHeader><TableBody>{rows.map((project) => <TableRow key={project.id} role="link" tabIndex={0} className="cursor-pointer hover:bg-accent focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-ring" onClick={() => openProject(project.id)} onKeyDown={(event) => { if (event.key === "Enter" || event.key === " ") { event.preventDefault(); openProject(project.id) } }}><TableCell><div className="font-medium">{project.name}</div><div className="text-xs text-muted-foreground">{project.code}</div></TableCell><TableCell><Badge variant="outline">{roleLabel[project.access_role]}</Badge></TableCell><TableCell>{project.location || "—"}</TableCell><TableCell><ProjectHealthBadge status={project.health_status} /></TableCell><TableCell>{project.online_device_count}/{project.device_count}</TableCell><TableCell>{project.offline_sensor_count}</TableCell><TableCell>{project.out_of_range_sensor_count}</TableCell><TableCell className={project.open_alert_count ? "font-semibold text-destructive" : undefined}>{project.open_alert_count}</TableCell><TableCell>{formatDateTime(project.last_telemetry_at)}</TableCell></TableRow>)}</TableBody></Table></CardContent></Card>
      <div className="grid gap-3 md:hidden">{rows.map((project) => <Card key={project.id} role="link" tabIndex={0} className="cursor-pointer" onClick={() => openProject(project.id)} onKeyDown={(event) => { if (event.key === "Enter") openProject(project.id) }}><CardHeader><div className="flex items-start justify-between gap-3"><div><CardTitle>{project.name}</CardTitle><p className="mt-1 text-xs text-muted-foreground">{project.code} · {roleLabel[project.access_role]}</p></div><ProjectHealthBadge status={project.health_status} /></div></CardHeader><CardContent className="grid grid-cols-3 gap-3 text-sm"><div><span className="block text-xs text-muted-foreground">Thiết bị</span>{project.online_device_count}/{project.device_count}</div><div><span className="block text-xs text-muted-foreground">Mất kết nối</span>{project.offline_sensor_count}</div><div><span className="block text-xs text-muted-foreground">Cảnh báo</span>{project.open_alert_count}</div><div className="col-span-3 text-xs text-muted-foreground">Dữ liệu cuối: {formatDateTime(project.last_telemetry_at)}</div></CardContent></Card>)}</div>
    </>}
  </div>
}
