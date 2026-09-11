import { PageHeader } from "@/shared/ui/page-header"
import { useAuthStore } from "@/features/auth/model/auth-store"
import { AdminMonitoringBoard } from "@/widgets/admin-project-health/AdminMonitoringBoard"
import { UserMonitoringBoard } from "@/widgets/user-project-monitoring/UserMonitoringBoard"

export function UserMonitoringPage() {
  const role = useAuthStore((state) => state.user?.system_role)
  if (role === "ADMIN") return <AdminMonitoringBoard />
  return <div className="flex flex-col gap-7">
    <PageHeader title="Quan trắc" description="Ưu tiên dự án theo rủi ro, kết nối cảm biến và cảnh báo đang mở." />
    <UserMonitoringBoard />
  </div>
}
