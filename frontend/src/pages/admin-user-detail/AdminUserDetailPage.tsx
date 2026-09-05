import { useQuery } from "@tanstack/react-query"
import { useParams } from "react-router-dom"
import { projectApi } from "@/entities/project/api/project-api"
import { userApi } from "@/entities/user/api/user-api"
import { UserAccountSecurityTab } from "@/features/admin-user-detail/UserAccountSecurityTab"
import { UserProjectsTab } from "@/features/admin-user-detail/UserProjectsTab"
import { SummaryCards } from "@/widgets/user-project-overview/SummaryCards"
import { formatDateTime } from "@/shared/lib/date"
import { Badge } from "@/shared/ui/badge"
import { Card, CardContent, CardHeader, CardTitle } from "@/shared/ui/card"
import { EmptyState } from "@/shared/ui/empty-state"
import { PageHeader } from "@/shared/ui/page-header"
import { Skeleton } from "@/shared/ui/skeleton"
import { StatusBadge } from "@/shared/ui/status-badge"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/shared/ui/tabs"
import { UserRound } from "lucide-react"
import { ProjectFormDialog } from "@/features/manage-projects/components/ProjectFormDialog"
import { auditActionLabels, auditEntityLabels, formatAuditDetail } from "@/entities/audit/lib/audit-format"
import { useAuthStore } from "@/features/auth/model/auth-store"
import { queryKeys } from "@/shared/api/query-keys"
import { Alert, AlertDescription, AlertTitle } from "@/shared/ui/alert"
import { ShieldAlert } from "lucide-react"

export function AdminUserDetailPage() {
  const userId = Number(useParams().userId)
  const enabled = Number.isFinite(userId)
  const authUser = useAuthStore((state) => state.user)
  const authScope = [authUser?.id, authUser?.token_version] as const
  const authenticated = authUser?.status === "ACTIVE" && authUser.is_deleted === false && authUser.deleted_at === null
  const user = useQuery({ queryKey: queryKeys.users.detail(authScope, userId), queryFn: () => userApi.adminGet(userId), enabled: enabled && authenticated })
  const operational = user.data?.status === "ACTIVE" && user.data?.is_deleted === false
  const projects = useQuery({ queryKey: queryKeys.users.projects(authScope, userId), queryFn: () => projectApi.listForUser(userId), enabled: enabled && authenticated && operational })
  const activity = useQuery({ queryKey: queryKeys.users.activity(authScope, userId), queryFn: () => userApi.activity(userId), enabled: enabled && authenticated })
  if (user.isLoading || (operational && projects.isLoading)) return <Skeleton className="h-[36rem]" />
  if (user.isError || (operational && projects.isError)) return <EmptyState icon={UserRound} title="Không thể tải người dùng" description="Bạn không có quyền hoặc dữ liệu không còn tồn tại." />
  if (!user.data || (operational && !projects.data)) return <EmptyState icon={UserRound} title="Không tìm thấy người dùng" description="Hãy kiểm tra lại đường dẫn." />
  return (
    <div className="flex flex-col gap-6">
      <PageHeader title={user.data.full_name} description={`@${user.data.username} · ${user.data.email}`} actions={<StatusBadge value={user.data.status} />} />
      <Tabs defaultValue="overview">
        <TabsList className="w-full justify-start overflow-x-auto">
          <TabsTrigger value="overview">{operational ? "Tổng quan" : "Thông tin tài khoản"}</TabsTrigger>
          {operational ? <TabsTrigger value="projects">Dự án</TabsTrigger> : null}
          <TabsTrigger value="account">Tài khoản và bảo mật</TabsTrigger>
          <TabsTrigger value="activity">Hoạt động</TabsTrigger>
        </TabsList>
        <TabsContent value="overview" className="flex flex-col gap-5">
          {!operational ? <Alert variant="destructive"><ShieldAlert /><AlertTitle>Tài khoản không hoạt động.</AlertTitle><AlertDescription>Toàn bộ dự án và dữ liệu vận hành liên quan đang được ẩn.</AlertDescription></Alert> : null}
          {operational ? <SummaryCards summary={{ total_devices: user.data.device_count, online_devices: user.data.online_device_count, offline_devices: user.data.offline_device_count, total_sensors: user.data.sensor_count, open_alerts: user.data.open_alert_count }} /> : null}
          <Card><CardHeader><CardTitle>Thông tin người dùng</CardTitle></CardHeader><CardContent><dl className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">{[
            ["Họ tên", user.data.full_name], ["Username", `@${user.data.username}`], ["Email", user.data.email],
            ["Số điện thoại", user.data.phone_number], ["Vai trò", user.data.system_role], ["Trạng thái", user.data.status],
            ...(operational ? [["Số Project", user.data.project_count], ["Tổng Device", user.data.device_count], ["Tổng Sensor", user.data.sensor_count],
            ["Device online/offline", `${user.data.online_device_count}/${user.data.offline_device_count}`], ["Cảnh báo đang mở", user.data.open_alert_count]] : []),
            ["Lần đăng nhập cuối", formatDateTime(user.data.last_login_at)], ["Ngày tạo", formatDateTime(user.data.created_at)],
          ].map(([label, value]) => <div key={label}><dt className="text-sm text-muted-foreground">{label}</dt><dd className="mt-1 font-medium">{value}</dd></div>)}</dl></CardContent></Card>
        </TabsContent>
        {operational && projects.data ? <TabsContent value="projects" className="flex flex-col gap-5"><div className="flex justify-end"><ProjectFormDialog userId={userId} /></div><UserProjectsTab projects={projects.data} userId={userId} /></TabsContent> : null}
        <TabsContent value="account"><UserAccountSecurityTab user={user.data} /></TabsContent>
        <TabsContent value="activity">
          <Card><CardHeader><CardTitle>Nhật ký hoạt động</CardTitle></CardHeader><CardContent className="flex flex-col gap-3">{activity.isLoading ? <Skeleton className="h-32" /> : activity.data?.length ? activity.data.map((item) => <div key={item.id} className="flex flex-col gap-2 rounded-lg border p-3 sm:flex-row sm:items-start sm:justify-between"><div className="flex flex-col gap-1"><Badge variant="outline" className="self-start">{auditActionLabels[item.action] ?? "Thao tác hệ thống"}</Badge><p className="text-sm">{auditEntityLabels[item.entity_type] ?? "Đối tượng"}: {item.target_name}</p><p className="text-sm text-muted-foreground">{formatAuditDetail(item)} · Người thực hiện: {item.actor_name}</p></div><time className="whitespace-nowrap text-xs text-muted-foreground">{formatDateTime(item.created_at)}</time></div>) : <p className="py-8 text-center text-sm text-muted-foreground">Chưa có hoạt động.</p>}</CardContent></Card>
        </TabsContent>
      </Tabs>
    </div>
  )
}
