import { useState } from "react"
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { ArrowLeft, KeyRound, LogOut, UserRound } from "lucide-react"
import { Link, useParams } from "react-router-dom"
import { forceLogoutUser, getUser, listRoles, queryKeys, setManagedUserPassword, updateManagedUser, userLifecycle } from "@/api/resources"
import { errorMessage } from "@/api/client"
import { useAuth } from "@/app/auth"
import { Button } from "@/shared/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/shared/ui/card"
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/shared/ui/dialog"
import { EmptyState } from "@/shared/ui/empty-state"
import { Input } from "@/shared/ui/input"
import { Label } from "@/shared/ui/label"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/shared/ui/select"
import { Skeleton } from "@/shared/ui/skeleton"
import { StatusBadge } from "@/shared/ui/status-badge"
import { toast } from "sonner"

export function UserDetailPage() {
  const userId = Number(useParams().userId)
  const validId = userId > 0
  const { can } = useAuth()
  const client = useQueryClient()
  const [passwordOpen, setPasswordOpen] = useState(false)
  const user = useQuery({ queryKey: queryKeys.user(userId), queryFn: () => getUser(userId), enabled: validId })
  const roles = useQuery({ queryKey: queryKeys.roles, queryFn: listRoles, enabled: validId && can("users.update") })
  const refresh = async () => { await Promise.all([client.invalidateQueries({ queryKey: queryKeys.user(userId) }), client.invalidateQueries({ queryKey: queryKeys.users })]) }
  const lifecycle = useMutation({ mutationFn: ({ action, reason }: { action: "activate" | "disable" | "lock" | "unlock" | "restore" | "soft-delete"; reason?: string }) => userLifecycle(userId, action, { reason }), onSuccess: async (value) => { await refresh(); toast.success(value.message) }, onError: (error) => toast.error(errorMessage(error)) })
  const forceLogout = useMutation({ mutationFn: () => forceLogoutUser(userId), onSuccess: (value) => toast.success(value.message), onError: (error) => toast.error(errorMessage(error)) })
  if (!validId) return <EmptyState icon={UserRound} title="Đường dẫn người dùng không hợp lệ" description="User ID phải là số nguyên dương." />
  if (user.isLoading) return <Skeleton className="h-72" />
  if (user.isError || !user.data) return <EmptyState icon={UserRound} title="Không thể tải người dùng" description={errorMessage(user.error)} />
  const value = user.data
  const runLifecycle = (action: "activate" | "disable" | "lock" | "unlock" | "restore" | "soft-delete", needsReason = false) => {
    const reason = needsReason ? window.prompt("Nhập lý do (tuỳ chọn):") : undefined
    if (needsReason && reason === null) return
    lifecycle.mutate({ action, reason: reason || undefined })
  }
  return <div className="max-w-4xl space-y-5"><Link className="inline-flex items-center gap-2 text-sm text-primary hover:underline" to="/users"><ArrowLeft className="size-4" />Danh sách người dùng</Link><div className="flex flex-wrap items-start justify-between gap-3"><div><h1 className="text-3xl font-bold">{value.full_name}</h1><p className="text-muted-foreground">@{value.username}</p></div><StatusBadge value={value.status} /></div>
    <Card><CardHeader><CardTitle>Thông tin tài khoản</CardTitle></CardHeader><CardContent className="grid gap-4 sm:grid-cols-2"><Field label="Email" value={value.email} /><Field label="Số điện thoại" value={value.phone_number || "Chưa cấu hình"} /><Field label="Vai trò" value={value.role_name ?? value.role_code ?? "Chưa gán"} /><Field label="Ngày tạo" value={new Date(value.created_at).toLocaleString("vi-VN")} />{can("users.update") ? <div className="sm:col-span-2"><Label>Vai trò</Label><Select value={value.role_id ? String(value.role_id) : "none"} onValueChange={(next) => { updateManagedUser(userId, { role_id: next === "none" ? null : Number(next) }).then(refresh).catch((e) => toast.error(errorMessage(e))) }}><SelectTrigger className="mt-1 max-w-sm"><SelectValue /></SelectTrigger><SelectContent><SelectItem value="none">Chưa gán</SelectItem>{(roles.data ?? []).map((role) => <SelectItem value={String(role.id)} key={role.id}>{role.name} ({role.code})</SelectItem>)}</SelectContent></Select></div> : null}</CardContent></Card>
    <Card><CardHeader><CardTitle>Quản trị & bảo mật</CardTitle></CardHeader><CardContent className="flex flex-wrap gap-2">{can("users.set_password") ? <Button variant="outline" onClick={() => setPasswordOpen(true)}><KeyRound />Đặt mật khẩu</Button> : null}{can("users.force_logout") ? <Button variant="outline" onClick={() => forceLogout.mutate()} disabled={forceLogout.isPending}><LogOut />Thu hồi phiên</Button> : null}{value.status !== "ACTIVE" && can("users.update") ? <Button onClick={() => runLifecycle(value.status === "SOFT_DELETED" ? "restore" : value.status === "LOCKED" ? "unlock" : "activate")}>Kích hoạt</Button> : null}{value.status === "ACTIVE" && can("users.lock") ? <Button variant="outline" onClick={() => runLifecycle("lock", true)}>Khoá</Button> : null}{value.status === "ACTIVE" && can("users.update") ? <Button variant="outline" onClick={() => runLifecycle("disable", true)}>Vô hiệu hoá</Button> : null}{value.status !== "SOFT_DELETED" && can("users.delete") ? <Button variant="destructive" onClick={() => { if (window.confirm("Xoá mềm tài khoản này?")) runLifecycle("soft-delete", true) }}>Xoá mềm</Button> : null}</CardContent></Card>
    <PasswordDialog userId={userId} open={passwordOpen} onOpenChange={setPasswordOpen} />
  </div>
}

function PasswordDialog({ userId, open, onOpenChange }: { userId: number; open: boolean; onOpenChange: (v: boolean) => void }) {
  const [password, setPassword] = useState("")
  const [confirm, setConfirm] = useState("")
  const mutation = useMutation({ mutationFn: () => setManagedUserPassword(userId, { new_password: password, confirm_password: confirm, invalidate_sessions: true, must_change_password: true }), onSuccess: (value) => { toast.success(value.message); onOpenChange(false) }, onError: (error) => toast.error(errorMessage(error)) })
  return <Dialog open={open} onOpenChange={onOpenChange}><DialogContent><DialogHeader><DialogTitle>Đặt mật khẩu mới</DialogTitle><DialogDescription>Mật khẩu mới sẽ buộc người dùng đổi lại sau lần đăng nhập kế tiếp.</DialogDescription></DialogHeader><div className="space-y-3"><div><Label htmlFor="managed-password">Mật khẩu</Label><Input id="managed-password" className="mt-1" type="password" value={password} onChange={(e) => setPassword(e.target.value)} /></div><div><Label htmlFor="managed-confirm">Xác nhận</Label><Input id="managed-confirm" className="mt-1" type="password" value={confirm} onChange={(e) => setConfirm(e.target.value)} /></div></div><DialogFooter><Button variant="outline" onClick={() => onOpenChange(false)}>Huỷ</Button><Button disabled={password.length < 8 || password !== confirm || mutation.isPending} onClick={() => mutation.mutate()}>Lưu mật khẩu</Button></DialogFooter></DialogContent></Dialog>
}
function Field({ label, value }: { label: string; value: string }) { return <div><p className="text-xs text-muted-foreground">{label}</p><p className="mt-1 font-medium">{value}</p></div> }
