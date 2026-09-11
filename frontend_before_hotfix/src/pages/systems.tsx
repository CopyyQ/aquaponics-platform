import { useQuery } from "@tanstack/react-query"
import { Link } from "react-router-dom"
import { listSystems } from "@/api/resources"
import { errorMessage } from "@/api/client"

export function SystemsPage() {
  const systems = useQuery({ queryKey: ["aquaponics-systems"], queryFn: listSystems })
  return <section className="space-y-6"><div><h1 className="text-3xl font-bold">Hệ thống Aquaponics</h1><p className="text-muted-foreground">Chọn một hệ thống để giám sát Device, Sensor, Actuator và Alert.</p></div>{systems.isLoading && <p>Đang tải…</p>}{systems.isError && <p className="text-destructive">{errorMessage(systems.error)}</p>}<div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">{systems.data?.map((system) => <Link key={system.id} to={`/aquaponics-systems/${system.id}`} className="rounded-xl border bg-card p-5 hover:border-primary"><div className="flex justify-between gap-3"><h2 className="font-semibold">{system.name}</h2><span className="rounded bg-muted px-2 py-1 text-xs">{system.status}</span></div><p className="mt-2 text-sm text-muted-foreground">{system.code} · {system.location || "Chưa đặt vị trí"}</p></Link>)}</div>{systems.data?.length === 0 && <p className="rounded border p-8 text-center text-muted-foreground">Chưa có Hệ thống Aquaponics.</p>}</section>
}
