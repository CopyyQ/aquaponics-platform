import { useState } from "react"
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { AlertTriangle } from "lucide-react"
import { Link, NavLink, Outlet, useParams } from "react-router-dom"
import { toast } from "sonner"
import type { ProjectOverview } from "@/entities/project/model/types"
import { ProjectContext } from "@/entities/project/model/project-context"
import { projectApi } from "@/entities/project/api/project-api"
import { useAuthStore } from "@/features/auth/model/auth-store"
import { Alert, AlertDescription, AlertTitle } from "@/shared/ui/alert"
import { Button } from "@/shared/ui/button"
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/shared/ui/dialog"
import { EmptyState } from "@/shared/ui/empty-state"
import { Label } from "@/shared/ui/label"
import { PageHeader } from "@/shared/ui/page-header"
import { Skeleton } from "@/shared/ui/skeleton"
import { StatusBadge } from "@/shared/ui/status-badge"
import { Textarea } from "@/shared/ui/textarea"
import { cn } from "@/shared/lib/utils"
import { useProtectedQueryScope } from "@/features/auth/model/use-protected-query-scope"
import { invalidateQueries } from "@/shared/api/query-invalidation"
import { queryKeys } from "@/shared/api/query-keys"

export function ProjectLayout() {
  const projectId = Number(useParams().projectId)
  const role = useAuthStore((state) => state.user?.system_role)
  const { active, queryScope } = useProtectedQueryScope()
  const query = useQuery({ queryKey: queryKeys.projects.detail(queryScope, projectId), queryFn: () => projectApi.overview(projectId), enabled: active && Number.isFinite(projectId) })
  if (query.isLoading) return <Skeleton className="h-[36rem]" />
  if (!query.data) return <EmptyState icon={AlertTriangle} title="Không thể tải dự án" description="Dự án không tồn tại hoặc bạn không có quyền truy cập." />
  const item = query.data
  const admin = role === "ADMIN"
  const tabs = [
    ["overview", "Tổng quan"], ["scada", "Sơ đồ vận hành"], ["monitoring", "Giám sát"],
    ["devices", "Thiết bị"], ["alerts", "Cảnh báo"],
    ...(role === "VIEWER" ? [] : [["notifications", "Thông báo & Nhật ký"], ["members", "Thành viên"], ["settings", "Cài đặt"]] as const),
  ] as const
  return <ProjectContext.Provider value={item}><div className="flex flex-col gap-6">
    <nav aria-label="Breadcrumb" className="flex flex-wrap items-center gap-2 text-sm text-muted-foreground">
      <Link className="hover:text-foreground hover:underline" to={admin ? "/admin/users" : "/projects"}>{admin ? "Danh mục khách hàng" : "Dự án"}</Link>
      {admin && item.owner ? <><span aria-hidden="true">→</span><Link className="hover:text-foreground hover:underline" to={`/admin/users/${item.owner.id}`}>{item.owner.full_name}</Link></> : null}
      <span aria-hidden="true">→</span><span className="text-foreground">{item.project.name}</span>
    </nav>
    <PageHeader title={item.project.name} description={`${item.project.code} · ${item.project.location || "Chưa có địa điểm"}`} actions={<div className="flex flex-wrap items-center gap-2"><StatusBadge value={item.project.status} />{admin ? <ProjectLifecycleAction projectId={projectId} status={item.project.status} /> : null}</div>} />
    {admin && item.project.status === "DISABLED" ? <Alert variant="destructive"><AlertTriangle /><AlertTitle>Dự án này đang bị vô hiệu hóa.</AlertTitle><AlertDescription>Dữ liệu lịch sử vẫn được bảo toàn. Bạn có thể kích hoạt lại dự án để tiếp tục vận hành.{item.project.disabled_reason ? ` Lý do: ${item.project.disabled_reason}` : ""}</AlertDescription></Alert> : null}
    <nav aria-label="Các mục của dự án" className="flex w-full gap-1 overflow-x-auto rounded-lg border bg-muted/30 p-1">
      {tabs.map(([path, label]) => <NavLink key={path} to={path} className={({ isActive }) => cn("whitespace-nowrap rounded-md px-3 py-2 text-sm font-medium outline-none hover:bg-background focus-visible:ring-2 focus-visible:ring-ring", isActive && "bg-background text-foreground shadow-sm")}>{label}</NavLink>)}
    </nav>
    <Outlet />
  </div></ProjectContext.Provider>
}

function ProjectLifecycleAction({ projectId, status }: { projectId: number; status: string }) {
  const [open, setOpen] = useState(false)
  const [reason, setReason] = useState("")
  const client = useQueryClient()
  const { queryScope } = useProtectedQueryScope()
  const disabled = status === "DISABLED"
  const mutation = useMutation({
    mutationFn: () => disabled ? projectApi.activate(projectId) : projectApi.disable(projectId, reason.trim()),
    onSuccess: async (project) => {
      client.setQueryData<ProjectOverview>(queryKeys.projects.detail(queryScope, projectId), (current) => current ? { ...current, project } : current)
      await invalidateQueries.projects(client, queryScope, projectId, project.owner_user_id)
      setReason("")
      setOpen(false)
      toast.success(disabled ? "Đã kích hoạt lại dự án" : "Đã vô hiệu hóa dự án")
    },
    onError: () => toast.error("Không thể cập nhật trạng thái dự án"),
  })
  return <>
    <Button variant={disabled ? "outline" : "destructive"} onClick={() => setOpen(true)} disabled={mutation.isPending}>{disabled ? "Kích hoạt lại" : "Vô hiệu hóa"}</Button>
    <Dialog open={open} onOpenChange={setOpen}><DialogContent><DialogHeader><DialogTitle>{disabled ? "Kích hoạt lại dự án?" : "Vô hiệu hóa dự án?"}</DialogTitle><DialogDescription>{disabled ? "Dự án sẽ chuyển sang trạng thái hoạt động. Thiết bị sẽ tiếp tục được phép vận hành theo cấu hình hiện tại; trạng thái kết nối thực tế chỉ cập nhật khi thiết bị gửi dữ liệu mới." : "Dự án vẫn xuất hiện trong danh sách quản trị và dữ liệu lịch sử không bị xóa. Bạn có thể kích hoạt lại bất kỳ lúc nào."}</DialogDescription></DialogHeader>{!disabled ? <div className="flex flex-col gap-2"><Label htmlFor="disable-project-reason">Lý do vô hiệu hóa</Label><Textarea id="disable-project-reason" value={reason} onChange={(event) => setReason(event.target.value)} aria-invalid={reason.trim().length > 0 && reason.trim().length < 3} aria-describedby="disable-project-reason-help" /><p id="disable-project-reason-help" className="text-xs text-muted-foreground">Nhập ít nhất 3 ký tự.</p></div> : null}<DialogFooter><Button variant="outline" onClick={() => setOpen(false)}>Hủy</Button><Button variant={disabled ? "default" : "destructive"} disabled={(!disabled && reason.trim().length < 3) || mutation.isPending} onClick={() => mutation.mutate()}>{disabled ? "Kích hoạt lại" : "Vô hiệu hóa"}</Button></DialogFooter></DialogContent></Dialog>
  </>
}
