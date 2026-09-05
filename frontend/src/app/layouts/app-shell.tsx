import { useState } from "react"
import { NavLink, Outlet, useNavigate } from "react-router-dom"
import { Droplets, LogOut, Menu, Moon, Sun, UserRound, X } from "lucide-react"
import { getNavigationItems } from "@/app/navigation/navigation-items"
import { cn } from "@/shared/lib/utils"
import { Button } from "@/shared/ui/button"
import { Avatar, AvatarFallback } from "@/shared/ui/avatar"
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuLabel, DropdownMenuSeparator, DropdownMenuTrigger } from "@/shared/ui/dropdown-menu"
import { useAuthStore } from "@/features/auth/model/auth-store"
import { useTheme } from "@/app/providers/theme-provider"

export function AppShell() {
  const [mobileOpen, setMobileOpen] = useState(false)
  const { user, logout } = useAuthStore()
  const { theme, setTheme } = useTheme()
  const navigate = useNavigate()
  const items = getNavigationItems(user?.system_role)

  const sidebar = <aside className="flex h-full w-72 flex-col border-r border-primary-foreground/10 bg-primary text-primary-foreground">
    <div className="flex h-20 items-center gap-3 border-b border-primary-foreground/10 px-6"><div className="grid size-10 place-items-center rounded-xl bg-primary-foreground text-primary"><Droplets className="size-5" /></div><div><div className="font-bold tracking-tight">Aquaponics</div><div className="text-xs text-primary-foreground/65">Trạm quan trắc</div></div></div>
    <nav className="flex flex-1 flex-col gap-1 overflow-y-auto p-4">{items.map(({ label, path, icon: Icon }) => <NavLink key={path} to={path} onClick={() => setMobileOpen(false)} className={({ isActive }) => cn("flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors", isActive ? "bg-primary-foreground text-primary shadow-sm" : "text-primary-foreground/75 hover:bg-primary-foreground/10 hover:text-primary-foreground")}><Icon className="size-4" /><span>{label}</span></NavLink>)}</nav>
    <div className="border-t border-primary-foreground/10 p-4"><div className="rounded-xl bg-primary-foreground/10 p-3"><div className="text-xs text-primary-foreground/65">Đăng nhập với vai trò</div><div className="mt-1 text-sm font-semibold">{user?.system_role === "ADMIN" ? "Quản trị viên" : user?.system_role === "OWNER" ? "Chủ dự án" : "Người xem"}</div></div></div>
  </aside>

  return <div className="min-h-screen bg-background"><div className="fixed inset-y-0 left-0 z-40 hidden lg:block">{sidebar}</div>{mobileOpen && <div className="fixed inset-0 z-50 lg:hidden"><button className="absolute inset-0 bg-black/50" onClick={() => setMobileOpen(false)} aria-label="Đóng menu" /><div className="relative h-full w-72">{sidebar}<Button variant="ghost" size="icon" className="absolute right-2 top-2" onClick={() => setMobileOpen(false)}><X /></Button></div></div>}
    <div className="lg:pl-72"><header className="sticky top-0 z-30 flex h-16 items-center justify-between border-b bg-background/85 px-4 backdrop-blur-xl sm:px-6"><Button variant="ghost" size="icon" className="lg:hidden" onClick={() => setMobileOpen(true)}><Menu /></Button><div className="hidden text-sm text-muted-foreground sm:block">Giám sát môi trường Aquaponics theo thời gian thực</div><div className="ml-auto flex items-center gap-2"><Button variant="ghost" size="icon" onClick={() => setTheme(theme === "dark" ? "light" : "dark")} aria-label="Đổi giao diện">{theme === "dark" ? <Sun /> : <Moon />}</Button><DropdownMenu><DropdownMenuTrigger asChild><Button variant="ghost" className="h-10 gap-2 px-2"><Avatar><AvatarFallback>{user?.full_name?.slice(0, 2).toUpperCase()}</AvatarFallback></Avatar><span className="hidden max-w-36 truncate text-left sm:block">{user?.full_name}</span></Button></DropdownMenuTrigger><DropdownMenuContent align="end" className="w-56"><DropdownMenuLabel><div className="font-medium">{user?.full_name}</div><div className="truncate text-xs font-normal text-muted-foreground">{user?.email}</div></DropdownMenuLabel><DropdownMenuSeparator /><DropdownMenuItem onSelect={() => navigate("/profile")}><UserRound /> Hồ sơ cá nhân</DropdownMenuItem><DropdownMenuItem onSelect={() => { logout(); navigate("/login") }}><LogOut /> Đăng xuất</DropdownMenuItem></DropdownMenuContent></DropdownMenu></div></header><main className="mx-auto max-w-[1600px] p-4 sm:p-6 lg:p-8"><Outlet /></main></div>
  </div>
}
