import { useEffect, useState } from "react"
import { useQuery } from "@tanstack/react-query"
import { Users } from "lucide-react"
import type { UserRole, UserStatus } from "@/entities/user/model/types"
import { accountApi } from "@/features/manage-accounts/api/account-api"
import { AccountFilters } from "@/features/manage-accounts/components/AccountFilters"
import { AccountTable } from "@/features/manage-accounts/components/AccountTable"
import { CreateAccountDialog } from "@/features/manage-accounts/components/CreateAccountDialog"
import { useAuthStore } from "@/features/auth/model/auth-store"
import { queryKeys } from "@/shared/api/query-keys"
import { Button } from "@/shared/ui/button"
import { EmptyState } from "@/shared/ui/empty-state"
import { PageHeader } from "@/shared/ui/page-header"
import { Skeleton } from "@/shared/ui/skeleton"

export function AccountsPage() {
  const authUser = useAuthStore((state) => state.user)
  const [search, setSearch] = useState("")
  const [queryText, setQueryText] = useState("")
  const [role, setRole] = useState<UserRole>()
  const [status, setStatus] = useState<UserStatus>()
  const [page, setPage] = useState(1)
  useEffect(() => {
    const timeout = window.setTimeout(() => { setQueryText(search.trim()); setPage(1) }, 275)
    return () => window.clearTimeout(timeout)
  }, [search])
  const query = useQuery({
    queryKey: queryKeys.users.list([authUser?.id, authUser?.token_version], queryText, role, status, page),
    queryFn: () => accountApi.list(queryText, page, false, role, status),
  })
  const changeRole = (value: UserRole | undefined) => { setRole(value); setPage(1) }
  const changeStatus = (value: UserStatus | undefined) => { setStatus(value); setPage(1) }
  const pageCount = Math.max(1, Math.ceil((query.data?.total ?? 0) / (query.data?.page_size ?? 20)))

  return <div className="flex flex-col gap-6">
    <PageHeader title="Quản lý tài khoản" description="Quản lý tài khoản đăng nhập, vai trò, trạng thái và bảo mật." actions={<CreateAccountDialog />} />
    <AccountFilters search={search} role={role} status={status} onSearchChange={setSearch} onRoleChange={changeRole} onStatusChange={changeStatus} />
    <p className="text-sm text-muted-foreground" aria-live="polite">{query.data?.total ?? 0} kết quả</p>
    {query.isLoading ? <Skeleton className="h-80" /> : query.isError ? <EmptyState icon={Users} title="Không thể tải danh sách tài khoản" description="Vui lòng kiểm tra kết nối Backend và thử lại." action={<Button variant="outline" onClick={() => void query.refetch()}>Thử lại</Button>} /> : query.data?.items.length ? <><AccountTable users={query.data.items} /><div className="flex items-center justify-between gap-3"><p className="text-sm text-muted-foreground">Trang {page} / {pageCount}</p><div className="flex gap-2"><Button variant="outline" disabled={page <= 1} onClick={() => setPage((current) => current - 1)}>Trang trước</Button><Button variant="outline" disabled={page >= pageCount} onClick={() => setPage((current) => current + 1)}>Trang sau</Button></div></div></> : <EmptyState icon={Users} title="Không tìm thấy tài khoản" description="Thử thay đổi từ khóa hoặc bộ lọc." />}
  </div>
}
