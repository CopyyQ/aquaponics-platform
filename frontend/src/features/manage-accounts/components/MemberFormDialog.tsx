import { useState } from "react"
import { useForm } from "react-hook-form"
import { zodResolver } from "@hookform/resolvers/zod"
import { z } from "zod"
import { useMutation, useQueryClient } from "@tanstack/react-query"
import { UserPlus } from "lucide-react"
import { toast } from "sonner"
import { userApi } from "@/entities/user/api/user-api"
import type { User, UserRole } from "@/entities/user/model/types"
import { useProtectedQueryScope } from "@/features/auth/model/use-protected-query-scope"
import { invalidateQueries } from "@/shared/api/query-invalidation"
import { queryKeys } from "@/shared/api/query-keys"
import { Button } from "@/shared/ui/button"
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle, DialogTrigger } from "@/shared/ui/dialog"
import { Input } from "@/shared/ui/input"
import { Label } from "@/shared/ui/label"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/shared/ui/select"
import { Textarea } from "@/shared/ui/textarea"

const schema = z.object({ username: z.string().min(3), temporary_password: z.string().min(8), full_name: z.string().min(2), email: z.string().email(), phone_number: z.string().min(8), address: z.string(), system_role: z.enum(["ADMIN", "OWNER", "VIEWER"]) })
type Values = z.infer<typeof schema>

export function MemberFormDialog({ actorRole }: { actorRole: UserRole }) {
  const [open, setOpen] = useState(false)
  const queryClient = useQueryClient()
  const { queryScope } = useProtectedQueryScope()
  const { register, handleSubmit, setValue, reset } = useForm<Values>({ resolver: zodResolver(schema), defaultValues: { address: "", system_role: "VIEWER" } })
  const mutation = useMutation({ mutationFn: userApi.create, onSuccess: async (user) => { queryClient.setQueryData<User[]>(queryKeys.users.members, (current) => current ? [user, ...current.filter((item) => item.id !== user.id)] : current); await invalidateQueries.users(queryClient, queryScope, user.id); reset(); setOpen(false); toast.success("Đã tạo tài khoản") }, onError: () => toast.error("Không thể tạo tài khoản") })
  return <Dialog open={open} onOpenChange={setOpen}><DialogTrigger asChild><Button><UserPlus /> Thêm thành viên</Button></DialogTrigger><DialogContent className="max-w-xl"><DialogHeader><DialogTitle>Tạo tài khoản</DialogTitle><DialogDescription>Tài khoản mới phải đổi mật khẩu trong lần đăng nhập đầu tiên.</DialogDescription></DialogHeader><form className="space-y-4" onSubmit={handleSubmit((values) => mutation.mutate(values))}><div className="grid gap-4 sm:grid-cols-2"><div className="space-y-2"><Label>Tên đăng nhập</Label><Input {...register("username")} /></div><div className="space-y-2"><Label>Mật khẩu tạm thời</Label><Input type="password" {...register("temporary_password")} /></div><div className="space-y-2"><Label>Họ tên</Label><Input {...register("full_name")} /></div><div className="space-y-2"><Label>Email</Label><Input type="email" {...register("email")} /></div><div className="space-y-2"><Label>Số điện thoại</Label><Input {...register("phone_number")} /></div><div className="space-y-2"><Label>Vai trò</Label><Select defaultValue="VIEWER" onValueChange={(value) => setValue("system_role", value as UserRole)}><SelectTrigger><SelectValue /></SelectTrigger><SelectContent>{actorRole === "ADMIN" && <><SelectItem value="ADMIN">Quản trị viên</SelectItem><SelectItem value="OWNER">Chủ hệ thống</SelectItem></>}<SelectItem value="VIEWER">Người xem</SelectItem></SelectContent></Select></div></div><div className="space-y-2"><Label>Địa chỉ</Label><Textarea {...register("address")} /></div><DialogFooter><Button type="button" variant="outline" onClick={() => setOpen(false)}>Hủy</Button><Button type="submit" disabled={mutation.isPending}>Tạo tài khoản</Button></DialogFooter></form></DialogContent></Dialog>
}
