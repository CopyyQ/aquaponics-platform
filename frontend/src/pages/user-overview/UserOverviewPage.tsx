import { useQuery } from "@tanstack/react-query"
import { RefreshCw } from "lucide-react"
import { overviewApi } from "@/features/user-overview/api/overview.api"
import { queryKeys } from "@/shared/api/query-keys"
import { UserProjectsOverview } from "@/widgets/user-project-overview/UserProjectsOverview"
import { useAuthStore } from "@/features/auth/model/auth-store"
import { useProtectedQueryScope } from "@/features/auth/model/use-protected-query-scope"
import { Button } from "@/shared/ui/button"
import { Card, CardContent } from "@/shared/ui/card"
import { PageHeader } from "@/shared/ui/page-header"
import { Skeleton } from "@/shared/ui/skeleton"

export function UserOverviewPage() {
  const role = useAuthStore((state) => state.user?.system_role ?? "VIEWER")
  const { active, queryScope } = useProtectedQueryScope()
  const query = useQuery({ queryKey: queryKeys.user.overview(queryScope), queryFn: overviewApi.me, enabled: active, refetchInterval: 30_000 })
  if (query.isLoading) return <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">{Array.from({ length: 4 }).map((_, index) => <Skeleton key={index} className="h-32" />)}</div>
  if (query.isError) return <Card><CardContent className="flex flex-col items-center gap-3 p-10 text-center"><strong>Không thể tải tổng quan</strong><Button variant="outline" onClick={() => query.refetch()}>Thử lại</Button></CardContent></Card>
  const data = query.data!
  return <div className="flex flex-col gap-7"><PageHeader title="Tổng quan" description="Toàn bộ dự án bạn sở hữu hoặc được mời tham gia." actions={<Button variant="outline" onClick={() => query.refetch()}><RefreshCw data-icon="inline-start" className={query.isFetching ? "animate-spin" : undefined} />Làm mới</Button>} /><UserProjectsOverview data={data} role={role} /></div>
}
