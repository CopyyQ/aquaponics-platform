import { useMemo, useState } from "react"
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { Plus, Search, Users } from "lucide-react"
import { Link } from "react-router-dom"
import { createManagedUser, listRoles, listUsers, queryKeys } from "@/api/resources"
import { errorMessage } from "@/api/client"
import { useAuth } from "@/app/auth"
import { Button } from "@/shared/ui/button"
import { Card, CardContent } from "@/shared/ui/card"
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/shared/ui/dialog"
import { EmptyState } from "@/shared/ui/empty-state"
import { Input } from "@/shared/ui/input"
import { Label } from "@/shared/ui/label"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/shared/ui/select"
import { Skeleton } from "@/shared/ui/skeleton"
import { StatusBadge } from "@/shared/ui/status-badge"
import { Switch } from "@/shared/ui/switch"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/shared/ui/table"
import { toast } from "sonner"

export function UsersPage() {
  const { can } = useAuth()
  const client = useQueryClient()
  const [search, setSearch] = useState("")
  const [creating, setCreating] = useState(false)
  const users = useQuery({ queryKey: queryKeys.users, queryFn: listUsers })
  const roles = useQuery({ queryKey: queryKeys.roles, queryFn: listRoles, enabled: can("users.create") })
  const filtered = useMemo(() => (users.data ?? []).filter((user) => `${user.full_name} ${user.username} ${user.email} ${user.role_name ?? user.role_code ?? ""}`.toLocaleLowerCase("vi").includes(search.toLocaleLowerCase("vi"))), [search, users.data])
  return <section className="space-y-5">
    <div className="flex flex-wrap items-start justify-between gap-3"><div><h1 className="text-3xl font-bold">Người dùng và RBAC</h1><p className="text-sm text-muted-foreground">Quản lý tài khoản bằng canonical Users API và quyền do session phát hành.</p></div>{can("users.create") ? <Button onClick={() => setCreating(true)}><Plus />Tạo tài khoản</Button> : null}</div>
    <label className="relative block max-w-xl"><span className="sr-only">Tìm người dùng</span><Search className="absolute left-3 top-2.5 size-4 text-muted-foreground" /><Input className="pl-9" placeholder="Tìm theo tên, username, email hoặc vai trò" value={search} onChange={(event) => setSearch(event.target.value)} /></label>
    {users.isLoading ? <Skeleton className="h-80" /> : users.isError ? <EmptyState icon={Users} title="Không thể tải người dùng" description={errorMessage(users.error)} /> : filtered.length ? <Card><CardContent className="overflow-x-auto p-0"><Table><TableHeader><TableRow><TableHead>Họ tên</TableHead><TableHead>Tên đăng nhập</TableHead><TableHead>Email</TableHead><TableHead>Vai trò</TableHead><TableHead>Trạng thái</TableHead></TableRow></TableHeader><TableBody>{filtered.map((user) => <TableRow key={user.id}><TableCell><Link className="font-medium text-primary hover:underline" to={`/users/${user.id}`}>{user.full_name}</Link></TableCell><TableCell>{user.username}</TableCell><TableCell>{user.email}</TableCell><TableCell>{user.role_name ?? user.role_code ?? "Chưa gán"}</TableCell><TableCell><StatusBadge value={user.status} /></TableCell></TableRow>)}</TableBody></Table></CardContent></Card> : <EmptyState icon={Users} title={users.data?.length ? "Không tìm thấy người dùng" : "Chưa có người dùng"} description={users.data?.length ? "Thử một từ khoá khác." : "API không trả về tài khoản nào."} />}
    <CreateUserDialog open={creating} onOpenChange={setCreating} roles={roles.data ?? []} onCreated={async () => { await client.invalidateQueries({ queryKey: queryKeys.users }) }} />
  </section>
}

function CreateUserDialog({ open, onOpenChange, roles, onCreated }: { open: boolean; onOpenChange: (v: boolean) => void; roles: { id: number; name: string; code: string }[]; onCreated: () => Promise<void> }) {
  const [username, setUsername] = useState("")
  const [fullName, setFullName] = useState("")
  const [email, setEmail] = useState("")
  const [phone, setPhone] = useState("")
  const [address, setAddress] = useState("")
  const [roleId, setRoleId] = useState<string>("")
  const [password, setPassword] = useState("")
  const [confirm, setConfirm] = useState("")
  const [mustChange, setMustChange] = useState(true)
  const mutation = useMutation({
    mutationFn: () => createManagedUser({ username: username.trim(), full_name: fullName.trim(), email: email.trim(), phone_number: phone.trim(), address: address.trim(), role_id: roleId ? Number(roleId) : null, password, confirm_password: confirm, must_change_password: mustChange }),
    onSuccess: async () => { await onCreated(); toast.success("Đã tạo tài khoản"); onOpenChange(false) },
    onError: (error) => toast.error(errorMessage(error)),
  })
  const valid = username.trim() && fullName.trim() && email.trim() && phone.trim() && password.length >= 8 && password === confirm
  return <Dialog open={open} onOpenChange={onOpenChange}><DialogContent className="sm:max-w-2xl"><DialogHeader><DialogTitle>Tạo tài khoản</DialogTitle><DialogDescription>Tạo người dùng mới và gán vai trò canonical.</DialogDescription></DialogHeader><div className="grid gap-4 sm:grid-cols-2">
    <Field id="new-username" label="Tên đăng nhập" value={username} onChange={setUsername} />
    <Field id="new-fullname" label="Họ tên" value={fullName} onChange={setFullName} />
    <Field id="new-email" label="Email" type="email" value={email} onChange={setEmail} />
    <Field id="new-phone" label="Số điện thoại" value={phone} onChange={setPhone} />
    <Field id="new-address" label="Địa chỉ" value={address} onChange={setAddress} required={false} />
    <div><Label>Vai trò</Label><Select value={roleId} onValueChange={setRoleId}><SelectTrigger className="mt-1"><SelectValue placeholder="Chọn vai trò" /></SelectTrigger><SelectContent>{roles.map((role) => <SelectItem value={String(role.id)} key={role.id}>{role.name} ({role.code})</SelectItem>)}</SelectContent></Select></div>
    <Field id="new-password" label="Mật khẩu" type="password" value={password} onChange={setPassword} />
    <Field id="new-confirm" label="Xác nhận mật khẩu" type="password" value={confirm} onChange={setConfirm} />
    <div className="flex items-center justify-between gap-3 rounded-lg border p-3 sm:col-span-2"><div><p className="font-medium">Yêu cầu đổi mật khẩu lần đầu</p><p className="text-xs text-muted-foreground">Người dùng sẽ được chuyển tới trang đổi mật khẩu sau đăng nhập.</p></div><Switch checked={mustChange} onCheckedChange={setMustChange} /></div>
  </div><DialogFooter><Button variant="outline" onClick={() => onOpenChange(false)}>Huỷ</Button><Button disabled={!valid || mutation.isPending} onClick={() => mutation.mutate()}>Tạo tài khoản</Button></DialogFooter></DialogContent></Dialog>
}

function Field({ id, label, value, onChange, type = "text", required = true }: { id: string; label: string; value: string; onChange: (v: string) => void; type?: string; required?: boolean }) { return <div><Label htmlFor={id}>{label}</Label><Input id={id} className="mt-1" type={type} required={required} value={value} onChange={(event) => onChange(event.target.value)} /></div> }
