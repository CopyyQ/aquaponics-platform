import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { MoreHorizontal, UserRoundX, Users } from "lucide-react"
import { toast } from "sonner"
import { userApi } from "@/entities/user/api/user-api"
import { MemberFormDialog } from "@/features/manage-accounts/components/MemberFormDialog"
import { useAuthStore } from "@/features/auth/model/auth-store"
import { useProtectedQueryScope } from "@/features/auth/model/use-protected-query-scope"
import { invalidateQueries } from "@/shared/api/query-invalidation"
import { queryKeys } from "@/shared/api/query-keys"
import { formatDateTime } from "@/shared/lib/date"
import { Button } from "@/shared/ui/button"
import { Card, CardContent } from "@/shared/ui/card"
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from "@/shared/ui/dropdown-menu"
import { EmptyState } from "@/shared/ui/empty-state"
import { PageHeader } from "@/shared/ui/page-header"
import { StatusBadge } from "@/shared/ui/status-badge"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/shared/ui/table"

export function AdminUsersPage() {
  const actor = useAuthStore((state) => state.user)!
  const queryClient = useQueryClient()
  const { queryScope } = useProtectedQueryScope()
  const query = useQuery({ queryKey: queryKeys.users.members, queryFn: userApi.list })
  const disable = useMutation({ mutationFn: userApi.disable, onSuccess: async (_result, userId) => { await invalidateQueries.users(queryClient, queryScope, userId); toast.success("Đã vô hiệu hóa tài khoản") }, onError: () => toast.error("Không thể vô hiệu hóa tài khoản") })
  const enable = useMutation({ mutationFn: userApi.enable, onSuccess: async (_result, userId) => { await invalidateQueries.users(queryClient, queryScope, userId); toast.success("Đã kích hoạt tài khoản") }, onError: () => toast.error("Không thể kích hoạt tài khoản") })
  const assignOwner = useMutation({ mutationFn: userApi.assignOwner, onSuccess: async (_result, userId) => { await invalidateQueries.users(queryClient, queryScope, userId); toast.success("Đã gán Chủ hệ thống") }, onError: () => toast.error("Không thể gán Chủ hệ thống") })
  return <div className="space-y-6"><PageHeader title="Thành viên" description={actor.system_role === "OWNER" ? "Chủ hệ thống chỉ quản lý tài khoản Người xem." : "Quản lý tài khoản và vai trò toàn hệ thống."} actions={<MemberFormDialog actorRole={actor.system_role} />} />{query.data?.length ? <Card><CardContent className="p-0"><Table><TableHeader><TableRow><TableHead>Người dùng</TableHead><TableHead>Vai trò</TableHead><TableHead>Trạng thái</TableHead><TableHead>Đăng nhập cuối</TableHead><TableHead className="text-right">Thao tác</TableHead></TableRow></TableHeader><TableBody>{query.data.map((user) => <TableRow key={user.id}><TableCell><div className="font-medium">{user.full_name}</div><div className="text-xs text-muted-foreground">{user.email} · @{user.username}</div></TableCell><TableCell><StatusBadge value={user.system_role} /></TableCell><TableCell><StatusBadge value={user.status} /></TableCell><TableCell className="text-muted-foreground">{formatDateTime(user.last_login_at)}</TableCell><TableCell className="text-right"><DropdownMenu><DropdownMenuTrigger asChild><Button variant="ghost" size="icon"><MoreHorizontal /></Button></DropdownMenuTrigger><DropdownMenuContent align="end">{user.status === "ACTIVE" ? <DropdownMenuItem onSelect={() => disable.mutate(user.id)}><UserRoundX /> Vô hiệu hóa</DropdownMenuItem> : <DropdownMenuItem onSelect={() => enable.mutate(user.id)}>Kích hoạt</DropdownMenuItem>}{actor.system_role === "ADMIN" && user.system_role !== "OWNER" && <DropdownMenuItem onSelect={() => assignOwner.mutate(user.id)}>Gán làm Chủ hệ thống</DropdownMenuItem>}</DropdownMenuContent></DropdownMenu></TableCell></TableRow>)}</TableBody></Table></CardContent></Card> : <EmptyState icon={Users} title="Chưa có thành viên" description="Tạo tài khoản Owner hoặc Viewer để bàn giao quyền truy cập hệ thống." />}</div>
}
