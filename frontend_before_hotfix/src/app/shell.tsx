import { Link, NavLink, Outlet } from "react-router-dom"
import { useAuth } from "./auth"

export function Shell() {
  const { session, logout, has } = useAuth()
  const itemClass = ({ isActive }: { isActive: boolean }) => `rounded-lg px-3 py-2 ${isActive ? "bg-primary text-primary-foreground" : "hover:bg-muted"}`
  return <div className="min-h-screen bg-background text-foreground">
    <header className="border-b bg-card"><div className="mx-auto flex max-w-7xl items-center gap-5 px-4 py-3"><Link className="font-bold" to="/aquaponics-systems">Aquaponics Platform</Link><nav className="flex flex-1 gap-2"><NavLink className={itemClass} to="/aquaponics-systems">Hệ thống Aquaponics</NavLink>{has("device_templates.read") && <NavLink className={itemClass} to="/catalogs">Danh mục</NavLink>}{has("users.read") && <NavLink className={itemClass} to="/users">Người dùng</NavLink>}<NavLink className={itemClass} to="/profile">Hồ sơ</NavLink></nav><span className="text-sm">{session?.user.full_name}</span><button className="rounded border px-3 py-2" onClick={() => void logout()}>Đăng xuất</button></div></header>
    <main className="mx-auto max-w-7xl p-4"><Outlet /></main>
  </div>
}
