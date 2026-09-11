import { useState } from "react"
import { useForm } from "react-hook-form"
import { useMutation, useQueryClient } from "@tanstack/react-query"
import { toast } from "sonner"
import type { AdminUserDetail, UserRole } from "@/entities/user/model/types"
import { userApi } from "@/entities/user/api/user-api"
import { useProtectedQueryScope } from "@/features/auth/model/use-protected-query-scope"
import { invalidateQueries } from "@/shared/api/query-invalidation"
import { queryKeys } from "@/shared/api/query-keys"
import { Button } from "@/shared/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/shared/ui/card"
import { Input } from "@/shared/ui/input"
import { Label } from "@/shared/ui/label"
import { Select, SelectContent, SelectGroup, SelectItem, SelectTrigger, SelectValue } from "@/shared/ui/select"
import { AdminSetPasswordDialog } from "@/features/manage-accounts/components/AdminSetPasswordDialog"

interface AccountValues {
  full_name: string
  email: string
  phone_number: string
  system_role: UserRole
}

export function UserAccountSecurityTab({ user }: { user: AdminUserDetail }) {
  const queryClient = useQueryClient()
  const { queryScope } = useProtectedQueryScope()
  const { register, handleSubmit, setValue } = useForm<AccountValues>({
    defaultValues: {
      full_name: user.full_name, email: user.email, phone_number: user.phone_number,
      system_role: user.system_role,
    },
  })
  const update = useMutation({
    mutationFn: (values: AccountValues) => userApi.adminUpdate(user.id, values),
    onSuccess: async (updatedUser) => {
      queryClient.setQueryData(queryKeys.users.detail(queryScope, user.id), updatedUser)
      await invalidateQueries.users(queryClient, queryScope, user.id)
      toast.success("Đã cập nhật thông tin người dùng")
    },
    onError: () => toast.error("Không thể cập nhật người dùng"),
  })
  return (
    <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_22rem]">
      <Card>
        <CardHeader><CardTitle>Thông tin tài khoản</CardTitle><CardDescription>Không bao gồm mật khẩu hoặc secret bảo mật.</CardDescription></CardHeader>
        <CardContent>
          <form className="flex flex-col gap-4" onSubmit={handleSubmit((values) => update.mutate(values))}>
            <div className="grid gap-4 sm:grid-cols-2">
              <div className="flex flex-col gap-2"><Label htmlFor="admin-full-name">Họ tên</Label><Input id="admin-full-name" {...register("full_name", { required: true })} /></div>
              <div className="flex flex-col gap-2"><Label htmlFor="admin-email">Email</Label><Input id="admin-email" type="email" {...register("email", { required: true })} /></div>
              <div className="flex flex-col gap-2"><Label htmlFor="admin-phone">Số điện thoại</Label><Input id="admin-phone" {...register("phone_number", { required: true })} /></div>
              <div className="flex flex-col gap-2"><Label>Vai trò</Label><Select defaultValue={user.system_role} onValueChange={(value) => setValue("system_role", value as UserRole)}><SelectTrigger><SelectValue /></SelectTrigger><SelectContent><SelectGroup><SelectItem value="ADMIN">Admin</SelectItem><SelectItem value="OWNER">Owner</SelectItem><SelectItem value="VIEWER">Viewer</SelectItem></SelectGroup></SelectContent></Select></div>
            </div>
            <Button type="submit" className="self-start" disabled={update.isPending}>Lưu thay đổi</Button>
          </form>
        </CardContent>
      </Card>
      <div className="flex flex-col gap-6">
        <LifecycleCard user={user} />
        <ResetPasswordCard user={user} />
      </div>
    </div>
  )
}

function LifecycleCard({ user }: { user: AdminUserDetail }) {
  const queryClient = useQueryClient()
  const { queryScope } = useProtectedQueryScope()
  const [reason, setReason] = useState("")
  const mutation = useMutation({
    mutationFn: (action: "activate" | "disable" | "lock" | "unlock") => {
      if (action === "activate") return userApi.activate(user.id, reason)
      if (action === "disable") return userApi.disableAccount(user.id, reason)
      if (action === "lock") return userApi.lock(user.id, reason)
      return userApi.unlock(user.id, reason)
    },
    onSuccess: async () => {
      await invalidateQueries.users(queryClient, queryScope, user.id)
      setReason("")
      toast.success("Đã cập nhật vòng đời tài khoản")
    },
    onError: () => toast.error("Không thể cập nhật tài khoản; hãy kiểm tra quy tắc Admin cuối cùng"),
  })
  return <Card><CardHeader><CardTitle>Quyền và trạng thái</CardTitle><CardDescription>Vô hiệu hóa, khóa hoặc đổi vai trò sẽ thu hồi phiên đăng nhập hiện tại.</CardDescription></CardHeader><CardContent className="flex flex-col gap-3"><div className="flex flex-col gap-2"><Label htmlFor="lifecycle-reason">Lý do</Label><Input id="lifecycle-reason" value={reason} onChange={(event) => setReason(event.target.value)} placeholder="Nhập lý do để lưu vào nhật ký" /></div><div className="flex flex-wrap gap-2">{user.status !== "ACTIVE" ? <Button variant="outline" onClick={() => mutation.mutate("activate")} disabled={mutation.isPending}>Kích hoạt</Button> : <Button variant="outline" onClick={() => mutation.mutate("disable")} disabled={mutation.isPending}>Vô hiệu hóa</Button>}{user.status === "LOCKED" ? <Button variant="outline" onClick={() => mutation.mutate("unlock")} disabled={mutation.isPending}>Mở khóa</Button> : <Button variant="destructive" onClick={() => mutation.mutate("lock")} disabled={mutation.isPending}>Khóa tài khoản</Button>}</div></CardContent></Card>
}

function ResetPasswordCard({ user }: { user: AdminUserDetail }) {
  const [open, setOpen] = useState(false)
  const queryClient = useQueryClient()
  const { queryScope } = useProtectedQueryScope()
  const forceLogout = useMutation({
    mutationFn: () => userApi.forceLogout(user.id, "Thu hồi phiên theo yêu cầu quản trị"),
    onSuccess: async () => {
      await Promise.all([
        invalidateQueries.users(queryClient, queryScope, user.id),
        queryClient.invalidateQueries({ queryKey: queryKeys.users.activity(queryScope, user.id), refetchType: "active" }),
      ])
      toast.success("Đã thu hồi toàn bộ phiên đăng nhập")
    },
    onError: () => toast.error("Không thể thu hồi phiên đăng nhập"),
  })
  return (
    <Card>
      <CardHeader><CardTitle>Bảo mật</CardTitle><CardDescription>Đặt mật khẩu mới mà không cần biết mật khẩu hiện tại của người dùng.</CardDescription></CardHeader>
      <CardContent>
        <div className="flex flex-wrap gap-2"><Button variant="destructive" onClick={() => setOpen(true)} disabled={user.status === "SOFT_DELETED" || user.is_deleted}>Đặt lại mật khẩu</Button><Button variant="outline" onClick={() => forceLogout.mutate()} disabled={forceLogout.isPending}>Thu hồi phiên</Button></div>
        <AdminSetPasswordDialog user={user} open={open} onOpenChange={setOpen} />
      </CardContent>
    </Card>
  )
}
