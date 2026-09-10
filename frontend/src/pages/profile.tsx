import { useState, type FormEvent } from "react"
import { useMutation } from "@tanstack/react-query"
import { errorMessage } from "@/api/client"
import { changePassword, updateProfile } from "@/api/resources"
import { useAuth } from "@/app/auth"

export function ProfilePage() {
  const { session, reload } = useAuth()
  const [fullName, setFullName] = useState(session?.user.full_name ?? "")
  const [email, setEmail] = useState(session?.user.email ?? "")
  const [currentPassword, setCurrentPassword] = useState("")
  const [newPassword, setNewPassword] = useState("")
  const [confirmPassword, setConfirmPassword] = useState("")
  const profile = useMutation({ mutationFn: () => updateProfile({ full_name: fullName.trim(), email: email.trim() }), onSuccess: reload })
  const password = useMutation({ mutationFn: () => changePassword({ current_password: currentPassword, new_password: newPassword, confirm_password: confirmPassword }), onSuccess: () => { setCurrentPassword(""); setNewPassword(""); setConfirmPassword("") } })
  const submitProfile = (event: FormEvent) => { event.preventDefault(); profile.mutate() }
  const submitPassword = (event: FormEvent) => { event.preventDefault(); password.mutate() }
  return <section className="grid max-w-3xl gap-5 lg:grid-cols-2"><div className="space-y-4 rounded-xl border bg-card p-5"><h1 className="text-2xl font-bold">Hồ sơ người dùng</h1><p className="text-sm text-muted-foreground">{session?.user.username}</p><form className="space-y-3" onSubmit={submitProfile}><label className="block text-sm">Họ tên<input className="mt-1 w-full rounded border bg-background p-2" value={fullName} onChange={(event) => setFullName(event.target.value)} required /></label><label className="block text-sm">Email<input className="mt-1 w-full rounded border bg-background p-2" type="email" value={email} onChange={(event) => setEmail(event.target.value)} required /></label><button className="rounded bg-primary px-4 py-2 text-primary-foreground">Lưu hồ sơ</button>{profile.isError && <p className="text-sm text-destructive">{errorMessage(profile.error)}</p>}</form></div><div className="space-y-4 rounded-xl border bg-card p-5"><h2 className="text-xl font-semibold">Đổi mật khẩu</h2><form className="space-y-3" onSubmit={submitPassword}><label className="block text-sm">Mật khẩu hiện tại<input className="mt-1 w-full rounded border bg-background p-2" type="password" value={currentPassword} onChange={(event) => setCurrentPassword(event.target.value)} minLength={8} required /></label><label className="block text-sm">Mật khẩu mới<input className="mt-1 w-full rounded border bg-background p-2" type="password" value={newPassword} onChange={(event) => setNewPassword(event.target.value)} minLength={8} required /></label><label className="block text-sm">Xác nhận mật khẩu mới<input className="mt-1 w-full rounded border bg-background p-2" type="password" value={confirmPassword} onChange={(event) => setConfirmPassword(event.target.value)} minLength={8} required /></label><button className="rounded border px-4 py-2">Đổi mật khẩu</button>{password.isError && <p className="text-sm text-destructive">{errorMessage(password.error)}</p>}</form></div></section>
}
