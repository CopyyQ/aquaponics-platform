import { Line, OrbitControls, OrthographicCamera } from "@react-three/drei"
import { Canvas } from "@react-three/fiber"
import { useMemo } from "react"
import type { ScadaLayout, ScadaRuntime, ScadaSymbol } from "@/entities/scada/model/types"
import { ScadaProcessSymbol } from "@/widgets/scada-symbols/ScadaProcessSymbol"

type Props = {
  runtime: ScadaRuntime
  layout: ScadaLayout
  selectedId: string | null
  editable?: boolean
  onSelect: (id: string | null) => void
  onMove?: (id: string, position: [number, number, number]) => void
}

function symbolState(runtime: ScadaRuntime, symbol: ScadaSymbol) {
  const binding = symbol.binding
  if (!binding) return { animated: false, muted: false, label: "Hạ tầng", alarm: false }
  const issues = runtime.issues.filter((issue) => issue.device_id === (binding.entity_type === "DEVICE" ? binding.entity_id : null) || issue.sensor_id === (binding.entity_type === "SENSOR" ? binding.entity_id : null) || issue.actuator_id === (binding.entity_type === "ACTUATOR" ? binding.entity_id : null))
  if (binding.entity_type === "DEVICE") {
    const item = runtime.inventory.devices.find((device) => device.id === binding.entity_id)
    return { animated: false, muted: !item?.enabled || item.connectivity !== "ONLINE", label: item?.enabled ? item.connectivity : "DISABLED", alarm: issues.some((issue) => issue.severity !== "INFO") }
  }
  if (binding.entity_type === "SENSOR") {
    const item = runtime.runtime.sensors.find((sensor) => sensor.id === binding.entity_id)
    return { animated: false, muted: item?.freshness !== "FRESH", label: item ? `${item.freshness} · ${item.quality}` : "UNKNOWN", alarm: issues.length > 0 }
  }
  const item = runtime.runtime.actuators.find((actuator) => actuator.id === binding.entity_id)
  const parent = runtime.inventory.actuators.find((actuator) => actuator.id === binding.entity_id)
  const device = runtime.inventory.devices.find((candidate) => candidate.id === parent?.device_id)
  return { animated: item?.reported_state === true && device?.connectivity === "ONLINE", muted: device?.connectivity !== "ONLINE", label: `${item?.reported_state ? "ON" : "OFF"} · ${item?.command_status ?? item?.synchronization ?? "UNKNOWN"}`, alarm: issues.length > 0 }
}

function SceneContent({ runtime, layout, selectedId, editable = false, onSelect, onMove }: Props) {
  const byId = useMemo(() => new Map(layout.symbols.map((symbol) => [symbol.id, symbol])), [layout.symbols])
  return <>
    <color attach="background" args={["#f4f8f7"]} />
    <hemisphereLight args={["#f8fafc", "#94a3b8", 1.35]} /><directionalLight position={[4, 9, 6]} intensity={1.6} />
    <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, -0.72, 0]} onClick={() => onSelect(null)}><planeGeometry args={[28, 15]} /><meshStandardMaterial color="#e4efec" roughness={0.95} /></mesh>
    <group>
      {layout.symbols.map((symbol) => { const state = symbolState(runtime, symbol); return <ScadaProcessSymbol key={symbol.id} symbol={symbol} selected={selectedId === symbol.id} animated={state.animated} muted={state.muted} statusLabel={state.label} alarm={state.alarm} editable={editable} onSelect={() => onSelect(symbol.id)} onMove={(position) => onMove?.(symbol.id, position)} /> })}
      {layout.connections.map((connection) => { const source = byId.get(connection.source_symbol_id); const target = byId.get(connection.target_symbol_id); if (!source || !target) return null; return <Line key={connection.id} points={[source.position, target.position]} color={connection.active ? "#0891b2" : "#94a3b8"} lineWidth={connection.active ? 4 : 2} dashed={!connection.active} dashSize={0.25} gapSize={0.15} /> })}
    </group>
    <OrthographicCamera makeDefault position={[0, 13, 15]} zoom={44} near={0.1} far={100} />
    <OrbitControls enabled={!editable} enableRotate={false} minZoom={24} maxZoom={75} enableDamping dampingFactor={0.08} />
  </>
}

export function ScadaScene(props: Props) {
  const supportsWebGl2 = useMemo(() => {
    try {
      return Boolean(document.createElement("canvas").getContext("webgl2"))
    } catch {
      return false
    }
  }, [])

  if (!supportsWebGl2) {
    return <div data-testid="scada-canvas" className="flex h-full items-center justify-center p-6 text-center" role="img" aria-label="Sơ đồ vận hành aquaponics không khả dụng">
      <p className="max-w-md text-sm text-muted-foreground">Trình duyệt không hỗ trợ WebGL2. Dùng nút “Danh sách vận hành” để xem đầy đủ thiết bị và dữ liệu hiện tại.</p>
    </div>
  }

  return <Canvas data-testid="scada-canvas" dpr={[1, 1.6]} orthographic gl={{ antialias: true, powerPreference: "high-performance" }} aria-label="Sơ đồ vận hành aquaponics"><SceneContent {...props} /></Canvas>
}
