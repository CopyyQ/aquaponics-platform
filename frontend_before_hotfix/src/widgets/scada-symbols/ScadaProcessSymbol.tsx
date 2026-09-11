import { Html } from "@react-three/drei"
import { type ThreeEvent, useFrame, useThree } from "@react-three/fiber"
import { useRef, useState } from "react"
import { Plane, Vector3, type Group } from "three"
import type { ScadaSymbol } from "@/entities/scada/model/types"

const dragPlane = new Plane(new Vector3(0, 1, 0), 0)

type Props = {
  symbol: ScadaSymbol
  selected: boolean
  animated: boolean
  muted: boolean
  statusLabel: string
  alarm: boolean
  editable: boolean
  onSelect: () => void
  onMove?: (position: [number, number, number]) => void
}

export function ScadaProcessSymbol({ symbol, selected, animated, muted, statusLabel, alarm, editable, onSelect, onMove }: Props) {
  const groupRef = useRef<Group>(null)
  const rotorRef = useRef<Group>(null)
  const [dragging, setDragging] = useState(false)
  const { raycaster } = useThree()
  useFrame((_, delta) => {
    if (rotorRef.current && animated) rotorRef.current.rotation.z -= delta * 3.2
  })
  const isPump = ["WATER_PUMP", "AIR_PUMP", "GENERIC_ACTUATOR"].includes(symbol.type)
  const isTank = ["FISH_TANK", "BIO_FILTER", "SUMP_TANK"].includes(symbol.type)
  const isGrowBed = symbol.type === "GROW_BED"
  const isEnergy = symbol.type === "ENERGY_MONITOR"
  const isController = symbol.type === "CONTROLLER_DEVICE"
  const isSensor = symbol.type.endsWith("_SENSOR")
  const color = muted ? "#94a3b8" : alarm ? "#dc2626" : isEnergy ? "#ca8a04" : isPump ? "#2563eb" : isSensor ? "#0f766e" : "#0e7490"

  function startDrag(event: ThreeEvent<PointerEvent>) {
    event.stopPropagation()
    onSelect()
    if (!editable) return
    setDragging(true)
    const target = event.nativeEvent.target
    if (target instanceof Element) target.setPointerCapture(event.pointerId)
  }
  function move(event: ThreeEvent<PointerEvent>) {
    if (!dragging || !editable || !onMove) return
    event.stopPropagation()
    const point = new Vector3()
    if (raycaster.ray.intersectPlane(dragPlane, point)) onMove([point.x, symbol.position[1], point.z])
  }
  function stopDrag(event: ThreeEvent<PointerEvent>) {
    if (!dragging) return
    event.stopPropagation()
    setDragging(false)
    const target = event.nativeEvent.target
    if (target instanceof Element && target.hasPointerCapture(event.pointerId)) target.releasePointerCapture(event.pointerId)
  }

  return <group ref={groupRef} position={symbol.position} onPointerDown={startDrag} onPointerMove={move} onPointerUp={stopDrag} onPointerCancel={stopDrag}>
    {isTank ? <group>
      <mesh scale={[1.25, 0.75, 1.05]}><cylinderGeometry args={[1, 1.05, 1.1, 24]} /><meshStandardMaterial color={color} roughness={0.72} /></mesh>
      <mesh position={[0, 0.58, 0]} rotation={[-Math.PI / 2, 0, 0]}><circleGeometry args={[0.9, 24]} /><meshStandardMaterial color="#67e8f9" transparent opacity={muted ? 0.25 : 0.65} /></mesh>
    </group> : null}
    {isGrowBed ? <group><mesh scale={[1.5, 0.45, 0.9]}><boxGeometry /><meshStandardMaterial color={color} roughness={0.85} /></mesh>{[-0.8, 0, 0.8].map((x) => <mesh key={x} position={[x, 0.65, 0]}><coneGeometry args={[0.25, 0.7, 8]} /><meshStandardMaterial color="#16a34a" /></mesh>)}</group> : null}
    {isPump ? <group ref={rotorRef}><mesh rotation={[Math.PI / 2, 0, 0]}><cylinderGeometry args={[0.62, 0.62, 0.72, 20]} /><meshStandardMaterial color={color} metalness={0.25} roughness={0.42} /></mesh><mesh position={[0, 0, 0.45]}><torusGeometry args={[0.36, 0.1, 10, 24]} /><meshStandardMaterial color="#dbeafe" /></mesh></group> : null}
    {isEnergy ? <group><mesh scale={[1.4, 1.05, 0.72]}><boxGeometry /><meshStandardMaterial color={color} metalness={0.25} roughness={0.48} /></mesh><mesh position={[0, 0.12, 0.4]}><boxGeometry args={[0.85, 0.38, 0.08]} /><meshBasicMaterial color="#0f172a" /></mesh><mesh position={[0, 0.12, 0.46]}><boxGeometry args={[0.55, 0.12, 0.02]} /><meshBasicMaterial color="#22c55e" /></mesh></group> : null}
    {isController ? <group><mesh scale={[1.35, 1, 0.68]}><boxGeometry /><meshStandardMaterial color={color} metalness={0.12} roughness={0.58} /></mesh>{[-0.28, 0, 0.28].map((x) => <mesh key={x} position={[x, 0.1, 0.38]}><sphereGeometry args={[0.07, 10, 8]} /><meshBasicMaterial color={muted ? "#64748b" : "#22c55e"} /></mesh>)}</group> : null}
    {isSensor ? <group><mesh><sphereGeometry args={[0.48, 18, 12]} /><meshStandardMaterial color={color} roughness={0.55} /></mesh><mesh position={[0, -0.58, 0]}><cylinderGeometry args={[0.09, 0.09, 0.55, 10]} /><meshStandardMaterial color="#475569" /></mesh></group> : null}
    {!isTank && !isGrowBed && !isPump && !isEnergy && !isController && !isSensor ? <mesh scale={[1.1, 0.8, 0.8]}><boxGeometry /><meshStandardMaterial color={color} /></mesh> : null}
    {selected ? <mesh scale={[1.75, 1.55, 1.35]}><boxGeometry /><meshBasicMaterial color="#f59e0b" wireframe /></mesh> : null}
    {alarm ? <Html center position={[0.8, 1.15, 0]}><span className="inline-flex h-6 w-6 items-center justify-center rounded-full bg-destructive text-xs font-bold text-destructive-foreground shadow" aria-label="Có cảnh báo">!</span></Html> : null}
    <Html center distanceFactor={11} position={[0, 1.2, 0]} className="pointer-events-none select-none whitespace-nowrap rounded bg-background/95 px-2 py-1 text-center text-[11px] font-medium shadow-sm ring-1 ring-border">
      <span className="block">{symbol.label}</span><span className="block text-[9px] text-muted-foreground">{statusLabel}</span>
    </Html>
  </group>
}
