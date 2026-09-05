import { useState } from "react"
import { useMutation, useQueryClient } from "@tanstack/react-query"
import { KeyRound, Lock, LockOpen, MoreHorizontal, Pencil, Power, RotateCcw, Trash2, UserRoundCheck, View } from "lucide-react"
import { useNavigate } from "react-router-dom"
import { toast } from "sonner"
import type { AdminUserDetail } from "@/entities/user/model/types"
import { accountApi } from "@/features/manage-accounts/api/account-api"
import { useProtectedQueryScope } from "@/features/auth/model/use-protected-query-scope"
import { invalidateQueries } from "@/shared/api/query-invalidation"
import { AdminSetPasswordDialog } from "@/features/manage-accounts/components/AdminSetPasswordDialog"
import { EditAccountDialog } from "@/features/manage-accounts/components/EditAccountDialog"
import { Button } from "@/shared/ui/button"
import { DropdownMenu, DropdownMenuContent, DropdownMenuGroup, DropdownMenuItem, DropdownMenuTrigger } from "@/shared/ui/dropdown-menu"

type LifecycleAction = "activate" | "disable" | "lock" | "unlock" | "delete" | "restore"

export function AccountActionsMenu({ user }: { user: AdminUserDetail }) {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const { queryScope } = useProtectedQueryScope()
  const [passwordOpen, setPasswordOpen] = useState(false)
  const [editOpen, setEditOpen] = useState(false)
  const mutation = useMutation({
    mutationFn: (action: LifecycleAction) => {
      if (action === "activate") return accountApi.activate(user.id)
      if (action === "disable") return accountApi.disable(user.id)
      if (action === "lock") return accountApi.lock(user.id)
      if (action === "unlock") return accountApi.unlock(user.id)
      if (action === "delete") return accountApi.softDelete(user.id)
      return accountApi.restore(user.id)
    },
    onSuccess: async () => {
      await invalidateQueries.users(queryClient, queryScope, user.id)
      toast.success("Đã cập nhật trạng thái tài khoản.")
    },
    onError: () => toast.error("Không thể cập nhật trạng thái tài khoản."),
  })
  const deleted = user.status === "SOFT_DELETED" || user.is_deleted

  return <>
    <DropdownMenu>
      <DropdownMenuTrigger asChild><Button variant="ghost" size="icon" aria-label={`Thao tác với ${user.full_name}`} disabled={mutation.isPending}><MoreHorizontal /></Button></DropdownMenuTrigger>
      <DropdownMenuContent align="end">
        <DropdownMenuGroup>
          {deleted ? <DropdownMenuItem onSelect={() => mutation.mutate("restore")}><RotateCcw />Khôi phục</DropdownMenuItem> : <>
            <DropdownMenuItem onSelect={() => navigate(`/admin/users/${user.id}`)}><View />Xem chi tiết</DropdownMenuItem>
            <DropdownMenuItem onSelect={() => setEditOpen(true)}><Pencil />Chỉnh sửa</DropdownMenuItem>
            <DropdownMenuItem onSelect={() => setPasswordOpen(true)}><KeyRound />Đặt lại mật khẩu</DropdownMenuItem>
            {user.status === "ACTIVE" ? <><DropdownMenuItem onSelect={() => mutation.mutate("disable")}><Power />Vô hiệu hóa</DropdownMenuItem><DropdownMenuItem onSelect={() => mutation.mutate("lock")}><Lock />Khóa</DropdownMenuItem></> : null}
            {user.status === "DISABLED" ? <DropdownMenuItem onSelect={() => mutation.mutate("activate")}><UserRoundCheck />Kích hoạt</DropdownMenuItem> : null}
            {user.status === "LOCKED" ? <DropdownMenuItem onSelect={() => mutation.mutate("unlock")}><LockOpen />Mở khóa</DropdownMenuItem> : null}
            <DropdownMenuItem onSelect={() => mutation.mutate("delete")}><Trash2 />Xóa mềm</DropdownMenuItem>
          </>}
        </DropdownMenuGroup>
      </DropdownMenuContent>
    </DropdownMenu>
    {!deleted ? <><AdminSetPasswordDialog user={user} open={passwordOpen} onOpenChange={setPasswordOpen} /><EditAccountDialog user={user} open={editOpen} onOpenChange={setEditOpen} /></> : null}
  </>
}
