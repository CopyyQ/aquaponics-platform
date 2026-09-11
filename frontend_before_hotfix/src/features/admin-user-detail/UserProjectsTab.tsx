import { useMemo, useState } from "react"
import { useMutation, useQueryClient } from "@tanstack/react-query"
import { Boxes, ExternalLink, RadioTower } from "lucide-react"
import { Link } from "react-router-dom"

import type { AdminUserProjectList } from "@/entities/project/model/types"
import type { AdminUserProject } from "@/entities/project/model/types"
import {
  filterProjectsByStatus,
  PROJECT_STATUS_FILTER_OPTIONS,
  projectStatusCounts,
  type ProjectStatusFilter,
} from "@/entities/project/model/project-status-filter"
import { projectApi } from "@/entities/project/api/project-api"
import { useProtectedQueryScope } from "@/features/auth/model/use-protected-query-scope"
import { queryKeys } from "@/shared/api/query-keys"
import { formatDateTime } from "@/shared/lib/date"
import { Badge } from "@/shared/ui/badge"
import { Button } from "@/shared/ui/button"
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/shared/ui/card"
import { EmptyState } from "@/shared/ui/empty-state"
import { StatusBadge } from "@/shared/ui/status-badge"
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/shared/ui/dialog"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/shared/ui/table"

export function UserProjectsTab({ projects, userId }: { projects: AdminUserProjectList; userId: number }) {
  const [statusFilter, setStatusFilter] = useState<ProjectStatusFilter>("active")
  const counts = useMemo(() => projectStatusCounts(projects.items), [projects.items])
  const visibleProjects = useMemo(
    () => filterProjectsByStatus(projects.items, statusFilter),
    [projects.items, statusFilter],
  )
  if (!projects.items.length) {
    return (
      <EmptyState
        icon={Boxes}
        title="Khách hàng chưa có Project"
        description="Hãy tạo Project trước khi thêm thiết bị và cảm biến."
      />
    )
  }

  return (
    <>
      <div className="flex flex-col gap-3 rounded-xl border bg-card p-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <p className="font-medium">Lọc Project theo trạng thái</p>
          <p className="text-sm text-muted-foreground" aria-live="polite">
            {statusFilter === "active"
              ? `${counts.active} Project đang hoạt động`
              : statusFilter === "disabled"
                ? `${counts.disabled} Project đã vô hiệu hóa`
                : `${counts.active + counts.disabled} Project • ${counts.active} đang hoạt động • ${counts.disabled} đã vô hiệu hóa`}
          </p>
        </div>
        <div className="flex flex-wrap gap-2" role="group" aria-label="Lọc Project theo trạng thái">
          {PROJECT_STATUS_FILTER_OPTIONS.map((option) => (
            <Button
              key={option.value}
              type="button"
              size="sm"
              variant={statusFilter === option.value ? "default" : "outline"}
              aria-pressed={statusFilter === option.value}
              onClick={() => setStatusFilter(option.value)}
            >
              {option.label}
            </Button>
          ))}
        </div>
      </div>
      {!visibleProjects.length ? (
        <EmptyState
          icon={Boxes}
          title={statusFilter === "active" ? "Không có Project đang hoạt động" : "Không có Project phù hợp"}
          description="Chọn trạng thái khác để xem các Project vẫn được bảo toàn trong hệ thống."
        />
      ) : <>
      <Card className="hidden overflow-hidden md:block">
        <CardHeader>
          <CardTitle>Danh sách Project</CardTitle>
          <CardDescription>
            {statusFilter === "active"
              ? `${counts.active} Project đang hoạt động.`
              : statusFilter === "disabled"
                ? `${counts.disabled} Project đã vô hiệu hóa.`
                : `${counts.active + counts.disabled} Project: ${counts.active} đang hoạt động, ${counts.disabled} đã vô hiệu hóa.`} Dữ liệu lịch sử luôn được bảo toàn.
          </CardDescription>
        </CardHeader>
        <CardContent className="overflow-x-auto p-0">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Project</TableHead>
                <TableHead>Địa điểm</TableHead>
                <TableHead>Trạng thái</TableHead>
                <TableHead>Thiết bị</TableHead>
                <TableHead>Cảm biến</TableHead>
                <TableHead>Cảnh báo mở</TableHead>
                <TableHead>Dữ liệu cuối</TableHead>
                <TableHead className="text-right">Thao tác</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {visibleProjects.map((project) => (
                <TableRow key={project.id}>
                  <TableCell>
                    <div className="font-medium">{project.name}</div>
                    <div className="font-mono text-xs text-muted-foreground">{project.code}</div>
                  </TableCell>
                  <TableCell>{project.location || "Chưa cập nhật"}</TableCell>
                  <TableCell><StatusBadge value={project.status} /></TableCell>
                  <TableCell>{project.device_count}</TableCell>
                  <TableCell>{project.sensor_count}</TableCell>
                  <TableCell>
                    <Badge variant={project.open_alert_count ? "destructive" : "outline"}>
                      {project.open_alert_count}
                    </Badge>
                  </TableCell>
                  <TableCell className="whitespace-nowrap">{formatDateTime(project.latest_telemetry_at)}</TableCell>
                  <TableCell>
                    <div className="flex justify-end gap-2">
                      <Button asChild size="sm" variant="outline">
                        <Link to={`/admin/projects/${project.id}/overview`}>
                          <ExternalLink data-icon="inline-start" />
                          Xem chi tiết
                        </Link>
                      </Button>
                      {project.status === "DISABLED" ? <ReactivateProjectButton project={project} userId={userId} /> : null}
                      <Button asChild size="sm" variant="outline">
                        <Link to={`/admin/projects/${project.id}/devices`}>
                          <Boxes data-icon="inline-start" />
                          Thiết bị và cảm biến
                        </Link>
                      </Button>
                    </div>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      <div className="grid gap-3 md:hidden">
        {visibleProjects.map((project) => (
          <Card key={project.id}>
            <CardHeader>
              <div className="flex items-start justify-between gap-3">
                <div className="min-w-0">
                  <CardTitle className="truncate">{project.name}</CardTitle>
                  <CardDescription className="truncate font-mono">{project.code}</CardDescription>
                </div>
                <StatusBadge value={project.status} />
              </div>
            </CardHeader>
            <CardContent className="flex flex-col gap-3">
              <p className="text-sm text-muted-foreground">{project.location || "Chưa cập nhật địa điểm"}</p>
              <div className="grid grid-cols-3 gap-2 text-center text-sm">
                <div className="rounded-lg bg-muted/40 p-2"><strong className="block text-lg">{project.device_count}</strong>Thiết bị</div>
                <div className="rounded-lg bg-muted/40 p-2"><strong className="block text-lg">{project.sensor_count}</strong>Cảm biến</div>
                <div className="rounded-lg bg-muted/40 p-2"><strong className="block text-lg">{project.open_alert_count}</strong>Cảnh báo</div>
              </div>
              <p className="text-xs text-muted-foreground">Dữ liệu cuối: {formatDateTime(project.latest_telemetry_at)}</p>
            </CardContent>
            <CardFooter className="flex flex-wrap gap-2">
              <Button asChild size="sm" variant="outline">
                <Link to={`/admin/projects/${project.id}/overview`}><ExternalLink data-icon="inline-start" />Xem chi tiết</Link>
              </Button>
              {project.status === "DISABLED" ? <ReactivateProjectButton project={project} userId={userId} /> : null}
              <Button asChild size="sm" variant="outline">
                <Link to={`/admin/projects/${project.id}/devices`}><RadioTower data-icon="inline-start" />Thiết bị và cảm biến</Link>
              </Button>
            </CardFooter>
          </Card>
        ))}
      </div>
      </>}
    </>
  )
}

function ReactivateProjectButton({ project, userId }: { project: AdminUserProject; userId: number }) {
  const [open, setOpen] = useState(false)
  const client = useQueryClient()
  const { queryScope } = useProtectedQueryScope()
  const mutation = useMutation({
    mutationFn: () => projectApi.activate(project.id),
    onSuccess: async () => {
      await client.invalidateQueries({ queryKey: queryKeys.users.projects(queryScope, userId) })
      setOpen(false)
    },
  })
  return <><Button size="sm" onClick={() => setOpen(true)}>Kích hoạt lại</Button><Dialog open={open} onOpenChange={setOpen}><DialogContent><DialogHeader><DialogTitle>Kích hoạt lại dự án?</DialogTitle><DialogDescription>Dự án sẽ chuyển sang trạng thái hoạt động. Trạng thái kết nối thực tế chỉ được cập nhật khi thiết bị gửi dữ liệu mới.</DialogDescription></DialogHeader><DialogFooter><Button variant="outline" onClick={() => setOpen(false)}>Hủy</Button><Button onClick={() => mutation.mutate()} disabled={mutation.isPending}>Kích hoạt lại</Button></DialogFooter></DialogContent></Dialog></>
}
