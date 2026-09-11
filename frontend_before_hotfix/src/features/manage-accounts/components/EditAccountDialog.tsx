import { zodResolver } from "@hookform/resolvers/zod"
import { useMutation, useQueryClient } from "@tanstack/react-query"
import { LoaderCircle, Save } from "lucide-react"
import { useForm } from "react-hook-form"
import { toast } from "sonner"
import { z } from "zod"
import type { AdminUserDetail, UserRole } from "@/entities/user/model/types"
import { accountApi } from "@/features/manage-accounts/api/account-api"
import { useProtectedQueryScope } from "@/features/auth/model/use-protected-query-scope"
import { invalidateQueries } from "@/shared/api/query-invalidation"
import { queryKeys } from "@/shared/api/query-keys"
import { Button } from "@/shared/ui/button"
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/shared/ui/dialog"
import { Input } from "@/shared/ui/input"
import { Label } from "@/shared/ui/label"
import { Select, SelectContent, SelectGroup, SelectItem, SelectTrigger, SelectValue } from "@/shared/ui/select"

const editSchema = z.object({
  full_name: z.string().trim().min(2, "Họ và tên tối thiểu 2 ký tự").max(255),
  email: z.string().trim().toLowerCase().email("Email không đúng định dạng"),
  phone_number: z.string().trim().regex(/^\+?[0-9]{8,15}$/, "Số điện thoại không hợp lệ"),
  address: z.string().trim().max(2000),
  system_role: z.enum(["ADMIN", "OWNER", "VIEWER"]),
})
type EditValues = z.infer<typeof editSchema>

export function EditAccountDialog({ user, open, onOpenChange }: { user: AdminUserDetail; open: boolean; onOpenChange: (open: boolean) => void }) {
  const queryClient = useQueryClient()
  const { queryScope } = useProtectedQueryScope()
  const form = useForm<EditValues>({ resolver: zodResolver(editSchema), values: { full_name: user.full_name, email: user.email, phone_number: user.phone_number, address: user.address, system_role: user.system_role } })
  const mutation = useMutation({ mutationFn: (values: EditValues) => accountApi.update(user.id, values), onSuccess: async (updatedUser) => { queryClient.setQueryData(queryKeys.users.detail(queryScope, user.id), updatedUser); await invalidateQueries.users(queryClient, queryScope, user.id); onOpenChange(false); toast.success("Đã cập nhật tài khoản.") }, onError: () => toast.error("Không thể cập nhật tài khoản.") })
  const input = (name: "full_name" | "email" | "phone_number" | "address", label: string, type = "text") => <div className="flex flex-col gap-2"><Label htmlFor={`edit-${name}-${user.id}`}>{label}</Label><Input id={`edit-${name}-${user.id}`} type={type} aria-invalid={!!form.formState.errors[name]} {...form.register(name)} />{form.formState.errors[name] ? <p className="text-xs text-destructive" role="alert">{form.formState.errors[name]?.message}</p> : null}</div>
  return <Dialog open={open} onOpenChange={onOpenChange}><DialogContent><DialogHeader><DialogTitle>Chỉnh sửa tài khoản</DialogTitle><DialogDescription>Cập nhật thông tin của @{user.username}. Trạng thái được quản lý bằng thao tác riêng.</DialogDescription></DialogHeader><form className="flex flex-col gap-4" onSubmit={form.handleSubmit((values) => mutation.mutate(values))}><div className="grid gap-4 sm:grid-cols-2">{input("full_name", "Họ và tên")}{input("email", "Email", "email")}{input("phone_number", "Số điện thoại", "tel")}{input("address", "Địa chỉ")}<div className="flex flex-col gap-2 sm:col-span-2"><Label htmlFor={`edit-role-${user.id}`}>Vai trò</Label><Select value={form.watch("system_role")} onValueChange={(value) => form.setValue("system_role", value as UserRole)}><SelectTrigger id={`edit-role-${user.id}`}><SelectValue /></SelectTrigger><SelectContent><SelectGroup><SelectItem value="ADMIN">Quản trị viên</SelectItem><SelectItem value="OWNER">Chủ dự án</SelectItem><SelectItem value="VIEWER">Người xem</SelectItem></SelectGroup></SelectContent></Select></div></div><DialogFooter><Button type="button" variant="outline" onClick={() => onOpenChange(false)}>Hủy</Button><Button type="submit" disabled={mutation.isPending}>{mutation.isPending ? <LoaderCircle data-icon="inline-start" className="animate-spin" /> : <Save data-icon="inline-start" />}Lưu thay đổi</Button></DialogFooter></form></DialogContent></Dialog>
}
