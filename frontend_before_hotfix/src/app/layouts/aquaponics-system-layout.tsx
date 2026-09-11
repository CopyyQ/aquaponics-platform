import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { Activity, AlertTriangle, BellRing, Boxes, CalendarDays, LayoutDashboard, Settings2, Users, Wrench } from "lucide-react"
import { Link, NavLink, Outlet, useParams } from "react-router-dom"
import { activateSystem, disableSystem, getSystem, queryKeys } from "@/api/resources"
import { useAuth } from "@/app/auth"
import { PageHeader } from "@/shared/ui/page-header"
import { Button } from "@/shared/ui/button"
import { Alert, AlertDescription, AlertTitle } from "@/shared/ui/alert"
import { Skeleton } from "@/shared/ui/skeleton"
import { cn } from "@/shared/lib/utils"

const tabs = [
  { path: "overview", label: "Tổng quan", icon: LayoutDashboard, permission: "aquaponics_systems.read" },
  { path: "scada", label: "Sơ đồ vận hành", icon: Boxes, permission: "scada.read" },
  { path: "monitoring", label: "Quan trắc", icon: Activity, permission: "monitoring.read" },
  { path: "devices", label: "Thiết bị", icon: Wrench, permission: "devices.read" },
  { path: "alerts", label: "Cảnh báo", icon: AlertTriangle, permission: "incidents.read" },
  { path: "members", label: "Thành viên", icon: Users, permission: "aquaponics_systems.read" },
  { path: "activities", label: "Hoạt động", icon: CalendarDays, permission: "activities.read" },
  { path: "notifications", label: "Thông báo", icon: BellRing, permission: "notifications.settings.read" },
  { path: "settings", label: "Thiết lập", icon: Settings2, permission: "aquaponics_systems.read" },
] as const

export function AquaponicsSystemLayout() {
  const systemId = useParams().systemId ?? ""
  const { can } = useAuth()
  const client = useQueryClient()
  const system = useQuery({ queryKey: queryKeys.system(systemId), queryFn: () => getSystem(systemId), enabled: Boolean(systemId) })

  if (system.isLoading) return <div className="space-y-5"><Skeleton className="h-28" /><Skeleton className="h-12" /><Skeleton className="h-96" /></div>
  if (system.isError || !system.data) return <div className="rounded-xl border border-destructive/30 bg-destructive/5 p-6 text-destructive">Không thể tải hệ thống Aquaponics.</div>

  return <div className="space-y-6">
    <PageHeader
      title={system.data.name}
      description={`${system.data.code} · ${system.data.location ?? "Chưa đặt vị trí"}`}
      actions={<div className="flex flex-wrap items-center gap-2"><Link className="text-sm font-medium text-primary hover:underline" to="/aquaponics-systems">← Tất cả hệ thống</Link>{can("aquaponics_systems.manage_all") ? <LifecycleButton system={system.data} onChanged={async () => { await Promise.all([client.invalidateQueries({ queryKey: queryKeys.system(systemId) }), client.invalidateQueries({ queryKey: queryKeys.systems })]) }} /> : null}</div>}
    />
    {system.data.status === "DISABLED" ? <Alert variant="destructive"><AlertTriangle /><AlertTitle>Hệ thống đang bị vô hiệu hóa</AlertTitle><AlertDescription>{system.data.disabled_reason || "Dữ liệu lịch sử vẫn được giữ; kích hoạt lại để tiếp tục vận hành."}</AlertDescription></Alert> : null}
    <nav aria-label="Điều hướng hệ thống" className="-mx-1 flex gap-1 overflow-x-auto border-b px-1 pb-1">
      {tabs.filter((tab) => can(tab.permission)).map(({ path, label, icon: Icon }) => <NavLink key={path} to={`/aquaponics-systems/${systemId}/${path}`} className={({ isActive }) => cn("inline-flex shrink-0 items-center gap-2 rounded-t-lg px-3 py-3 text-sm font-medium transition-colors", isActive ? "border-b-2 border-primary text-primary" : "text-muted-foreground hover:bg-muted hover:text-foreground")}><Icon className="size-4" aria-hidden="true" />{label}</NavLink>)}
    </nav>
    <Outlet context={{ system: system.data }} />
  </div>
}


function LifecycleButton({ system, onChanged }: { system: import("@/api/contracts").AquaponicsSystem; onChanged: () => Promise<void> }) {
  const disabled = system.status === "DISABLED"
  const mutation = useMutation({ mutationFn: (reason?: string) => disabled ? activateSystem(system.id) : disableSystem(system.id, { reason }), onSuccess: onChanged })
  const submit = () => {
    if (disabled) return mutation.mutate(undefined)
    const reason = window.prompt("Lý do vô hiệu hóa hệ thống (ít nhất 3 ký tự):")
    if (reason === null) return
    if (reason.trim().length < 3) return
    mutation.mutate(reason.trim())
  }
  return <Button size="sm" variant={disabled ? "outline" : "destructive"} disabled={mutation.isPending} onClick={submit}>{disabled ? "Kích hoạt lại" : "Vô hiệu hóa"}</Button>
}
