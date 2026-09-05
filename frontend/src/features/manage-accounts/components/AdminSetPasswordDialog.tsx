import { zodResolver } from "@hookform/resolvers/zod"
import { useMutation, useQueryClient } from "@tanstack/react-query"
import { AxiosError } from "axios"
import { KeyRound, LoaderCircle, TriangleAlert } from "lucide-react"
import { useForm } from "react-hook-form"
import { toast } from "sonner"
import type { AdminUserDetail } from "@/entities/user/model/types"
import { accountApi } from "@/features/manage-accounts/api/account-api"
import { useProtectedQueryScope } from "@/features/auth/model/use-protected-query-scope"
import { invalidateQueries } from "@/shared/api/query-invalidation"
import { queryKeys } from "@/shared/api/query-keys"
import { setPasswordSchema, type SetPasswordValues } from "@/features/manage-accounts/schemas/set-password.schema"
import { Alert, AlertDescription, AlertTitle } from "@/shared/ui/alert"
import { Button } from "@/shared/ui/button"
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/shared/ui/dialog"
import { Input } from "@/shared/ui/input"
import { Label } from "@/shared/ui/label"
import { Switch } from "@/shared/ui/switch"

const defaults: SetPasswordValues = { new_password: "", confirm_password: "", invalidate_sessions: true, must_change_password: false }

export function AdminSetPasswordDialog({ user, open, onOpenChange }: { user: AdminUserDetail; open: boolean; onOpenChange: (open: boolean) => void }) {
  const queryClient = useQueryClient()
  const { queryScope } = useProtectedQueryScope()
  const form = useForm<SetPasswordValues>({ resolver: zodResolver(setPasswordSchema), defaultValues: defaults })
  const mutation = useMutation({
    mutationFn: (values: SetPasswordValues) => accountApi.setPassword(user.id, values),
    onSuccess: async () => {
      await Promise.all([
        invalidateQueries.users(queryClient, queryScope, user.id),
        queryClient.invalidateQueries({ queryKey: queryKeys.users.activity(queryScope, user.id), refetchType: "active" }),
      ])
      form.reset(defaults)
      onOpenChange(false)
      toast.success("Đã cập nhật mật khẩu thành công.")
    },
    onError: (error) => {
      const detail = error instanceof AxiosError ? (error.response?.data as { detail?: unknown } | undefined)?.detail : undefined
      toast.error(typeof detail === "string" ? detail : "Không thể cập nhật mật khẩu.")
    },
  })
  const statusWarning = user.status === "DISABLED"
    ? "Mật khẩu sẽ được cập nhật nhưng tài khoản vẫn đang bị vô hiệu hóa."
    : user.status === "LOCKED"
      ? "Mật khẩu sẽ được cập nhật nhưng tài khoản vẫn đang bị khóa."
      : null

  return (
    <Dialog open={open} onOpenChange={(next) => { if (mutation.isPending) return; onOpenChange(next); if (!next) form.reset(defaults) }}>
      <DialogContent>
        <DialogHeader><DialogTitle>Đặt lại mật khẩu</DialogTitle><DialogDescription>Tài khoản: {user.full_name}<br />Username: {user.username}</DialogDescription></DialogHeader>
        {statusWarning ? <Alert><TriangleAlert /><AlertTitle>Tài khoản chưa hoạt động</AlertTitle><AlertDescription>{statusWarning}</AlertDescription></Alert> : null}
        <form className="flex flex-col gap-5" onSubmit={form.handleSubmit((values) => mutation.mutate(values))}>
          <div className="flex flex-col gap-2" data-invalid={form.formState.errors.new_password ? "true" : undefined}>
            <Label htmlFor={`admin-new-password-${user.id}`}>Mật khẩu mới</Label>
            <Input id={`admin-new-password-${user.id}`} type="password" autoComplete="new-password" aria-invalid={!!form.formState.errors.new_password} {...form.register("new_password")} />
            {form.formState.errors.new_password ? <p className="text-xs text-destructive" role="alert">{form.formState.errors.new_password.message}</p> : null}
          </div>
          <div className="flex flex-col gap-2" data-invalid={form.formState.errors.confirm_password ? "true" : undefined}>
            <Label htmlFor={`admin-confirm-password-${user.id}`}>Xác nhận mật khẩu mới</Label>
            <Input id={`admin-confirm-password-${user.id}`} type="password" autoComplete="new-password" aria-invalid={!!form.formState.errors.confirm_password} {...form.register("confirm_password")} />
            {form.formState.errors.confirm_password ? <p className="text-xs text-destructive" role="alert">{form.formState.errors.confirm_password.message}</p> : null}
          </div>
          <div className="flex items-start gap-3"><Switch id={`must-change-${user.id}`} checked={form.watch("must_change_password")} onCheckedChange={(checked) => form.setValue("must_change_password", checked)} /><Label htmlFor={`must-change-${user.id}`}>Yêu cầu người dùng đổi mật khẩu khi đăng nhập lần tới</Label></div>
          <div className="flex items-start gap-3"><Switch id={`invalidate-${user.id}`} checked={form.watch("invalidate_sessions")} onCheckedChange={(checked) => form.setValue("invalidate_sessions", checked)} /><Label htmlFor={`invalidate-${user.id}`}>Đăng xuất khỏi tất cả thiết bị</Label></div>
          <DialogFooter><Button type="button" variant="outline" onClick={() => onOpenChange(false)}>Hủy</Button><Button type="submit" disabled={mutation.isPending}>{mutation.isPending ? <LoaderCircle data-icon="inline-start" className="animate-spin" /> : <KeyRound data-icon="inline-start" />}Cập nhật mật khẩu</Button></DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}
