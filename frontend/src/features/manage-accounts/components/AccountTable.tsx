import { useNavigate } from "react-router-dom"
import type { AdminUserDetail } from "@/entities/user/model/types"
import { AccountActionsMenu } from "@/features/manage-accounts/components/AccountActionsMenu"
import { AccountStatusBadge } from "@/features/manage-accounts/components/AccountStatusBadge"
import { formatDateTime } from "@/shared/lib/date"
import { Card, CardContent } from "@/shared/ui/card"
import { StatusBadge } from "@/shared/ui/status-badge"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/shared/ui/table"

export function AccountTable({ users }: { users: AdminUserDetail[] }) {
  const navigate = useNavigate()
  return <Card><CardContent className="overflow-x-auto p-0"><Table><TableHeader><TableRow><TableHead>Họ tên</TableHead><TableHead>Tên đăng nhập</TableHead><TableHead>Email</TableHead><TableHead>Số điện thoại</TableHead><TableHead>Vai trò</TableHead><TableHead>Trạng thái</TableHead><TableHead>Lần đăng nhập cuối</TableHead><TableHead>Ngày tạo</TableHead><TableHead className="text-right">Thao tác</TableHead></TableRow></TableHeader><TableBody>{users.map((user) => <TableRow key={user.id} className="cursor-pointer outline-none hover:bg-accent focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-ring" tabIndex={0} role="link" onClick={() => navigate(`/admin/users/${user.id}`)} onKeyDown={(event) => { if (event.key === "Enter") navigate(`/admin/users/${user.id}`) }}><TableCell className="font-medium">{user.full_name}</TableCell><TableCell>@{user.username}</TableCell><TableCell>{user.email}</TableCell><TableCell>{user.phone_number}</TableCell><TableCell><StatusBadge value={user.system_role} /></TableCell><TableCell><AccountStatusBadge status={user.status} /></TableCell><TableCell className="whitespace-nowrap">{formatDateTime(user.last_login_at)}</TableCell><TableCell className="whitespace-nowrap">{formatDateTime(user.created_at)}</TableCell><TableCell className="text-right" onClick={(event) => event.stopPropagation()} onKeyDown={(event) => event.stopPropagation()}><AccountActionsMenu user={user} /></TableCell></TableRow>)}</TableBody></Table></CardContent></Card>
}
