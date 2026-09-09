import { useEffect, useState } from "react"
import { useMutation } from "@tanstack/react-query"
import { KeyRound, Save, UserRound } from "lucide-react"
import { useNavigate, useSearchParams } from "react-router-dom"
import { changePassword, updateProfile } from "@/api/resources"
import { errorMessage } from "@/api/client"
import { useAuth } from "@/app/auth"
import { Alert, AlertDescription, AlertTitle } from "@/shared/ui/alert"
import { Button } from "@/shared/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/shared/ui/card"
import { Input } from "@/shared/ui/input"
import { Label } from "@/shared/ui/label"
import { Textarea } from "@/shared/ui/textarea"

export function ProfilePage() {
  const { session, reload, logout } = useAuth()
  const navigate = useNavigate()
  const [params] = useSearchParams()
  const [fullName, setFullName] = useState("")
  const [email, setEmail] = useState("")
  const [phoneNumber, setPhoneNumber] = useState("")
  const [address, setAddress] = useState("")
  const [currentPassword, setCurrentPassword] = useState("")
  const [newPassword, setNewPassword] = useState("")
  const [confirmPassword, setConfirmPassword] = useState("")
  const [saved, setSaved] = useState(false)
  useEffect(() => { if (session?.user) { setFullName(session.user.full_name); setEmail(session.user.email); setPhoneNumber(session.user.phone_number); setAddress(session.user.address ?? "") } }, [session])
  const profile = useMutation({ mutationFn: () => updateProfile({ full_name: fullName.trim(), email: email.trim(), phone_number: phoneNumber.trim(), address: address.trim() }), onSuccess: async () => { await reload(); setSaved(true) } })
  const passwordMismatch = confirmPassword.length > 0 && newPassword !== confirmPassword
  const password = useMutation({ mutationFn: () => changePassword({ current_password: currentPassword, new_password: newPassword, confirm_password: confirmPassword }), onSuccess: async () => { await logout(); navigate("/login?password=changed", { replace: true }) } })
  const forced = session?.user.must_change_password || params.get("change-password") === "required"
  return <section className="grid max-w-4xl gap-5 lg:grid-cols-2">{forced ? <Alert className="lg:col-span-2"><KeyRound /><AlertTitle>Bạn cần đổi mật khẩu</AlertTitle><AlertDescription>Hoàn tất đổi mật khẩu trước khi truy cập các chức năng vận hành khác.</AlertDescription></Alert> : null}<Card><CardHeader><CardTitle className="flex items-center gap-2"><UserRound className="size-5 text-primary" />Hồ sơ người dùng</CardTitle></CardHeader><CardContent><p className="mb-4 text-sm text-muted-foreground">@{session?.user.username}</p><form className="space-y-3" onSubmit={(event) => { event.preventDefault(); profile.mutate() }}><TextField id="profile-name" label="Họ tên" value={fullName} onChange={setFullName} /><TextField id="profile-email" label="Email" value={email} type="email" onChange={setEmail} /><TextField id="profile-phone" label="Số điện thoại" value={phoneNumber} type="tel" onChange={setPhoneNumber} /><div><Label htmlFor="profile-address">Địa chỉ</Label><Textarea id="profile-address" className="mt-1" value={address} onChange={(event) => setAddress(event.target.value)} /></div><Button type="submit" disabled={profile.isPending}><Save />Lưu hồ sơ</Button>{saved ? <p role="status" className="text-sm text-emerald-700 dark:text-emerald-300">Đã lưu hồ sơ.</p> : null}{profile.isError ? <p role="alert" className="text-sm text-destructive">{errorMessage(profile.error)}</p> : null}</form></CardContent></Card><Card><CardHeader><CardTitle className="flex items-center gap-2"><KeyRound className="size-5 text-primary" />Đổi mật khẩu</CardTitle></CardHeader><CardContent><form className="space-y-3" onSubmit={(event) => { event.preventDefault(); password.mutate() }}><TextField id="current-password" label="Mật khẩu hiện tại" value={currentPassword} type="password" minLength={8} onChange={setCurrentPassword} /><TextField id="new-password" label="Mật khẩu mới" value={newPassword} type="password" minLength={8} onChange={setNewPassword} /><TextField id="confirm-password" label="Xác nhận mật khẩu mới" value={confirmPassword} type="password" minLength={8} onChange={setConfirmPassword} />{passwordMismatch ? <p role="alert" className="text-sm text-destructive">Mật khẩu xác nhận không khớp.</p> : null}<Button type="submit" variant="outline" disabled={password.isPending || passwordMismatch || newPassword.length < 8}><KeyRound />Đổi mật khẩu</Button>{password.isError ? <p role="alert" className="text-sm text-destructive">{errorMessage(password.error)}</p> : null}<p className="text-xs text-muted-foreground">Sau khi đổi mật khẩu, token hiện tại hết hiệu lực và bạn cần đăng nhập lại.</p></form></CardContent></Card></section>
}

function TextField({ id, label, value, type = "text", minLength, onChange }: { id: string; label: string; value: string; type?: string; minLength?: number; onChange: (value: string) => void }) { return <div><Label htmlFor={id}>{label}</Label><Input id={id} className="mt-1" type={type} minLength={minLength} value={value} onChange={(event) => onChange(event.target.value)} required /></div> }
