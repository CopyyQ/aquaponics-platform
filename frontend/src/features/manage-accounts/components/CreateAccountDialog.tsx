import { useState } from "react"
import { zodResolver } from "@hookform/resolvers/zod"
import { useMutation, useQueryClient } from "@tanstack/react-query"
import { AxiosError } from "axios"
import { LoaderCircle, UserPlus } from "lucide-react"
import { useForm } from "react-hook-form"
import { toast } from "sonner"
import { accountApi } from "@/features/manage-accounts/api/account-api"
import { useProtectedQueryScope } from "@/features/auth/model/use-protected-query-scope"
import { invalidateQueries } from "@/shared/api/query-invalidation"
import { queryKeys } from "@/shared/api/query-keys"
import { createAccountSchema, type CreateAccountValues } from "@/features/manage-accounts/schemas/create-account.schema"
import { Button } from "@/shared/ui/button"
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle, DialogTrigger } from "@/shared/ui/dialog"
import { Input } from "@/shared/ui/input"
import { Label } from "@/shared/ui/label"
import { Select, SelectContent, SelectGroup, SelectItem, SelectTrigger, SelectValue } from "@/shared/ui/select"
import { Switch } from "@/shared/ui/switch"

const defaults: CreateAccountValues = {
  username: "", full_name: "", email: "", phone_number: "", address: "",
  system_role: "OWNER", status: "ACTIVE", password: "", confirm_password: "",
  must_change_password: true,
}

function apiErrorMessage(error: unknown): string {
  if (error instanceof AxiosError) {
    const detail = (error.response?.data as { detail?: unknown } | undefined)?.detail
    if (typeof detail === "string") return detail
  }
  return "Không thể tạo tài khoản. Vui lòng kiểm tra lại dữ liệu."
}

export function CreateAccountDialog() {
  const [open, setOpen] = useState(false)
  const queryClient = useQueryClient()
  const { queryScope } = useProtectedQueryScope()
  const form = useForm<CreateAccountValues>({ resolver: zodResolver(createAccountSchema), defaultValues: defaults })
  const mutation = useMutation({
    mutationFn: accountApi.create,
    onSuccess: async (user) => {
      queryClient.setQueryData(queryKeys.users.detail(queryScope, user.id), user)
      await invalidateQueries.users(queryClient, queryScope, user.id)
      form.reset(defaults)
      setOpen(false)
      toast.success("Đã tạo tài khoản thành công.")
    },
    onError: (error) => toast.error(apiErrorMessage(error)),
  })
  const { errors } = form.formState

  const field = (name: "username" | "full_name" | "email" | "phone_number" | "address" | "password" | "confirm_password", label: string, type = "text", autoComplete?: string) => (
    <div className="flex flex-col gap-2" data-invalid={errors[name] ? "true" : undefined}>
      <Label htmlFor={`create-account-${name}`}>{label}</Label>
      <Input id={`create-account-${name}`} type={type} autoComplete={autoComplete} aria-invalid={!!errors[name]} {...form.register(name)} />
      {errors[name] ? <p className="text-xs text-destructive" role="alert">{errors[name]?.message}</p> : null}
    </div>
  )

  return (
    <Dialog open={open} onOpenChange={(next) => { if (mutation.isPending) return; setOpen(next); if (!next) form.reset(defaults) }}>
      <DialogTrigger asChild><Button><UserPlus data-icon="inline-start" />Thêm tài khoản</Button></DialogTrigger>
      <DialogContent className="max-h-[calc(100vh-2rem)] max-w-2xl overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Thêm tài khoản</DialogTitle>
          <DialogDescription>Tạo tài khoản đăng nhập mới. Mật khẩu được mã hóa và không thể xem lại.</DialogDescription>
        </DialogHeader>
        <form className="flex flex-col gap-5" onSubmit={form.handleSubmit((values) => mutation.mutate(values))}>
          <div className="grid gap-4 sm:grid-cols-2">
            {field("username", "Tên đăng nhập", "text", "username")}
            {field("full_name", "Họ và tên", "text", "name")}
            {field("email", "Email", "email", "email")}
            {field("phone_number", "Số điện thoại", "tel", "tel")}
            <div className="sm:col-span-2">{field("address", "Địa chỉ", "text", "street-address")}</div>
            <div className="flex flex-col gap-2">
              <Label htmlFor="create-account-role">Vai trò</Label>
              <Select value={form.watch("system_role")} onValueChange={(value) => form.setValue("system_role", value as CreateAccountValues["system_role"], { shouldValidate: true })}>
                <SelectTrigger id="create-account-role"><SelectValue /></SelectTrigger>
                <SelectContent><SelectGroup><SelectItem value="ADMIN">Quản trị viên</SelectItem><SelectItem value="OWNER">Chủ dự án</SelectItem><SelectItem value="VIEWER">Người xem</SelectItem></SelectGroup></SelectContent>
              </Select>
            </div>
            <div className="flex flex-col gap-2">
              <Label htmlFor="create-account-status">Trạng thái</Label>
              <Select value={form.watch("status")} onValueChange={(value) => form.setValue("status", value as CreateAccountValues["status"], { shouldValidate: true })}>
                <SelectTrigger id="create-account-status"><SelectValue /></SelectTrigger>
                <SelectContent><SelectGroup><SelectItem value="ACTIVE">Đang hoạt động</SelectItem><SelectItem value="DISABLED">Vô hiệu hóa</SelectItem><SelectItem value="LOCKED">Đang bị khóa</SelectItem></SelectGroup></SelectContent>
              </Select>
            </div>
            {field("password", "Mật khẩu", "password", "new-password")}
            {field("confirm_password", "Xác nhận mật khẩu", "password", "new-password")}
          </div>
          <div className="flex items-start gap-3 rounded-lg border p-3">
            <Switch id="create-account-must-change" checked={form.watch("must_change_password")} onCheckedChange={(checked) => form.setValue("must_change_password", checked, { shouldDirty: true })} />
            <div className="flex flex-col gap-1"><Label htmlFor="create-account-must-change">Yêu cầu đổi mật khẩu khi đăng nhập lần đầu</Label><p className="text-xs text-muted-foreground">Nên bật cho tài khoản bàn giao cho người dùng thật.</p></div>
          </div>
          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => setOpen(false)}>Hủy</Button>
            <Button type="submit" disabled={mutation.isPending}>{mutation.isPending ? <LoaderCircle data-icon="inline-start" className="animate-spin" /> : <UserPlus data-icon="inline-start" />}Tạo tài khoản</Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}
