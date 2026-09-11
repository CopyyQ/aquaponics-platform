import { useMemo, useState } from "react"
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { Droplets, Plus, Search } from "lucide-react"
import { Link } from "react-router-dom"
import { createSystem, listSystems, queryKeys } from "@/api/resources"
import type { AquaponicsSystemCreate } from "@/api/contracts"
import { errorMessage } from "@/api/client"
import { useAuth } from "@/app/auth"
import { Button } from "@/shared/ui/button"
import { Card, CardContent } from "@/shared/ui/card"
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle, DialogTrigger } from "@/shared/ui/dialog"
import { EmptyState } from "@/shared/ui/empty-state"
import { Input } from "@/shared/ui/input"
import { Label } from "@/shared/ui/label"
import { Skeleton } from "@/shared/ui/skeleton"
import { StatusBadge } from "@/shared/ui/status-badge"
import { Textarea } from "@/shared/ui/textarea"

const initialDraft: AquaponicsSystemCreate = { code: "", name: "", location: null, description: null }

export function SystemsPage() {
  const { can } = useAuth()
  const client = useQueryClient()
  const [open, setOpen] = useState(false)
  const [search, setSearch] = useState("")
  const [draft, setDraft] = useState<AquaponicsSystemCreate>(initialDraft)
  const systems = useQuery({ queryKey: queryKeys.systems, queryFn: listSystems })
  const creation = useMutation({ mutationFn: () => createSystem({ ...draft, code: draft.code.trim().toUpperCase(), name: draft.name.trim(), location: draft.location?.trim() || null, description: draft.description?.trim() || null }), onSuccess: async () => { await client.invalidateQueries({ queryKey: queryKeys.systems }); setDraft(initialDraft); setOpen(false) } })
  const filtered = useMemo(() => (systems.data ?? []).filter((system) => `${system.name} ${system.code} ${system.location ?? ""}`.toLocaleLowerCase("vi").includes(search.toLocaleLowerCase("vi"))), [search, systems.data])

  return <section className="space-y-6">
    <div className="flex flex-wrap items-start justify-between gap-3"><div><h1 className="text-3xl font-bold">Hệ thống Aquaponics</h1><p className="text-muted-foreground">Chọn một hệ thống để giám sát Device, Sensor, Actuator và Alert.</p></div>{can("aquaponics_systems.create") ? <Dialog open={open} onOpenChange={setOpen}><DialogTrigger asChild><Button><Plus />Tạo hệ thống</Button></DialogTrigger><DialogContent><DialogHeader><DialogTitle>Tạo hệ thống Aquaponics</DialogTitle><DialogDescription>Hệ thống là phạm vi sở hữu của Device và quyền thành viên.</DialogDescription></DialogHeader><form className="space-y-4" onSubmit={(event) => { event.preventDefault(); creation.mutate() }}><div className="grid gap-4 sm:grid-cols-2"><TextField id="system-code" label="Mã hệ thống" value={draft.code} onChange={(code) => setDraft((current) => ({ ...current, code }))} /><TextField id="system-name" label="Tên hệ thống" value={draft.name} onChange={(name) => setDraft((current) => ({ ...current, name }))} /><TextField id="system-location" label="Vị trí" required={false} value={draft.location ?? ""} onChange={(location) => setDraft((current) => ({ ...current, location }))} /><div><Label htmlFor="system-description">Mô tả</Label><Textarea id="system-description" className="mt-1" value={draft.description ?? ""} onChange={(event) => setDraft((current) => ({ ...current, description: event.target.value }))} /></div></div>{creation.isError ? <p role="alert" className="text-sm text-destructive">{errorMessage(creation.error)}</p> : null}<DialogFooter><Button type="button" variant="outline" onClick={() => setOpen(false)}>Huỷ</Button><Button type="submit" disabled={creation.isPending}>Tạo hệ thống</Button></DialogFooter></form></DialogContent></Dialog> : null}</div>
    <label className="relative block max-w-xl"><span className="sr-only">Tìm hệ thống</span><Search className="absolute left-3 top-2.5 size-4 text-muted-foreground" /><Input className="pl-9" placeholder="Tìm theo tên, mã hoặc vị trí" value={search} onChange={(event) => setSearch(event.target.value)} /></label>
    {systems.isLoading ? <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3"><Skeleton className="h-36" /><Skeleton className="h-36" /><Skeleton className="h-36" /></div> : systems.isError ? <EmptyState icon={Droplets} title="Không thể tải hệ thống" description={errorMessage(systems.error)} /> : filtered.length ? <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">{filtered.map((system) => <Link key={system.id} to={`/aquaponics-systems/${system.id}`}><Card className="h-full transition-colors hover:border-primary"><CardContent className="p-5"><div className="flex justify-between gap-3"><h2 className="font-semibold">{system.name}</h2><StatusBadge value={system.status} /></div><p className="mt-2 text-sm text-muted-foreground">{system.code}</p><p className="mt-4 text-sm">{system.location || "Chưa đặt vị trí"}</p><p className="mt-1 line-clamp-2 text-xs text-muted-foreground">{system.description || "Không có mô tả"}</p></CardContent></Card></Link>)}</div> : <EmptyState icon={Droplets} title={systems.data?.length ? "Không tìm thấy hệ thống" : "Chưa có hệ thống Aquaponics"} description={systems.data?.length ? "Thử một từ khoá khác." : "Tạo hệ thống đầu tiên khi bạn có quyền."} />}
  </section>
}

function TextField({ id, label, value, onChange, required = true }: { id: string; label: string; value: string; onChange: (value: string) => void; required?: boolean }) { return <div><Label htmlFor={id}>{label}</Label><Input id={id} className="mt-1" value={value} onChange={(event) => onChange(event.target.value)} required={required} /></div> }
