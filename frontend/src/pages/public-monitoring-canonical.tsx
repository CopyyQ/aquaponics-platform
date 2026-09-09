import { useState } from "react"
import { useQuery } from "@tanstack/react-query"
import { Droplets, Globe2 } from "lucide-react"
import { useParams } from "react-router-dom"
import type { MonitoringRange } from "@/api/contracts"
import { getPublicMonitoringLatest, getPublicMonitoringSeries } from "@/api/resources"
import { errorMessage } from "@/api/client"
import { MonitoringDashboard } from "@/widgets/canonical-monitoring/MonitoringDashboard"
import { EmptyState } from "@/shared/ui/empty-state"
import { Skeleton } from "@/shared/ui/skeleton"
import { Tabs, TabsList, TabsTrigger } from "@/shared/ui/tabs"

const ranges: MonitoringRange[] = ["1h", "6h", "12h", "24h", "30d"]

export function PublicMonitoringPage() {
  const { slug = "" } = useParams()
  const [range, setRange] = useState<MonitoringRange>("24h")
  const latest = useQuery({ queryKey: ["public-monitoring", slug, "latest"], queryFn: () => getPublicMonitoringLatest(slug), enabled: Boolean(slug), refetchInterval: 15_000 })
  const series = useQuery({ queryKey: ["public-monitoring", slug, "series", range], queryFn: () => getPublicMonitoringSeries(slug, range), enabled: Boolean(slug), refetchInterval: 30_000 })
  if (!slug) return <EmptyState icon={Globe2} title="Đường dẫn giám sát không hợp lệ" description="Thiếu mã chia sẻ công khai." />
  return <main className="min-h-screen bg-background"><header className="border-b bg-card/80 backdrop-blur"><div className="mx-auto flex max-w-[1600px] items-center gap-3 px-4 py-4 sm:px-6"><div className="grid size-10 place-items-center rounded-xl bg-primary text-primary-foreground"><Droplets /></div><div><h1 className="font-semibold">Aquaponics Monitoring</h1><p className="text-xs text-muted-foreground">Chế độ công khai chỉ đọc</p></div></div></header><div className="mx-auto max-w-[1600px] space-y-5 px-4 py-6 sm:px-6"><div className="flex flex-wrap items-center justify-between gap-3"><div><h2 className="text-2xl font-bold">Giám sát hệ thống</h2><p className="text-sm text-muted-foreground">Dữ liệu được cập nhật tự động; không có thao tác điều khiển.</p></div><Tabs value={range} onValueChange={(v) => setRange(v as MonitoringRange)}><TabsList>{ranges.map((value) => <TabsTrigger value={value} key={value}>{value}</TabsTrigger>)}</TabsList></Tabs></div>{latest.isLoading || series.isLoading ? <><Skeleton className="h-28" /><Skeleton className="h-96" /></> : latest.isError || series.isError || !latest.data || !series.data ? <EmptyState icon={Globe2} title="Không thể tải dữ liệu công khai" description={errorMessage(latest.error ?? series.error)} /> : <MonitoringDashboard latest={latest.data} series={series.data} range={range} />}</div></main>
}
