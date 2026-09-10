import { useMemo, useState } from "react"
import { useQuery } from "@tanstack/react-query"
import { Droplets, Search } from "lucide-react"
import { Link } from "react-router-dom"
import { listSystems, queryKeys } from "@/api/resources"
import { errorMessage } from "@/api/client"
import { Card, CardContent } from "@/shared/ui/card"
import { EmptyState } from "@/shared/ui/empty-state"
import { Input } from "@/shared/ui/input"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/shared/ui/select"
import { Skeleton } from "@/shared/ui/skeleton"
import { StatusBadge } from "@/shared/ui/status-badge"

type StatusFilter = "ACTIVE" | "DISABLED" | "ALL"

export function SystemsPage() {
  const [search, setSearch] = useState("")
  const [status, setStatus] = useState<StatusFilter>("ACTIVE")
  const systems = useQuery({ queryKey: queryKeys.systems, queryFn: listSystems })
  const filtered = useMemo(() => (systems.data ?? []).filter((system) => (status === "ALL" || system.status === status) && `${system.name} ${system.code} ${system.location ?? ""}`.toLocaleLowerCase("vi").includes(search.toLocaleLowerCase("vi"))), [search, status, systems.data])

  return <section className="space-y-6">
    <div><h1 className="text-balance text-3xl font-bold">Hệ thống Aquaponics</h1><p className="text-pretty text-muted-foreground">Chọn một hệ thống để giám sát Device, Sensor, Actuator và Alert.</p></div>
    <div className="flex flex-wrap items-center gap-2">
      <label className="relative block w-full shrink-0 md:w-[calc((100%-1rem)/2)] xl:w-[calc((100%-2rem)/3)]"><span className="sr-only">Tìm hệ thống</span><Search className="absolute left-3 top-2.5 size-4 text-muted-foreground" /><Input className="pl-9" placeholder="Tìm theo tên, mã hoặc vị trí" value={search} onChange={(event) => setSearch(event.target.value)} /></label>
      <Select value={status} onValueChange={(value) => setStatus(value as StatusFilter)}><SelectTrigger aria-label="Lọc theo trạng thái" className="w-auto shrink-0 gap-2"><SelectValue /></SelectTrigger><SelectContent position="popper" sideOffset={6} className="w-auto min-w-[var(--radix-select-trigger-width)] whitespace-nowrap"><SelectItem value="ACTIVE">Đang hoạt động</SelectItem><SelectItem value="DISABLED">Đã vô hiệu hóa</SelectItem><SelectItem value="ALL">Tất cả trạng thái</SelectItem></SelectContent></Select>
    </div>
    {systems.isLoading ? <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3"><Skeleton className="h-36" /><Skeleton className="h-36" /><Skeleton className="h-36" /></div> : systems.isError ? <EmptyState icon={Droplets} title="Không thể tải hệ thống" description={errorMessage(systems.error)} /> : filtered.length ? <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">{filtered.map((system) => <Link key={system.id} to={`/aquaponics-systems/${system.id}`}><Card className="h-full transition-colors hover:border-primary"><CardContent className="p-5"><div className="flex justify-between gap-3"><h2 className="font-semibold">{system.name}</h2><StatusBadge value={system.status} /></div><p className="mt-2 text-sm text-muted-foreground">{system.code}</p><p className="mt-4 text-sm">{system.location || "Chưa đặt vị trí"}</p><p className="mt-1 line-clamp-2 text-xs text-muted-foreground">{system.description || "Không có mô tả"}</p></CardContent></Card></Link>)}</div> : <EmptyState icon={Droplets} title={systems.data?.length ? "Không tìm thấy hệ thống" : "Chưa có hệ thống Aquaponics"} description={systems.data?.length ? "Thử từ khoá khác hoặc đổi bộ lọc trạng thái." : "Tạo hệ thống đầu tiên khi bạn có quyền."} />}
  </section>
}
