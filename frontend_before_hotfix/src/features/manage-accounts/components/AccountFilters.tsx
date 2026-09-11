import { Search, X } from "lucide-react"
import type { UserRole, UserStatus } from "@/entities/user/model/types"
import { Button } from "@/shared/ui/button"
import { Input } from "@/shared/ui/input"
import { Select, SelectContent, SelectGroup, SelectItem, SelectTrigger, SelectValue } from "@/shared/ui/select"

export function AccountFilters({ search, role, status, onSearchChange, onRoleChange, onStatusChange }: {
  search: string
  role: UserRole | undefined
  status: UserStatus | undefined
  onSearchChange: (value: string) => void
  onRoleChange: (value: UserRole | undefined) => void
  onStatusChange: (value: UserStatus | undefined) => void
}) {
  return <div className="grid gap-3 md:grid-cols-[minmax(16rem,1fr)_12rem_12rem]">
    <div className="relative">
      <Search className="pointer-events-none absolute left-3 top-2.5 size-4 text-muted-foreground" />
      <Input className="px-9" value={search} onChange={(event) => onSearchChange(event.target.value)} placeholder="Tên, username, email hoặc số điện thoại" aria-label="Tìm kiếm tài khoản" />
      {search ? <Button type="button" variant="ghost" size="icon" className="absolute right-0 top-0" aria-label="Xóa từ khóa" onClick={() => onSearchChange("")}><X /></Button> : null}
    </div>
    <Select value={role ?? "ALL"} onValueChange={(value) => onRoleChange(value === "ALL" ? undefined : value as UserRole)}><SelectTrigger aria-label="Lọc vai trò"><SelectValue /></SelectTrigger><SelectContent><SelectGroup><SelectItem value="ALL">Tất cả vai trò</SelectItem><SelectItem value="ADMIN">Quản trị viên</SelectItem><SelectItem value="OWNER">Chủ dự án</SelectItem><SelectItem value="VIEWER">Người xem</SelectItem></SelectGroup></SelectContent></Select>
    <Select value={status ?? "ALL"} onValueChange={(value) => onStatusChange(value === "ALL" ? undefined : value as UserStatus)}><SelectTrigger aria-label="Lọc trạng thái"><SelectValue /></SelectTrigger><SelectContent><SelectGroup><SelectItem value="ALL">Tất cả trạng thái</SelectItem><SelectItem value="ACTIVE">Đang hoạt động</SelectItem><SelectItem value="DISABLED">Vô hiệu hóa</SelectItem><SelectItem value="LOCKED">Đang bị khóa</SelectItem><SelectItem value="SOFT_DELETED">Đã xóa mềm</SelectItem></SelectGroup></SelectContent></Select>
  </div>
}
