import { useState, type FormEvent } from "react"
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { Link } from "react-router-dom"
import { createSystem, listSystems } from "@/api/resources"
import { errorMessage } from "@/api/client"
import { useAuth } from "@/app/auth"

export function SystemsPage() {
  const queryClient = useQueryClient(); const { has } = useAuth()
  const systems = useQuery({ queryKey: ["aquaponics-systems"], queryFn: listSystems })
  const [code, setCode] = useState(""); const [name, setName] = useState("")
  const creation = useMutation({ mutationFn: createSystem, onSuccess: async () => { setCode(""); setName(""); await queryClient.invalidateQueries({ queryKey: ["aquaponics-systems"] }) } })
  const submit = (event: FormEvent) => { event.preventDefault(); creation.mutate({ code: code.trim().toUpperCase(), name: name.trim() }) }
  return <section className="space-y-6"><div><h1 className="text-3xl font-bold">Hệ thống Aquaponics</h1><p className="text-muted-foreground">Chọn một hệ thống để giám sát Device, Sensor, Actuator và Alert.</p></div>{has("aquaponics_systems.create") && <form className="flex flex-wrap gap-2 rounded-xl border bg-card p-4" onSubmit={submit}><input className="rounded border bg-background p-2" placeholder="Mã hệ thống" value={code} onChange={(event) => setCode(event.target.value)} required /><input className="min-w-64 rounded border bg-background p-2" placeholder="Tên hệ thống" value={name} onChange={(event) => setName(event.target.value)} required /><button className="rounded bg-primary px-4 text-primary-foreground">Tạo hệ thống</button>{creation.isError && <p className="w-full text-sm text-destructive">{errorMessage(creation.error)}</p>}</form>}{systems.isLoading && <p>Đang tải…</p>}{systems.isError && <p className="text-destructive">{errorMessage(systems.error)}</p>}<div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">{systems.data?.map((system) => <Link key={system.id} to={`/aquaponics-systems/${system.id}`} className="rounded-xl border bg-card p-5 hover:border-primary"><div className="flex justify-between gap-3"><h2 className="font-semibold">{system.name}</h2><span className="rounded bg-muted px-2 py-1 text-xs">{system.status}</span></div><p className="mt-2 text-sm text-muted-foreground">{system.code} · {system.location || "Chưa đặt vị trí"}</p></Link>)}</div>{systems.data?.length === 0 && <p className="rounded border p-8 text-center text-muted-foreground">Chưa có Hệ thống Aquaponics.</p>}</section>
}
