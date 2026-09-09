import { useState } from "react"
import { useQuery } from "@tanstack/react-query"
import { Activity, BookOpenCheck } from "lucide-react"
import { useParams } from "react-router-dom"
import { listActivities, queryKeys } from "@/api/resources"
import { Card, CardContent } from "@/shared/ui/card"
import { EmptyState } from "@/shared/ui/empty-state"
import { Skeleton } from "@/shared/ui/skeleton"
import { errorMessage } from "@/api/client"
import { Button } from "@/shared/ui/button"
import { Input } from "@/shared/ui/input"

export function ActivitiesPage() {
  const systemId = Number(useParams().systemId)
  const [page, setPage] = useState(1)
  const [action, setAction] = useState("")
  const [entityType, setEntityType] = useState("")
  const params = { page, page_size: 25, action: action || undefined, entity_type: entityType || undefined }
  const activities = useQuery({ queryKey: queryKeys.activities(systemId, params), queryFn: () => listActivities(systemId, params), placeholderData: (previous) => previous })
  if (activities.isLoading) return <Skeleton className="h-80" />
  if (activities.isError) return <EmptyState icon={BookOpenCheck} title="Không thể tải nhật ký" description={errorMessage(activities.error)} />
  const totalPages = Math.max(1, Math.ceil((activities.data?.total ?? 0) / 25))
  return <div className="space-y-5"><div><h2 className="text-xl font-semibold">Hoạt động hệ thống</h2><p className="text-sm text-muted-foreground">Nhật ký thao tác được trả về từ API canonical.</p></div><Card><CardContent className="grid gap-3 p-4 sm:grid-cols-2"><Input aria-label="Lọc theo hành động" placeholder="Hành động, ví dụ device.created" value={action} onChange={(event) => { setAction(event.target.value); setPage(1) }} /><Input aria-label="Lọc theo loại thực thể" placeholder="Loại thực thể, ví dụ DEVICE" value={entityType} onChange={(event) => { setEntityType(event.target.value); setPage(1) }} /></CardContent></Card>{activities.data?.items.length ? <Card><CardContent className="divide-y p-0">{activities.data.items.map((item) => <div key={item.id} className="flex gap-4 p-4"><div className="mt-0.5 rounded-lg bg-primary/10 p-2 text-primary"><Activity className="size-4" aria-hidden="true" /></div><div className="min-w-0"><div className="flex flex-wrap items-center gap-2"><p className="font-medium">{item.summary}</p><span className="text-xs text-muted-foreground">{item.action}</span></div><p className="mt-1 text-sm text-muted-foreground">{item.actor.name} · {item.entity.type}{item.entity.id === null ? "" : ` #${item.entity.id}`} · {new Date(item.created_at).toLocaleString("vi-VN")}</p></div></div>)}</CardContent></Card> : <EmptyState icon={BookOpenCheck} title="Chưa có hoạt động" description="Không có hoạt động phù hợp với bộ lọc hiện tại." />}<div className="flex items-center justify-between"><p className="text-sm text-muted-foreground">Trang {page}/{totalPages} · {activities.data?.total ?? 0} mục</p><div className="flex gap-2"><Button variant="outline" disabled={page <= 1 || activities.isFetching} onClick={() => setPage((value) => value - 1)}>Trước</Button><Button variant="outline" disabled={page >= totalPages || activities.isFetching} onClick={() => setPage((value) => value + 1)}>Sau</Button></div></div></div>
}
