import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { AlertTriangle, ListTree, Pencil, RefreshCw, Save, Send, X } from "lucide-react"
import { useState } from "react"
import { Link, useParams } from "react-router-dom"
import { toast } from "sonner"
import { scadaApi } from "@/entities/scada/api/scada-api"
import type { ScadaLayout, ScadaRuntime, ScadaSymbol, ScadaUnplacedEntity } from "@/entities/scada/model/types"
import { useAuthStore } from "@/features/auth/model/auth-store"
import { useProtectedQueryScope } from "@/features/auth/model/use-protected-query-scope"
import { ScadaScene } from "@/widgets/project-scada/ScadaScene"
import { queryKeys } from "@/shared/api/query-keys"
import { formatDateTime } from "@/shared/lib/date"
import { Button } from "@/shared/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/shared/ui/card"
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@/shared/ui/dialog"
import { EmptyState } from "@/shared/ui/empty-state"
import { PageHeader } from "@/shared/ui/page-header"
import { Skeleton } from "@/shared/ui/skeleton"
import { StatusBadge } from "@/shared/ui/status-badge"

const symbolTypes = ["CONTROLLER_DEVICE", "ENERGY_MONITOR", "WATER_PUMP", "AIR_PUMP", "VALVE", "FAN", "GROW_LIGHT", "HEATER", "GENERIC_ACTUATOR", "PH_SENSOR", "WATER_TEMPERATURE_SENSOR", "HUMIDITY_SENSOR", "GENERIC_SENSOR"]

export function ProjectScadaPage() {
  const projectId = Number(useParams().projectId)
  const role = useAuthStore((state) => state.user?.system_role)
  const { active, queryScope } = useProtectedQueryScope()
  const queryClient = useQueryClient()
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [listOpen, setListOpen] = useState(false)
  const [editing, setEditing] = useState(false)
  const [draftLayout, setDraftLayout] = useState<ScadaLayout | null>(null)
  const [editorWarnings, setEditorWarnings] = useState<string[]>([])
  const queryKey = queryKeys.projects.scadaRuntime(queryScope, projectId)
  const query = useQuery({
    queryKey,
    queryFn: () => scadaApi.runtime(projectId),
    enabled: active && projectId > 0,
    refetchInterval: () => document.visibilityState === "visible" && !editing ? 10_000 : false,
    staleTime: 5_000,
  })
  const saveMutation = useMutation({
    mutationFn: (layout: ScadaLayout) => scadaApi.saveDraft(projectId, layout),
    onSuccess: (result) => { setEditorWarnings(result.warnings); toast.success("Đã lưu bản nháp sơ đồ") },
    onError: () => toast.error("Không thể lưu bản nháp sơ đồ"),
  })
  const publishMutation = useMutation({
    mutationFn: () => scadaApi.publish(projectId),
    onSuccess: async (result) => { setEditorWarnings(result.warnings); await queryClient.invalidateQueries({ queryKey }); setEditing(false); setDraftLayout(null); toast.success("Đã xuất bản sơ đồ vận hành") },
    onError: () => toast.error("Không thể xuất bản sơ đồ. Hãy lưu bản nháp trước."),
  })
  const displayedLayout = draftLayout ?? query.data?.layout
  const selected = displayedLayout?.symbols.find((symbol) => symbol.id === selectedId)

  if (query.isLoading) return <div className="flex flex-col gap-4"><Skeleton className="h-20" /><Skeleton className="h-[38rem]" /></div>
  if (query.isError) return <EmptyState icon={AlertTriangle} title="Không thể tải sơ đồ vận hành" description="Runtime API đang gặp lỗi. Hãy thử lại sau." action={<Button onClick={() => void query.refetch()}><RefreshCw />Thử lại</Button>} />
  if (!query.data || !displayedLayout) return <EmptyState icon={AlertTriangle} title="Chưa có dữ liệu vận hành" description="Dự án này chưa có inventory vận hành khả dụng." />
  const runtime = query.data
  const currentLayout = displayedLayout

  function startEditing() { setDraftLayout(structuredClone(runtime.layout)); setEditorWarnings([]); setEditing(true) }
  function cancelEditing() { setDraftLayout(null); setEditorWarnings([]); setEditing(false) }
  function moveSymbol(id: string, position: [number, number, number]) { setDraftLayout((layout) => layout ? { ...layout, symbols: layout.symbols.map((symbol) => symbol.id === id ? { ...symbol, position } : symbol) } : layout) }
  function changeSymbolType(type: string) { if (!selectedId) return; setDraftLayout((layout) => layout ? { ...layout, symbols: layout.symbols.map((symbol) => symbol.id === selectedId ? { ...symbol, type } : symbol) } : layout) }
  function addUnplaced(entity: ScadaUnplacedEntity) {
    setDraftLayout((layout) => layout ? { ...layout, symbols: [...layout.symbols, { id: `${entity.entity_type.toLowerCase()}-${entity.entity_id}`, type: entity.suggested_symbol_type, label: entity.name, position: [0, 0, 0], binding: { entity_type: entity.entity_type, entity_id: entity.entity_id } }] } : layout)
  }
  function selectIssue(issue: ScadaRuntime["issues"][number]) {
    const direct = currentLayout.symbols.find((symbol) => symbol.binding && ((issue.sensor_id && symbol.binding.entity_type === "SENSOR" && symbol.binding.entity_id === issue.sensor_id) || (issue.actuator_id && symbol.binding.entity_type === "ACTUATOR" && symbol.binding.entity_id === issue.actuator_id)))
    const parent = currentLayout.symbols.find((symbol) => issue.device_id && symbol.binding?.entity_type === "DEVICE" && symbol.binding.entity_id === issue.device_id)
    setSelectedId((direct ?? parent)?.id ?? null)
  }

  return <div className="flex flex-col gap-5">
    <PageHeader title="Sơ đồ vận hành Aquaponics" description="Theo dõi inventory, dữ liệu đo và trạng thái điều khiển theo thời gian thực." actions={<div className="flex flex-wrap gap-2">
      <Button variant="outline" size="sm" aria-busy={query.isFetching} onClick={() => void query.refetch()}><RefreshCw className={query.isFetching ? "animate-spin" : ""} />{query.isFetching ? "Đang làm mới" : "Làm mới"}</Button>
      <Button variant="outline" size="sm" onClick={() => setListOpen(true)}><ListTree />Danh sách vận hành</Button>
      {role === "ADMIN" && !editing ? <Button variant="outline" size="sm" onClick={startEditing}><Pencil />Chỉnh sửa sơ đồ</Button> : null}
      {editing ? <><Button variant="outline" size="sm" onClick={cancelEditing}><X />Hủy</Button><Button variant="outline" size="sm" disabled={!draftLayout || saveMutation.isPending} onClick={() => draftLayout && saveMutation.mutate(draftLayout)}><Save />Lưu nháp</Button><Button size="sm" disabled={publishMutation.isPending} onClick={() => publishMutation.mutate()}><Send />Xuất bản</Button></> : null}
    </div>} />

    <KpiGrid runtime={runtime} />
    <div className={editing ? "grid gap-5 xl:grid-cols-[18rem_minmax(0,1fr)_22rem]" : "grid gap-5 xl:grid-cols-[minmax(0,1fr)_22rem]"}>
      {editing ? <EditorPanel runtime={runtime} layout={currentLayout} selected={selected} warnings={editorWarnings} onSelect={setSelectedId} onAdd={addUnplaced} onChangeType={changeSymbolType} /> : null}
      <Card className="overflow-hidden"><CardHeader className="flex-row items-center justify-between space-y-0"><CardTitle className="text-base">Dòng vận hành · {runtime.project.name}</CardTitle><span className="text-xs text-muted-foreground">Cập nhật {formatTime(runtime.updated_at)}</span></CardHeader><CardContent className="h-[32rem] p-0 sm:h-[40rem]"><ScadaScene runtime={runtime} layout={currentLayout} selectedId={selectedId} editable={editing} onSelect={setSelectedId} onMove={moveSymbol} /></CardContent></Card>
      <Card className="h-full"><CardHeader><CardTitle className="text-base">Chi tiết vận hành</CardTitle></CardHeader><CardContent>{selected ? <Details runtime={runtime} symbol={selected} /> : <p className="text-sm text-muted-foreground">Chọn một bể, thiết bị, bơm hoặc cảm biến trên sơ đồ để xem chi tiết.</p>}</CardContent></Card>
    </div>

    <Card><CardHeader><CardTitle className="text-base">Vấn đề vận hành ưu tiên</CardTitle></CardHeader><CardContent>{runtime.issues.length ? <div className="grid gap-3 lg:grid-cols-2">{runtime.issues.map((issue) => <article key={issue.id} className="rounded-lg border p-4"><div className="flex items-center gap-2"><StatusBadge value={issue.severity} /><strong className="text-sm">{issue.title}</strong></div><dl className="mt-3 grid gap-1 text-sm"><div><dt className="inline font-medium">Nguyên nhân: </dt><dd className="inline text-muted-foreground">{issue.root_cause}</dd></div><div><dt className="inline font-medium">Hiện trạng: </dt><dd className="inline text-muted-foreground">{issue.current_state}</dd></div><div><dt className="inline font-medium">Đề xuất: </dt><dd className="inline text-muted-foreground">{issue.suggested_action}</dd></div></dl><Button className="mt-3" variant="outline" size="sm" onClick={() => selectIssue(issue)}>Xem trên sơ đồ</Button></article>)}</div> : <p className="text-sm text-muted-foreground">Không có vấn đề cần xử lý.</p>}</CardContent></Card>
    <OperationalList open={listOpen} onOpenChange={setListOpen} runtime={runtime} onSelect={(binding) => { const symbol = currentLayout.symbols.find((item) => item.binding?.entity_type === binding.entity_type && item.binding.entity_id === binding.entity_id) ?? currentLayout.symbols.find((item) => binding.parent_device_id && item.binding?.entity_type === "DEVICE" && item.binding.entity_id === binding.parent_device_id); setSelectedId(symbol?.id ?? null); setListOpen(false) }} />
    <div className="sr-only" aria-live="polite">Sơ đồ vận hành có {runtime.summary.active_devices_total} thiết bị hoạt động, {runtime.summary.active_sensors_total} cảm biến hoạt động, {runtime.summary.active_actuators_total} cơ cấu chấp hành và {runtime.issues.length} vấn đề.</div>
  </div>
}

function KpiGrid({ runtime }: { runtime: ScadaRuntime }) {
  const groups = [
    ["Thiết bị", [[runtime.summary.active_devices_total, "Hoạt động"], [runtime.summary.connected_devices, "Kết nối"], [runtime.summary.waiting_devices, "Chờ kết nối"], [runtime.summary.disconnected_devices, "Mất kết nối"], [runtime.summary.disabled_devices, "Đã vô hiệu hóa"]]],
    ["Cảm biến", [[runtime.summary.active_sensors_total, "Hoạt động"], [runtime.summary.fresh_sensors, "Có dữ liệu mới"], [runtime.summary.fresh_valid_sensors, "Hợp lệ"], [runtime.summary.fresh_invalid_sensors, "Dữ liệu lỗi"], [runtime.summary.stale_sensors, "Dữ liệu cũ"], [runtime.summary.no_data_sensors, "Chưa có dữ liệu"]]],
    ["Điều khiển", [[runtime.summary.active_actuators_total, "Cơ cấu"], [runtime.summary.actuators_on, "Đang bật"], [runtime.summary.actuators_off, "Đang tắt"], [runtime.summary.actuators_out_of_sync, "Không đồng bộ"], [runtime.summary.commands_timeout, "Timeout"]]],
    ["Năng lượng & cảnh báo", [[runtime.summary.active_energy_monitors, "Energy Monitor"], [runtime.summary.connected_energy_monitors, "Energy kết nối"], [runtime.summary.open_alerts, "Cảnh báo mở"], [runtime.summary.critical_alerts, "Critical"], [runtime.summary.warning_alerts, "Warning"]]],
  ] as const
  return <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">{groups.map(([title, metrics]) => <Card key={title}><CardHeader className="pb-2"><CardTitle className="text-sm">{title}</CardTitle></CardHeader><CardContent className="grid grid-cols-2 gap-2">{metrics.map(([value, label]) => <div key={label} className="rounded-md bg-muted/60 p-2"><div className="text-lg font-bold tabular-nums">{value}</div><div className="text-xs text-muted-foreground">{label}</div></div>)}</CardContent></Card>)}</div>
}

function EditorPanel({ runtime, layout, selected, warnings, onSelect, onAdd, onChangeType }: { runtime: ScadaRuntime; layout: ScadaLayout; selected: ScadaSymbol | undefined; warnings: string[]; onSelect: (id: string) => void; onAdd: (entity: ScadaUnplacedEntity) => void; onChangeType: (type: string) => void }) {
  return <Card><CardHeader><CardTitle className="text-base">Trình chỉnh sửa</CardTitle></CardHeader><CardContent className="space-y-5 text-sm"><section><h3 className="font-medium">Thư viện ký hiệu</h3><label className="mt-2 block text-xs text-muted-foreground" htmlFor="scada-symbol-type">Loại symbol đang chọn</label><select id="scada-symbol-type" className="mt-1 h-9 w-full rounded-md border bg-background px-2" disabled={!selected} value={selected?.type ?? ""} onChange={(event) => onChangeType(event.target.value)}><option value="">Chọn symbol</option>{symbolTypes.map((type) => <option key={type} value={type}>{type}</option>)}</select></section><section><h3 className="font-medium">Entities chưa bố trí ({runtime.unplaced_entities.length})</h3>{runtime.unplaced_entities.length ? <ul className="mt-2 space-y-2">{runtime.unplaced_entities.map((entity) => <li key={`${entity.entity_type}-${entity.entity_id}`} className="rounded border p-2"><div className="font-medium">{entity.name}</div><div className="text-xs text-muted-foreground">{entity.entity_type} · {entity.code}</div><Button className="mt-2" size="sm" variant="outline" onClick={() => onAdd(entity)}>Thêm vào canvas</Button></li>)}</ul> : <p className="mt-2 text-xs text-muted-foreground">Mọi entity active bắt buộc đã được biểu diễn.</p>}</section><section><h3 className="font-medium">Entities đã bố trí ({layout.symbols.filter((item) => item.binding).length})</h3><ul className="mt-2 max-h-48 space-y-1 overflow-auto">{layout.symbols.filter((item) => item.binding).map((item) => <li key={item.id}><button className="w-full rounded px-2 py-1 text-left hover:bg-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring" onClick={() => onSelect(item.id)}>{item.label}</button></li>)}</ul></section>{warnings.length ? <section aria-live="polite"><h3 className="font-medium text-warning">Cảnh báo publish</h3><ul className="mt-2 list-disc space-y-1 pl-4 text-xs">{warnings.map((warning) => <li key={warning}>{warning}</li>)}</ul></section> : null}</CardContent></Card>
}

function Details({ runtime, symbol }: { runtime: ScadaRuntime; symbol: ScadaSymbol }) {
  const binding = symbol.binding
  if (!binding) return <div><h3 className="font-semibold">{symbol.label}</h3><p className="mt-2 text-sm text-muted-foreground">Ký hiệu hạ tầng, không mang trạng thái runtime.</p></div>
  if (binding.entity_type === "DEVICE") {
    const device = runtime.inventory.devices.find((item) => item.id === binding.entity_id)
    if (!device) return null
    const sensors = runtime.inventory.sensors.filter((item) => item.device_id === device.id)
    const actuators = runtime.inventory.actuators.filter((item) => item.device_id === device.id)
    const energy = runtime.energy_monitor_runtime.find((item) => item.device_id === device.id)
    return <div><h3 className="font-semibold">{device.name}</h3><Info lines={[`Mã: ${device.code}`, `Template: ${device.template_code ?? "—"}`, `Loại: ${device.device_kind}`, `Lifecycle: ${device.enabled ? "ENABLED" : "DISABLED"}`, `Kết nối: ${device.connectivity}`, `Lần cuối: ${formatTime(device.last_seen_at)}`]} />{energy ? <Info lines={[`Điện áp đầu ra: ${energy.output_voltage ?? "—"} V`, `Điện áp đầu vào: ${energy.input_voltage ?? "—"} V`, `Dòng điện tiêu thụ: ${energy.load_current ?? "—"} A`, `Dòng điện đầu vào: ${energy.input_current ?? "—"} A`, `Công suất tiêu thụ: ${energy.current_power ?? "—"} W`, `Điện năng tiêu thụ: ${energy.energy_total ?? "—"} Wh`, `Phép đo hợp lệ: ${energy.valid_measurements}/${energy.expected_measurements}`]} /> : null}<h4 className="mt-4 text-sm font-medium">Cảm biến ({sensors.length})</h4><ul className="mt-1 text-xs text-muted-foreground">{sensors.map((item) => <li key={item.id}>{item.name} · {item.enabled ? "Hoạt động" : "Vô hiệu hóa"}</li>)}</ul><h4 className="mt-4 text-sm font-medium">Cơ cấu ({actuators.length})</h4><ul className="mt-1 text-xs text-muted-foreground">{actuators.map((item) => <li key={item.id}>{item.name} · {item.enabled ? "Hoạt động" : "Vô hiệu hóa"}</li>)}</ul><Link className="mt-5 inline-block text-sm font-medium text-primary hover:underline" to={`../devices/${device.id}`}>{energy ? "Mở dashboard năng lượng" : "Xem thiết bị"}</Link></div>
  }
  if (binding.entity_type === "SENSOR") {
    const sensor = runtime.inventory.sensors.find((item) => item.id === binding.entity_id); const state = runtime.runtime.sensors.find((item) => item.id === binding.entity_id)
    if (!sensor || !state) return null
    return <div><h3 className="font-semibold">{sensor.name}</h3><Info lines={[`Mã: ${sensor.code}`, `Model: ${sensor.sensor_model_code}`, `Giá trị: ${state.value ?? "—"} ${sensor.unit}`, `Freshness: ${state.freshness}`, `Quality: ${state.quality}`, `Recorded: ${formatTime(state.recorded_at)}`, `Received: ${formatTime(state.received_at)}`]} /><Link className="mt-5 inline-block text-sm font-medium text-primary hover:underline" to={`../devices/${sensor.device_id}/sensors/${sensor.id}`}>Xem cảm biến</Link></div>
  }
  const actuator = runtime.inventory.actuators.find((item) => item.id === binding.entity_id); const state = runtime.runtime.actuators.find((item) => item.id === binding.entity_id); const device = runtime.inventory.devices.find((item) => item.id === actuator?.device_id)
  if (!actuator || !state) return null
  return <div><h3 className="font-semibold">{actuator.name}</h3><Info lines={[`Mã: ${actuator.code}`, `Device: ${device?.name ?? "—"}`, `Kết nối: ${device?.connectivity ?? "—"}`, `Mong muốn: ${formatBoolean(state.desired_state)}`, `Thực tế: ${formatBoolean(state.reported_state)}`, `Đồng bộ: ${state.synchronization}`, `Lệnh gần nhất: ${state.command_status ?? "—"}`, `Thời gian lệnh: ${formatTime(state.command_time)}`, `ACK: ${formatTime(state.last_ack_at)}`, `Lỗi: ${state.failure_reason ?? "—"}`]} /><p className="mt-3 text-xs text-muted-foreground">Trạng thái reported chỉ cập nhật từ phản hồi thiết bị, không cập nhật lạc quan.</p><Link className="mt-4 inline-block text-sm font-medium text-primary hover:underline" to={`../devices/${actuator.device_id}`}>Xem thiết bị</Link></div>
}

function OperationalList({ open, onOpenChange, runtime, onSelect }: { open: boolean; onOpenChange: (open: boolean) => void; runtime: ScadaRuntime; onSelect: (binding: { entity_type: "DEVICE" | "SENSOR" | "ACTUATOR"; entity_id: number; parent_device_id?: number }) => void }) {
  return <Dialog open={open} onOpenChange={onOpenChange}><DialogContent className="max-h-[90vh] max-w-6xl overflow-y-auto"><DialogHeader><DialogTitle>Danh sách vận hành</DialogTitle><DialogDescription>Inventory đầy đủ của {runtime.project.name}, kể cả entity chưa bố trí và đã vô hiệu hóa.</DialogDescription></DialogHeader><InventorySection title="Thiết bị" rows={runtime.inventory.devices.map((item) => ({ key: item.id, name: item.name, code: item.code, status: `${item.enabled ? item.connectivity : "DISABLED"} · ${item.device_kind}`, action: () => onSelect({ entity_type: "DEVICE", entity_id: item.id }) }))} /><InventorySection title="Cảm biến" rows={runtime.inventory.sensors.map((item) => { const state = runtime.runtime.sensors.find((candidate) => candidate.id === item.id); return { key: item.id, name: item.name, code: item.code, status: `${item.enabled ? state?.freshness : "DISABLED"} · ${state?.quality ?? "—"} · ${state?.value ?? "—"} ${item.unit}`, action: () => onSelect({ entity_type: "SENSOR", entity_id: item.id, parent_device_id: item.device_id }) } })} /><InventorySection title="Cơ cấu chấp hành" rows={runtime.inventory.actuators.map((item) => { const state = runtime.runtime.actuators.find((candidate) => candidate.id === item.id); return { key: item.id, name: item.name, code: item.code, status: `${item.enabled ? state?.synchronization : "DISABLED"} · reported ${formatBoolean(state?.reported_state ?? null)} · ${state?.command_status ?? "—"}`, action: () => onSelect({ entity_type: "ACTUATOR", entity_id: item.id, parent_device_id: item.device_id }) } })} /><InventorySection title="Thiết bị năng lượng" rows={runtime.inventory.energy_monitors.map((item) => { const state = runtime.energy_monitor_runtime.find((candidate) => candidate.device_id === item.id); return { key: item.id, name: item.name, code: item.code, status: `${item.connectivity} · ${state?.current_power ?? "—"} W · ${state?.output_voltage ?? "—"} V · ${state?.valid_measurements ?? 0}/${state?.expected_measurements ?? 0} hợp lệ`, action: () => onSelect({ entity_type: "DEVICE", entity_id: item.id }) } })} /><InventorySection title="Chưa bố trí trên sơ đồ" rows={runtime.unplaced_entities.map((item) => ({ key: `${item.entity_type}-${item.entity_id}`, name: item.name, code: item.code, status: item.reason, action: () => onSelect({ entity_type: item.entity_type, entity_id: item.entity_id, parent_device_id: item.parent_device_id ?? undefined }) }))} /></DialogContent></Dialog>
}

function InventorySection({ title, rows }: { title: string; rows: Array<{ key: string | number; name: string; code: string; status: string; action: () => void }> }) { return <section><h3 className="mb-2 font-semibold">{title} ({rows.length})</h3>{rows.length ? <div className="overflow-x-auto"><table className="w-full text-sm"><thead><tr className="border-b text-left"><th className="p-2">Tên</th><th className="p-2">Mã</th><th className="p-2">Trạng thái / giá trị</th><th className="p-2">Thao tác</th></tr></thead><tbody>{rows.map((row) => <tr key={row.key} className="border-b"><td className="p-2 font-medium">{row.name}</td><td className="p-2 font-mono text-xs">{row.code}</td><td className="p-2 text-muted-foreground">{row.status}</td><td className="p-2"><Button size="sm" variant="outline" onClick={row.action}>Chọn trên sơ đồ</Button></td></tr>)}</tbody></table></div> : <p className="text-sm text-muted-foreground">Không có entity trong nhóm này.</p>}</section> }
function Info({ lines }: { lines: string[] }) { return <ul className="mt-3 space-y-1 text-sm text-muted-foreground">{lines.map((line) => <li key={line}>{line}</li>)}</ul> }
function formatBoolean(value: boolean | null) { return value === null ? "—" : value ? "Bật" : "Tắt" }
function formatTime(value: string | null) { return value ? formatDateTime(value) : "—" }
