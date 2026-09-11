import { useEffect, useState } from "react"
import { useQuery } from "@tanstack/react-query"
import { Search, Users, X } from "lucide-react"
import { useNavigate } from "react-router-dom"
import { userApi } from "@/entities/user/api/user-api"
import { formatDateTime } from "@/shared/lib/date"
import { Button } from "@/shared/ui/button"
import { Card, CardContent } from "@/shared/ui/card"
import { EmptyState } from "@/shared/ui/empty-state"
import { Input } from "@/shared/ui/input"
import { PageHeader } from "@/shared/ui/page-header"
import { Skeleton } from "@/shared/ui/skeleton"
import { StatusBadge } from "@/shared/ui/status-badge"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/shared/ui/table"
import { useAuthStore } from "@/features/auth/model/auth-store"
import { queryKeys } from "@/shared/api/query-keys"

export function CustomerDirectoryPage({ mode = "customers" }: { mode?: "customers" | "accounts" }) {
  const navigate = useNavigate()
  const [search, setSearch] = useState("")
  const [queryText, setQueryText] = useState("")
  const authUser = useAuthStore((state) => state.user)
  const authenticated = authUser?.status === "ACTIVE" && authUser.is_deleted === false && authUser.deleted_at === null
  useEffect(() => {
    const timeout = window.setTimeout(() => setQueryText(search.trim()), 275)
    return () => window.clearTimeout(timeout)
  }, [search])
  const query = useQuery({ queryKey: queryKeys.users.list([authUser?.id, authUser?.token_version], mode, queryText, 1), queryFn: () => userApi.adminList(queryText, 1, mode === "customers"), enabled: authenticated })
  const open = (id: number) => navigate(`/admin/users/${id}`)
  return <div className="flex flex-col gap-6">
    <PageHeader title={mode === "customers" ? "Danh mục khách hàng" : "Quản lý tài khoản"} description={mode === "customers" ? "Theo dõi Project, thiết bị, cảm biến và tình trạng dữ liệu của từng khách hàng." : "Tài khoản nội bộ và khách hàng được phân biệt rõ bằng vai trò và trạng thái vòng đời."} />
    <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
      <div className="relative w-full sm:max-w-xl">
        <Search className="pointer-events-none absolute left-3 top-2.5 size-4 text-muted-foreground" />
        <Input className="px-9" value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Tìm theo tên, username, email hoặc số điện thoại" aria-label="Tìm khách hàng" />
        {search ? <Button variant="ghost" size="icon" className="absolute right-0 top-0" aria-label="Xóa từ khóa" onClick={() => setSearch("")}><X /></Button> : null}
      </div>
      <p className="text-sm text-muted-foreground" aria-live="polite">{query.data?.total ?? 0} kết quả</p>
    </div>
    {query.isLoading ? <Skeleton className="h-80" /> : query.isError ? <EmptyState icon={Users} title="Không thể tải danh mục" description="Vui lòng thử lại hoặc kiểm tra kết nối Backend." /> : query.data?.items.length ? <Card><CardContent className="overflow-x-auto p-0"><Table><TableHeader><TableRow><TableHead>{mode === "customers" ? "Khách hàng" : "Tài khoản"}</TableHead><TableHead>Vai trò</TableHead><TableHead>Project</TableHead><TableHead>Device</TableHead><TableHead>Sensor</TableHead><TableHead>Device online / tổng</TableHead><TableHead>Cảnh báo mở</TableHead><TableHead>Dữ liệu cuối</TableHead><TableHead>Trạng thái</TableHead><TableHead /></TableRow></TableHeader><TableBody>{query.data.items.map((user) => { const operational = user.status === "ACTIVE" && user.is_deleted === false && user.deleted_at === null; return <TableRow key={user.id} role="link" tabIndex={0} className="cursor-pointer outline-none hover:bg-accent focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-ring" onClick={() => open(user.id)} onKeyDown={(event) => { if (event.key === "Enter" || event.key === " ") { event.preventDefault(); open(user.id) } }}><TableCell><div className="font-medium">{user.full_name}</div><div className="text-xs text-muted-foreground">@{user.username} · {user.email}</div>{!operational ? <div className="mt-1 text-xs text-muted-foreground">{user.disabled_reason ?? user.locked_reason ?? "Dữ liệu vận hành đã được ẩn"} · {formatDateTime(user.disabled_at ?? user.locked_at ?? user.deleted_at)}</div> : null}</TableCell><TableCell><StatusBadge value={user.system_role} /></TableCell><TableCell>{operational ? user.project_count : "—"}</TableCell><TableCell>{operational ? user.device_count : "—"}</TableCell><TableCell>{operational ? user.sensor_count : "—"}</TableCell><TableCell>{operational ? `${user.online_device_count} / ${user.device_count}` : "—"}</TableCell><TableCell>{operational ? user.open_alert_count : "—"}</TableCell><TableCell>{operational ? formatDateTime(user.last_telemetry_at) : "—"}</TableCell><TableCell><StatusBadge value={user.status} /></TableCell><TableCell><Button variant="outline" size="sm" onClick={(event) => { event.stopPropagation(); open(user.id) }}>Xem chi tiết</Button></TableCell></TableRow> })}</TableBody></Table></CardContent></Card> : <EmptyState icon={Users} title={mode === "customers" ? "Không tìm thấy khách hàng" : "Không tìm thấy tài khoản"} description="Thử thay đổi hoặc xóa từ khóa tìm kiếm." />}
  </div>
}
