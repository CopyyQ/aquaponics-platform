import { useState } from "react"
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { ArrowLeft, ExternalLink, KeyRound, LogOut, Plus, Settings, UserRound } from "lucide-react"
import { Link, useParams } from "react-router-dom"
import {
  createUserAquaponicsSystem, forceLogoutUser, getUser, listRoles,
  listUserAquaponicsSystems, queryKeys, setManagedUserPassword, updateManagedUser, userLifecycle,
} from "@/api/resources"
import type { UserStatus } from "@/api/contracts"
import { errorMessage } from "@/api/client"
import { useAuth } from "@/app/auth"
import { Button } from "@/shared/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/shared/ui/card"
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/shared/ui/dialog"
import { AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle } from "@/shared/ui/alert-dialog"
import { EmptyState } from "@/shared/ui/empty-state"
import { Input } from "@/shared/ui/input"
import { Label } from "@/shared/ui/label"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/shared/ui/select"
import { Skeleton } from "@/shared/ui/skeleton"
import { StatusBadge } from "@/shared/ui/status-badge"
import { toast } from "sonner"

type LifecycleAction = "activate" | "disable" | "lock" | "unlock" | "restore" | "soft-delete"
type Confirmation = { action: LifecycleAction; title: string } | null

export function UserDetailPage() {
  const userId = useParams().userId ?? ""
  const validId = Boolean(userId)
  const { can, session } = useAuth()
  const client = useQueryClient()
  const [manageOpen, setManageOpen] = useState(false)
  const [passwordOpen, setPasswordOpen] = useState(false)
  const [confirmation, setConfirmation] = useState<Confirmation>(null)
  const [reason, setReason] = useState("")
  const user = useQuery({ queryKey: queryKeys.user(userId), queryFn: () => getUser(userId), enabled: validId })
  const roles = useQuery({ queryKey: queryKeys.roles, queryFn: listRoles, enabled: validId && can("users.update") })
  const refreshUser = async () => { await Promise.all([client.invalidateQueries({ queryKey: queryKeys.user(userId) }), client.invalidateQueries({ queryKey: queryKeys.users })]) }
  const lifecycle = useMutation({ mutationFn: ({ action, reason: why }: { action: LifecycleAction; reason?: string }) => userLifecycle(userId, action, { reason: why }), onSuccess: async (value) => { await refreshUser(); setConfirmation(null); setReason(""); toast.success(value.message) }, onError: (error) => toast.error(errorMessage(error)) })
  const forceLogout = useMutation({ mutationFn: () => forceLogoutUser(userId), onSuccess: (value) => toast.success(value.message), onError: (error) => toast.error(errorMessage(error)) })
  const confirm = (action: LifecycleAction, title: string) => { setManageOpen(false); setConfirmation({ action, title }) }
  if (!validId) return <EmptyState icon={UserRound} title="Đường dẫn người dùng không hợp lệ" description="Mã người dùng phải là số nguyên dương." />
  if (user.isLoading) return <div className="space-y-5"><Skeleton className="h-20" /><Skeleton className="h-64" /><Skeleton className="h-64" /></div>
  if (user.isError || !user.data) return <EmptyState icon={UserRound} title="Không thể tải người dùng" description={errorMessage(user.error)} />
  const value = user.data
  const isSelf = session?.user.id === value.id
  return <div className="mx-auto max-w-5xl space-y-5">
    <Link className="inline-flex items-center gap-2 text-sm text-primary hover:underline" to="/users"><ArrowLeft className="size-4" />Danh sách người dùng</Link>
    <header className="flex flex-wrap items-start justify-between gap-3"><div><h1 className="text-balance text-3xl font-bold">{value.full_name}</h1><p className="text-muted-foreground">@{value.username}</p></div><StatusBadge value={value.status} /></header>
    <Card><CardHeader className="flex-row items-center justify-between gap-3"><CardTitle className="text-balance">Thông tin tài khoản</CardTitle>{can("users.update") || can("users.set_password") ? <Button variant="outline" onClick={() => setManageOpen(true)}><Settings />Quản lý tài khoản</Button> : null}</CardHeader><CardContent className="grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
      <Field label="Email" value={value.email} /><Field label="Số điện thoại" value={value.phone_number || "Chưa cấu hình"} />
      <div><Label>Vai trò tài khoản</Label>{can("users.update") ? <Select value={value.role_id ? String(value.role_id) : "none"} onValueChange={(next) => { void updateManagedUser(userId, { role_id: next === "none" ? null : Number(next) }).then(refreshUser).catch((e: unknown) => toast.error(errorMessage(e))) }}><SelectTrigger className="mt-1"><SelectValue /></SelectTrigger><SelectContent><SelectItem value="none">Chưa gán</SelectItem>{(roles.data ?? []).map((role) => <SelectItem value={String(role.id)} key={role.id}>{role.name} ({role.code})</SelectItem>)}</SelectContent></Select> : <p className="mt-1 font-medium">{value.role_name ?? value.role_code ?? "Chưa gán"}</p>}</div>
      <Field label="Ngày tạo" value={formatDate(value.created_at)} /><Field label="Lần đăng nhập cuối" value={formatDate(value.last_login_at)} />
    </CardContent></Card>
    <UserAquaponicsSystems userId={userId} canManage={can("aquaponics_systems.manage_all")} />
    <ManageAccountDialog open={manageOpen} onOpenChange={setManageOpen} status={value.status} isSelf={isSelf} can={can} onPassword={() => { setManageOpen(false); setPasswordOpen(true) }} onForceLogout={() => forceLogout.mutate()} onConfirm={confirm} pending={forceLogout.isPending} />
    <PasswordDialog userId={userId} open={passwordOpen} onOpenChange={setPasswordOpen} />
    <AlertDialog open={Boolean(confirmation)} onOpenChange={(open) => { if (!open) { setConfirmation(null); setReason("") } }}><AlertDialogContent><AlertDialogHeader><AlertDialogTitle>{confirmation?.title}</AlertDialogTitle><AlertDialogDescription>Thao tác sẽ thay đổi quyền truy cập của tài khoản. Hãy nhập lý do để lưu cùng lịch sử quản trị.</AlertDialogDescription></AlertDialogHeader><div><Label htmlFor="lifecycle-reason">Lý do</Label><Input id="lifecycle-reason" className="mt-1" value={reason} onChange={(event) => setReason(event.target.value)} /></div><AlertDialogFooter><AlertDialogCancel>Hủy</AlertDialogCancel><AlertDialogAction variant={confirmation?.action === "soft-delete" ? "destructive" : "default"} disabled={lifecycle.isPending || reason.trim().length < 3} onClick={(event) => { event.preventDefault(); if (confirmation) lifecycle.mutate({ action: confirmation.action, reason: reason.trim() }) }}>Xác nhận</AlertDialogAction></AlertDialogFooter></AlertDialogContent></AlertDialog>
  </div>
}

function UserAquaponicsSystems({ userId, canManage }: { userId: string; canManage: boolean }) {
  const client = useQueryClient()
  const [createOpen, setCreateOpen] = useState(false)
  const [name, setName] = useState("")
  const systems = useQuery({ queryKey: queryKeys.userSystems(userId), queryFn: () => listUserAquaponicsSystems(userId) })
  const refresh = async () => { await Promise.all([client.invalidateQueries({ queryKey: queryKeys.userSystems(userId) }), client.invalidateQueries({ queryKey: queryKeys.systems })]) }
  const creation = useMutation({ mutationFn: () => createUserAquaponicsSystem(userId, name.trim()), onSuccess: async () => { await refresh(); setCreateOpen(false); setName(""); toast.success("Đã tạo Hệ thống Aquaponics") }, onError: (error) => toast.error(errorMessage(error)) })
  return <Card><CardHeader className="flex-row items-center justify-between gap-3"><CardTitle className="text-balance">Hệ thống Aquaponics sở hữu</CardTitle>{canManage ? <Button onClick={() => setCreateOpen(true)}><Plus />Thêm Hệ thống Aquaponics</Button> : null}</CardHeader><CardContent>
    {systems.isLoading ? <Skeleton className="h-36" /> : systems.isError ? <EmptyState icon={UserRound} title="Không thể tải Hệ thống Aquaponics" description={errorMessage(systems.error)} /> : systems.data?.length ? <div className="grid gap-3 sm:grid-cols-2">{systems.data.map((system) => <article key={system.id} className="rounded-lg border p-4"><div className="flex items-start justify-between gap-3"><div className="min-w-0"><h3 className="text-pretty font-semibold">{system.name}</h3><p className="mt-1 text-sm text-muted-foreground">Mã hệ thống: <span className="font-mono">{system.code}</span></p></div><StatusBadge value={system.status} /></div><p className="mt-3 text-sm font-medium">Chủ hệ thống</p><div className="mt-4"><Button asChild size="sm" variant="outline"><Link to={`/aquaponics-systems/${system.id}`}><ExternalLink />Xem hệ thống</Link></Button></div></article>)}</div> : <EmptyState icon={UserRound} title="Chưa sở hữu Hệ thống Aquaponics" description="Tạo Hệ thống Aquaponics đầu tiên cho tài khoản này." />}
    <Dialog open={createOpen} onOpenChange={setCreateOpen}><DialogContent><DialogHeader><DialogTitle>Thêm Hệ thống Aquaponics</DialogTitle><DialogDescription>Mã hệ thống sẽ được tạo tự động và tài khoản này sẽ là chủ sở hữu.</DialogDescription></DialogHeader><form className="space-y-4" onSubmit={(event) => { event.preventDefault(); creation.mutate() }}><div><Label htmlFor="owned-system-name">Tên hệ thống</Label><Input id="owned-system-name" className="mt-1" value={name} onChange={(event) => setName(event.target.value)} required minLength={2} maxLength={255} autoFocus /></div>{creation.isError ? <p role="alert" className="text-sm text-destructive">{errorMessage(creation.error)}</p> : null}<DialogFooter><Button type="button" variant="outline" onClick={() => setCreateOpen(false)}>Hủy</Button><Button type="submit" disabled={name.trim().length < 2 || creation.isPending}>Tạo hệ thống</Button></DialogFooter></form></DialogContent></Dialog>
  </CardContent></Card>
}

function ManageAccountDialog({ open, onOpenChange, status, isSelf, can, onPassword, onForceLogout, onConfirm, pending }: { open: boolean; onOpenChange: (open: boolean) => void; status: UserStatus; isSelf: boolean; can: (permission: string) => boolean; onPassword: () => void; onForceLogout: () => void; onConfirm: (action: LifecycleAction, title: string) => void; pending: boolean }) {
  return <Dialog open={open} onOpenChange={onOpenChange}><DialogContent><DialogHeader><DialogTitle>Quản lý tài khoản</DialogTitle><DialogDescription>Chỉ các thao tác phù hợp với trạng thái hiện tại được hiển thị.</DialogDescription></DialogHeader><div className="grid gap-2 sm:grid-cols-2">{can("users.set_password") ? <Button variant="outline" onClick={onPassword}><KeyRound />Đặt mật khẩu</Button> : null}{can("users.force_logout") ? <Button variant="outline" onClick={onForceLogout} disabled={pending}><LogOut />Thu hồi phiên đăng nhập</Button> : null}{status === "ACTIVE" && can("users.lock") && !isSelf ? <Button variant="outline" onClick={() => onConfirm("lock", "Khóa tài khoản?")}>Khóa</Button> : null}{status === "LOCKED" && can("users.unlock") ? <Button onClick={() => onConfirm("unlock", "Mở khóa tài khoản?")}>Mở khóa</Button> : null}{status === "ACTIVE" && can("users.update") && !isSelf ? <Button variant="outline" onClick={() => onConfirm("disable", "Vô hiệu hóa tài khoản?")}>Vô hiệu hóa</Button> : null}{status === "DISABLED" && can("users.update") ? <Button onClick={() => onConfirm("activate", "Kích hoạt tài khoản?")}>Kích hoạt</Button> : null}{status !== "SOFT_DELETED" && can("users.delete") && !isSelf ? <Button variant="destructive" onClick={() => onConfirm("soft-delete", "Xóa mềm tài khoản?")}>Xóa mềm</Button> : null}{status === "SOFT_DELETED" && can("users.update") ? <Button onClick={() => onConfirm("restore", "Khôi phục tài khoản?")}>Khôi phục</Button> : null}</div><DialogFooter><Button variant="outline" onClick={() => onOpenChange(false)}>Đóng</Button></DialogFooter></DialogContent></Dialog>
}

function PasswordDialog({ userId, open, onOpenChange }: { userId: string; open: boolean; onOpenChange: (open: boolean) => void }) {
  const [password, setPassword] = useState("")
  const [confirm, setConfirm] = useState("")
  const mutation = useMutation({ mutationFn: () => setManagedUserPassword(userId, { new_password: password, confirm_password: confirm, invalidate_sessions: true, must_change_password: true }), onSuccess: (value) => { toast.success(value.message); onOpenChange(false); setPassword(""); setConfirm("") }, onError: (error) => toast.error(errorMessage(error)) })
  return <Dialog open={open} onOpenChange={onOpenChange}><DialogContent><DialogHeader><DialogTitle>Đặt mật khẩu</DialogTitle><DialogDescription>Người dùng sẽ phải đổi mật khẩu sau lần đăng nhập kế tiếp.</DialogDescription></DialogHeader><div className="space-y-3"><div><Label htmlFor="managed-password">Mật khẩu mới</Label><Input id="managed-password" className="mt-1" type="password" value={password} onChange={(event) => setPassword(event.target.value)} /></div><div><Label htmlFor="managed-confirm">Xác nhận mật khẩu</Label><Input id="managed-confirm" className="mt-1" type="password" value={confirm} onChange={(event) => setConfirm(event.target.value)} /></div></div><DialogFooter><Button variant="outline" onClick={() => onOpenChange(false)}>Hủy</Button><Button disabled={password.length < 8 || password !== confirm || mutation.isPending} onClick={() => mutation.mutate()}>Lưu mật khẩu</Button></DialogFooter></DialogContent></Dialog>
}

function Field({ label, value }: { label: string; value: string }) { return <div><p className="text-sm text-muted-foreground">{label}</p><p className="mt-1 font-medium tabular-nums">{value}</p></div> }
function formatDate(value: string | null) { return value ? new Date(value).toLocaleString("vi-VN") : "Chưa có" }
