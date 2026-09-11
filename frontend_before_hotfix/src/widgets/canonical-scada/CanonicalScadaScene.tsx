import { Html, Line, OrbitControls, OrthographicCamera } from "@react-three/drei"
import { Canvas, useFrame } from "@react-three/fiber"
import { useMemo, useRef, useState } from "react"
import type { Group } from "three"
import type { ScadaRuntimeResponse, ScadaSymbol } from "@/api/contracts"
import { Card, CardContent } from "@/shared/ui/card"
import { StatusBadge } from "@/shared/ui/status-badge"

function boundStatus(runtime: ScadaRuntimeResponse, symbol: ScadaSymbol) {
  const binding = symbol.binding
  if (!binding) return { label: "Chưa gắn dữ liệu", active: false, alarm: false }
  if (binding.entity_type === "DEVICE") {
    const device = runtime.inventory.devices.find((item) => item.id === binding.entity_id)
    const state = runtime.runtime.devices.find((item) => item.id === binding.entity_id)
    return { label: device?.enabled ? state?.connectivity ?? "UNKNOWN" : "DISABLED", active: state?.connectivity === "ONLINE", alarm: false }
  }
  if (binding.entity_type === "SENSOR") {
    const state = runtime.runtime.sensors.find((item) => item.id === binding.entity_id)
    return { label: state ? `${state.freshness} · ${state.quality}` : "NO_DATA", active: state?.freshness === "FRESH" && state.quality === "VALID", alarm: state?.quality === "INVALID" || state?.quality === "OUT_OF_RANGE" }
  }
  const state = runtime.runtime.actuators.find((item) => item.id === binding.entity_id)
  return { label: state ? `${state.reported_state ? "BẬT" : "TẮT"} · ${state.synchronization}` : "UNKNOWN", active: state?.reported_state === true, alarm: state?.synchronization === "OUT_OF_SYNC" || state?.command_status === "TIMEOUT" || state?.command_status === "FAILED" }
}

function ProcessSymbol({ symbol, state, selected, reducedMotion, onSelect }: { symbol: ScadaSymbol; state: ReturnType<typeof boundStatus>; selected: boolean; reducedMotion: boolean; onSelect: () => void }) {
  const [hovered, setHovered] = useState(false)
  const group = useRef<Group>(null)
  const color = state.alarm ? "#dc2626" : state.active ? "#0f766e" : "#64748b"
  const kind = symbol.type.toLowerCase()
  useFrame((_, delta) => { if (state.active && !reducedMotion && (kind.includes("pump") || kind.includes("air")) && group.current) group.current.rotation.z += delta * 1.8 })
  return <group ref={group} position={symbol.position} onClick={(event) => { event.stopPropagation(); onSelect() }} onPointerOver={() => setHovered(true)} onPointerOut={() => setHovered(false)}>
    {kind.includes("tank") || kind.includes("bed") || kind.includes("filter") ? <mesh><cylinderGeometry args={[0.8, 0.8, 0.5, 32]} /><meshStandardMaterial color={color} roughness={0.7} /></mesh> : kind.includes("sensor") ? <mesh><sphereGeometry args={[0.45, 20, 12]} /><meshStandardMaterial color={color} emissive={color} emissiveIntensity={state.active ? 0.25 : 0} /></mesh> : <mesh rotation={[Math.PI / 2, 0, 0]}><cylinderGeometry args={[0.42, 0.42, 0.9, 20]} /><meshStandardMaterial color={color} metalness={0.15} roughness={0.5} /></mesh>}
    <Html position={[0, 0.72, 0]} center distanceFactor={10} style={{ pointerEvents: "none" }}><div className={`rounded-md border bg-background/95 px-2 py-1 text-center text-[10px] shadow-sm ${selected ? "border-primary ring-2 ring-primary/20" : "border-border"}`}><div className="font-semibold whitespace-nowrap">{symbol.label}</div><div className="text-muted-foreground whitespace-nowrap">{state.label}</div></div></Html>
    {hovered ? <mesh scale={1.2}><ringGeometry args={[0.55, 0.59, 24]} /><meshBasicMaterial color={color} transparent opacity={0.28} /></mesh> : null}
  </group>
}

function SceneContent({ runtime, selectedId, reducedMotion, onSelect }: { runtime: ScadaRuntimeResponse; selectedId: string | null; reducedMotion: boolean; onSelect: (id: string) => void }) {
  const symbols = runtime.layout.symbols
  const byId = useMemo(() => new Map(symbols.map((symbol) => [symbol.id, symbol])), [symbols])
  return <><color attach="background" args={["#edf7f4"]} /><hemisphereLight args={["#ffffff", "#94a3b8", 1.2]} /><directionalLight position={[5, 8, 6]} intensity={1.35} /><mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, -0.62, 0]}><planeGeometry args={[26, 16]} /><meshStandardMaterial color="#dceee9" roughness={0.95} /></mesh>{runtime.layout.connections.map((connection) => { const source = byId.get(connection.source_symbol_id); const target = byId.get(connection.target_symbol_id); if (!source || !target) return null; return <Line key={connection.id} points={[source.position, target.position]} color={connection.active ? "#0891b2" : "#94a3b8"} lineWidth={connection.active ? 4 : 2} dashed={!connection.active} dashSize={0.22} gapSize={0.12} /> })}{symbols.map((symbol) => <ProcessSymbol key={symbol.id} symbol={symbol} state={boundStatus(runtime, symbol)} selected={selectedId === symbol.id} reducedMotion={reducedMotion} onSelect={() => onSelect(symbol.id)} />)}<OrthographicCamera makeDefault position={[0, 12, 15]} zoom={42} near={0.1} far={100} /><OrbitControls enableRotate={false} enablePan={true} enableZoom={true} minZoom={25} maxZoom={70} /></>
}

export function CanonicalScadaScene({ runtime, selectedId, reducedMotion, onSelect }: { runtime: ScadaRuntimeResponse; selectedId: string | null; reducedMotion: boolean; onSelect: (id: string) => void }) {
  const [webglUnavailable] = useState(() => { try { return !document.createElement("canvas").getContext("webgl2") } catch { return true } })
  if (webglUnavailable) return <Card><CardContent className="p-8 text-center text-sm text-muted-foreground">Trình duyệt không hỗ trợ WebGL2. Dùng danh sách vận hành bên dưới để xem trạng thái đầy đủ.</CardContent></Card>
  return <div className="h-[32rem] overflow-hidden rounded-xl border bg-[#edf7f4]" data-testid="scada-canvas"><Canvas orthographic dpr={[1, 1.5]} gl={{ antialias: true, powerPreference: "high-performance" }} aria-label="Sơ đồ vận hành Aquaponics"><SceneContent runtime={runtime} selectedId={selectedId} reducedMotion={reducedMotion} onSelect={onSelect} /></Canvas></div>
}

export function ScadaFallbackList({ runtime, onSelect }: { runtime: ScadaRuntimeResponse; onSelect: (id: string) => void }) {
  return <Card><CardContent className="p-0"><div className="border-b p-4"><h3 className="font-semibold">Danh sách vận hành</h3><p className="mt-1 text-sm text-muted-foreground">HTML fallback cho bàn phím, khả năng tiếp cận và trình duyệt không có WebGL.</p></div><div className="divide-y">{runtime.layout.symbols.map((symbol) => { const state = boundStatus(runtime, symbol); return <button key={symbol.id} type="button" className="flex w-full items-center justify-between gap-3 p-4 text-left hover:bg-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-ring" onClick={() => onSelect(symbol.id)}><span><span className="block font-medium">{symbol.label}</span><span className="text-xs text-muted-foreground">{symbol.type} · {symbol.binding ? `${symbol.binding.entity_type} #${symbol.binding.entity_id}` : "Chưa gắn dữ liệu"}</span></span><StatusBadge value={state.label.split(" · ")[0]} /></button> })}</div></CardContent></Card>
}
