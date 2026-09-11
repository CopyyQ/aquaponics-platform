import { useForm } from "react-hook-form"
import { zodResolver } from "@hookform/resolvers/zod"
import { z } from "zod"
import { useNavigate } from "react-router-dom"
import { toast } from "sonner"
import { httpClient } from "@/shared/api/http-client"
import { useAuthStore } from "@/features/auth/model/auth-store"
import type { User } from "@/entities/user/model/types"
import { Button } from "@/shared/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/shared/ui/card"
import { Input } from "@/shared/ui/input"
import { Label } from "@/shared/ui/label"
import { PageHeader } from "@/shared/ui/page-header"
import { StatusBadge } from "@/shared/ui/status-badge"

const passwordSchema = z.object({
  current_password: z.string().min(8, "Mật khẩu hiện tại tối thiểu 8 ký tự"),
  new_password: z.string().min(8, "Mật khẩu mới tối thiểu 8 ký tự"),
  confirm_password: z.string().min(8),
}).refine((value) => value.new_password === value.confirm_password, {
  message: "Mật khẩu xác nhận không khớp", path: ["confirm_password"],
})
type PasswordValues = z.infer<typeof passwordSchema>
interface ProfileValues { full_name: string; email: string; phone_number: string; address: string }

export function ProfilePage() {
  const user = useAuthStore((state) => state.user)!
  const setUser = useAuthStore((state) => state.setUser)
  const logout = useAuthStore((state) => state.logout)
  const navigate = useNavigate()
  const passwordForm = useForm<PasswordValues>({ resolver: zodResolver(passwordSchema) })
  const profileForm = useForm<ProfileValues>({ defaultValues: {
    full_name: user.full_name, email: user.email, phone_number: user.phone_number, address: user.address,
  } })
  const updateProfile = profileForm.handleSubmit(async (values) => {
    try {
      const updated = (await httpClient.patch<User>("/auth/me", values)).data
      setUser(updated)
      toast.success("Đã cập nhật hồ sơ")
    } catch { toast.error("Không thể cập nhật hồ sơ") }
  })
  const changePassword = passwordForm.handleSubmit(async (values) => {
    try {
      await httpClient.post("/auth/change-password", values)
      toast.success("Đổi mật khẩu thành công", { description: "Vui lòng đăng nhập lại bằng mật khẩu mới." })
      passwordForm.reset()
      logout()
      navigate("/login", { replace: true })
    } catch { toast.error("Không thể đổi mật khẩu", { description: "Kiểm tra mật khẩu hiện tại và mật khẩu xác nhận." }) }
  })
  return (
    <div className="flex flex-col gap-6">
      <PageHeader title={user.must_change_password ? "Bắt buộc đổi mật khẩu" : "Hồ sơ cá nhân"} description={user.must_change_password ? "Bạn cần đặt mật khẩu mới trước khi tiếp tục sử dụng hệ thống." : "Cập nhật thông tin cá nhân và bảo mật tài khoản."} actions={<StatusBadge value={user.system_role} />} />
      <div className="grid gap-6 lg:grid-cols-2">
        <Card><CardHeader><CardTitle>Thông tin cá nhân</CardTitle><CardDescription>Username @{user.username} không thể thay đổi.</CardDescription></CardHeader><CardContent><form className="flex flex-col gap-4" onSubmit={updateProfile}><div className="flex flex-col gap-2"><Label htmlFor="profile-name">Họ tên</Label><Input id="profile-name" {...profileForm.register("full_name", { required: true })} /></div><div className="flex flex-col gap-2"><Label htmlFor="profile-email">Email</Label><Input id="profile-email" type="email" {...profileForm.register("email", { required: true })} /></div><div className="flex flex-col gap-2"><Label htmlFor="profile-phone">Số điện thoại</Label><Input id="profile-phone" {...profileForm.register("phone_number", { required: true })} /></div><div className="flex flex-col gap-2"><Label htmlFor="profile-address">Địa chỉ</Label><Input id="profile-address" {...profileForm.register("address")} /></div><Button type="submit" className="self-start" disabled={profileForm.formState.isSubmitting}>Lưu hồ sơ</Button></form></CardContent></Card>
        <Card><CardHeader><CardTitle>Đổi mật khẩu</CardTitle><CardDescription>Mật khẩu mới phải khác mật khẩu hiện tại và có tối thiểu 8 ký tự.</CardDescription></CardHeader><CardContent><form className="flex flex-col gap-4" onSubmit={changePassword}><div className="flex flex-col gap-2"><Label htmlFor="current-password">Mật khẩu hiện tại</Label><Input id="current-password" type="password" autoComplete="current-password" {...passwordForm.register("current_password")} /></div><div className="flex flex-col gap-2"><Label htmlFor="new-password">Mật khẩu mới</Label><Input id="new-password" type="password" autoComplete="new-password" {...passwordForm.register("new_password")} /></div><div className="flex flex-col gap-2"><Label htmlFor="confirm-password">Xác nhận mật khẩu mới</Label><Input id="confirm-password" type="password" autoComplete="new-password" aria-invalid={!!passwordForm.formState.errors.confirm_password} {...passwordForm.register("confirm_password")} />{passwordForm.formState.errors.confirm_password ? <p className="text-xs text-destructive">{passwordForm.formState.errors.confirm_password.message}</p> : null}</div><Button type="submit" className="self-start" disabled={passwordForm.formState.isSubmitting}>Đổi mật khẩu</Button></form></CardContent></Card>
      </div>
    </div>
  )
}
