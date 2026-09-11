import { useState, useRef, useCallback } from "react"
import { createPortal } from "react-dom"
import { buildActuatorChartSegments } from "@/features/view-device-monitoring-history/lib/actuator-chart-segments"
import type {
  MonitoringActuatorHistoryGap,
  MonitoringActuatorHistoryPoint,
} from "@/entities/telemetry/model/project-monitoring"
import { parseApiDate, VIETNAM_TIME_ZONE } from "@/shared/lib/date"

const fullTimeFormatter = new Intl.DateTimeFormat("vi-VN", {
  timeZone: VIETNAM_TIME_ZONE,
  day: "2-digit",
  month: "2-digit",
  year: "numeric",
  hour: "2-digit",
  minute: "2-digit",
  second: "2-digit",
})

interface TooltipData {
  screenX: number
  screenY: number
  point: MonitoringActuatorHistoryPoint
  type: "transition" | "data"
}

interface ViewState {
  scale: number
  offsetX: number
}

export function ActuatorStateHistoryChart({
  points,
  gaps,
  actuatorName,
}: {
  points: MonitoringActuatorHistoryPoint[]
  gaps: MonitoringActuatorHistoryGap[]
  actuatorName: string
}) {
  if (points.length === 0) {
    return (
      <div className="flex min-h-64 items-center justify-center rounded-lg border border-dashed bg-muted/20 p-6 text-center text-sm text-muted-foreground">
        Chưa có lịch sử bật/tắt.
      </div>
    )
  }

  return (
    <ActuatorStateHistoryChartContent
      points={points}
      gaps={gaps}
      actuatorName={actuatorName}
    />
  )
}

function ActuatorStateHistoryChartContent({
  points,
  gaps,
  actuatorName,
}: {
  points: MonitoringActuatorHistoryPoint[]
  gaps: MonitoringActuatorHistoryGap[]
  actuatorName: string
}) {
  const [tooltip, setTooltip] = useState<TooltipData | null>(null)
  const [viewState, setViewState] = useState<ViewState>({ scale: 1, offsetX: 0 })
  const [isDragging, setIsDragging] = useState(false)
  const [dragStart, setDragStart] = useState({ x: 0, offsetX: 0 })
  const svgRef = useRef<SVGSVGElement>(null)

  const timestamps = points.map((point) => parseApiDate(point.recorded_at).getTime())
    const start = Math.min(...timestamps)
    const end = Math.max(...timestamps)
    const timeRange = end - start || 1

    const chartLeft = 68
    const chartRight = 696
    const chartWidth = chartRight - chartLeft

    const visibleWidth = chartWidth / viewState.scale
    const maxOffsetX = chartWidth - visibleWidth
    const clampedOffsetX = Math.max(0, Math.min(maxOffsetX, viewState.offsetX))

    const toX = (timestamp: string) => {
      const ts = parseApiDate(timestamp).getTime()
      if (isNaN(ts)) return chartLeft
      const baseX = chartLeft + ((ts - start) / timeRange) * chartWidth
      const zoomedX = chartLeft + (baseX - chartLeft - clampedOffsetX) * viewState.scale
      return zoomedX
    }

    const toY = (state: boolean) => state ? 36 : 174

    const segments = buildActuatorChartSegments(points, gaps)

    // Tìm các điểm chuyển đổi
    const transitionPoints = points.filter((point, index) => {
      if (index === 0) return true
      const prevPoint = points[index - 1]
      if (!prevPoint) return false
      return point.state !== prevPoint.state
    })

    // Xác định loại chuyển đổi cho từng điểm
    const transitionTypes = transitionPoints.map((point, idx) => {
      if (idx === 0) return null // Điểm đầu tiên không phải chuyển đổi
      const prevState = transitionPoints[idx - 1]?.state
      if (prevState === undefined) return null
      
      return {
        point,
        fromState: prevState,
        toState: point.state,
        type: prevState ? "OFF" : "ON", // ON→OFF hoặc OFF→ON
      }
    }).filter(Boolean) as Array<{
      point: MonitoringActuatorHistoryPoint
      fromState: boolean
      toState: boolean
      type: "ON" | "OFF"
    }>

    const visibleStartTime = start + (clampedOffsetX / chartWidth) * timeRange
    const visibleEndTime = start + ((clampedOffsetX + visibleWidth) / chartWidth) * timeRange

    const handleWheel = useCallback((e: React.WheelEvent<SVGSVGElement>) => {
      e.preventDefault()
      const delta = e.deltaY > 0 ? 0.9 : 1.1
      const newScale = Math.max(1, Math.min(50, viewState.scale * delta))

      const rect = e.currentTarget.getBoundingClientRect()
      const mouseX = e.clientX - rect.left
      const chartMouseX = mouseX - chartLeft

      const newOffsetX = clampedOffsetX + (chartMouseX / viewState.scale) * (1 - viewState.scale / newScale)

      setViewState({
        scale: newScale,
        offsetX: newOffsetX,
      })
    }, [viewState.scale, clampedOffsetX])

    const handleMouseDown = useCallback((e: React.MouseEvent<SVGSVGElement>) => {
      if (e.button !== 0) return
      setIsDragging(true)
      setDragStart({ x: e.clientX, offsetX: clampedOffsetX })
    }, [clampedOffsetX])

    const handleMouseMove = useCallback((e: React.MouseEvent<SVGSVGElement>) => {
      if (!isDragging) return
      const dx = e.clientX - dragStart.x
      const newOffsetX = dragStart.offsetX - (dx / viewState.scale)
      setViewState(prev => ({
        ...prev,
        offsetX: Math.max(0, Math.min(maxOffsetX, newOffsetX)),
      }))
    }, [isDragging, dragStart, viewState.scale, maxOffsetX])

    const handleMouseUp = useCallback(() => {
      setIsDragging(false)
    }, [])

    const handleMouseLeave = useCallback(() => {
      setIsDragging(false)
      setTooltip(null)
    }, [])

    const handleResetZoom = useCallback(() => {
      setViewState({ scale: 1, offsetX: 0 })
    }, [])

    const handlePointHover = (
      e: React.MouseEvent<SVGElement>,
      point: MonitoringActuatorHistoryPoint,
      type: "transition" | "data"
    ) => {
      if (isDragging) return
      const rect = e.currentTarget.getBoundingClientRect()
      setTooltip({
        screenX: rect.left + rect.width / 2,
        screenY: rect.top,
        point,
        type,
      })
    }

    // Chỉ hiển thị label chuyển đổi khi zoom đủ lớn (>= 5x)
    const showTransitionLabels = viewState.scale >= 5

    return (
      <div className="min-h-64 w-full rounded-lg border bg-background p-2">
        <div className="mb-2 flex items-center justify-between">
          <div className="flex items-center gap-2 text-xs text-muted-foreground">
            <span>Cuộn chuột để zoom · Kéo chuột để di chuyển</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-xs text-muted-foreground">
              Zoom: {Math.round(viewState.scale * 100)}%
            </span>
            {viewState.scale > 1 && (
              <button
                onClick={handleResetZoom}
                className="rounded border px-2 py-1 text-xs hover:bg-accent"
              >
                Reset
              </button>
            )}
          </div>
        </div>

        <svg
          ref={svgRef}
          viewBox="0 0 720 220"
          preserveAspectRatio="none"
          className="h-64 w-full select-none"
          style={{ cursor: isDragging ? "grabbing" : "grab" }}
          role="img"
          aria-label={`Lịch sử trạng thái của ${actuatorName}`}
          onWheel={handleWheel}
          onMouseDown={handleMouseDown}
          onMouseMove={handleMouseMove}
          onMouseUp={handleMouseUp}
          onMouseLeave={handleMouseLeave}
        >
          <title>{`Lịch sử bật tắt của ${actuatorName}`}</title>

          <defs>
            <clipPath id="chart-area">
              <rect x={chartLeft} y="0" width={chartWidth} height="220" />
            </clipPath>
            {/* Mũi tên cho chuyển đổi ON→OFF */}
            <marker id="arrow-off" markerWidth="10" markerHeight="10" refX="5" refY="5" orient="auto">
              <path d="M0,0 L10,5 L0,10 Z" fill="#ef4444" />
            </marker>
            {/* Mũi tên cho chuyển đổi OFF→ON */}
            <marker id="arrow-on" markerWidth="10" markerHeight="10" refX="5" refY="5" orient="auto">
              <path d="M0,0 L10,5 L0,10 Z" fill="#10b981" />
            </marker>
          </defs>

          {/* Grid lines */}
          <line x1={chartLeft} x2={chartRight} y1="36" y2="36" stroke="currentColor" opacity="0.12" />
          <line x1={chartLeft} x2={chartRight} y1="174" y2="174" stroke="currentColor" opacity="0.12" />

          {/* Y-axis labels */}
          <text x="58" y="40" textAnchor="end" fontSize="12" fill="currentColor" fontWeight="600">
            Bật
          </text>
          <text x="58" y="178" textAnchor="end" fontSize="12" fill="currentColor" fontWeight="600">
            Tắt
          </text>

          <g clipPath="url(#chart-area)">
            {/* Gap regions */}
            {gaps && gaps.map((gap) => {
              const gapFrom = parseApiDate(gap.from).getTime()
              const gapTo = parseApiDate(gap.to).getTime()
              if (isNaN(gapFrom) || isNaN(gapTo)) return null

              const x1 = toX(gap.from)
              const x2 = toX(gap.to)
              if (x2 < chartLeft || x1 > chartRight) return null

              return (
                <g key={`${gap.from}-${gap.to}`}>
                  <rect
                    x={x1}
                    y="24"
                    width={Math.max(2, x2 - x1)}
                    height="162"
                    fill="currentColor"
                    opacity="0.06"
                  />
                </g>
              )
            })}

            {/* State segments - Đường ngang thể hiện trạng thái */}
            {segments.map((segment) => {
              const fromX = toX(segment.from.recorded_at)
              const toXValue = toX(segment.to.recorded_at)
              
              if (toXValue < chartLeft || fromX > chartRight) return null

              const stateColor = segment.from.state ? "#10b981" : "#6b7280"

              return (
                <path
                  key={`segment-${segment.from.recorded_at}`}
                  d={`M${fromX},${toY(segment.from.state)} H${toXValue}`}
                  fill="none"
                  stroke={stateColor}
                  strokeWidth="3"
                  strokeLinecap="round"
                  vectorEffect="non-scaling-stroke"
                />
              )
            })}

            {/* Transition lines - Đường dọc thể hiện chuyển đổi (NỔI BẬT) */}
            {transitionTypes.map(({ point, fromState, toState, type }) => {
              const x = toX(point.recorded_at)
              const fromY = toY(fromState)
              const toYValue = toY(toState)
              
              if (x < chartLeft - 10 || x > chartRight + 10) return null

              const transitionColor = type === "OFF" ? "#ef4444" : "#10b981"
              const markerId = type === "OFF" ? "url(#arrow-off)" : "url(#arrow-on)"

              return (
                <g key={`transition-${point.recorded_at}`}>
                  {/* Đường chuyển đổi dày, nổi bật */}
                  <line
                    x1={x}
                    y1={fromY}
                    x2={x}
                    y2={toYValue}
                    stroke={transitionColor}
                    strokeWidth="4"
                    strokeLinecap="round"
                    vectorEffect="non-scaling-stroke"
                    markerEnd={markerId}
                  />
                  
                  {/* Vòng tròn lớn tại điểm chuyển đổi */}
                  <circle
                    cx={x}
                    cy={toYValue}
                    r="10"
                    fill={transitionColor}
                    opacity="0.3"
                  />
                  <circle
                    cx={x}
                    cy={toYValue}
                    r="6"
                    fill={transitionColor}
                    stroke="white"
                    strokeWidth="2"
                    className="cursor-pointer"
                    onMouseEnter={(e) => handlePointHover(e, point, "transition")}
                    onMouseLeave={() => setTooltip(null)}
                  />

                  {/* Label chuyển đổi (chỉ hiển thị khi zoom >= 5x) */}
                  {showTransitionLabels && (
                    <g>
                      <rect
                        x={x - 25}
                        y={toYValue - 25}
                        width="50"
                        height="16"
                        rx="3"
                        fill={transitionColor}
                        opacity="0.9"
                      />
                      <text
                        x={x}
                        y={toYValue - 14}
                        textAnchor="middle"
                        fontSize="9"
                        fontWeight="600"
                        fill="white"
                      >
                        {type === "OFF" ? "" : ""}
                      </text>
                    </g>
                  )}
                </g>
              )
            })}

            {/* Regular data points */}
            {points.map((point) => {
              const x = toX(point.recorded_at)
              const y = toY(point.state)
              
              if (x < chartLeft - 10 || x > chartRight + 10) return null

              const isTransition = transitionPoints.some(tp => tp.recorded_at === point.recorded_at)
              if (isTransition) return null

              return (
                <circle
                  key={point.recorded_at}
                  cx={x}
                  cy={y}
                  r="3"
                  fill={point.state ? "#10b981" : "#6b7280"}
                  className="cursor-pointer"
                  onMouseEnter={(e) => handlePointHover(e, point, "data")}
                  onMouseLeave={() => setTooltip(null)}
                />
              )
            })}
          </g>

          {/* Time range labels */}
          <text x={chartLeft} y="215" textAnchor="start" fontSize="10" fill="currentColor" opacity="0.6">
            {fullTimeFormatter.format(new Date(visibleStartTime))}
          </text>
          <text x={chartRight} y="215" textAnchor="end" fontSize="10" fill="currentColor" opacity="0.6">
            {fullTimeFormatter.format(new Date(visibleEndTime))}
          </text>
        </svg>

        {/* Legend */}
        <div className="mt-2 flex items-center justify-center gap-6 text-xs">
          <div className="flex items-center gap-2">
            <div className="h-3 w-3 rounded-full bg-green-500" />
            <span className="text-muted-foreground">Bật</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="h-3 w-3 rounded-full bg-gray-500" />
            <span className="text-muted-foreground">Tắt</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="h-1 w-6 bg-red-500" />
            <span className="text-muted-foreground">BẬT→TẮT</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="h-1 w-6 bg-green-500" />
            <span className="text-muted-foreground">TẮT→BẬT</span>
          </div>
        </div>

        {/* Tooltip */}
        {tooltip && typeof document !== 'undefined' && createPortal(
          <div
            className="pointer-events-none fixed z-[9999] rounded-lg border bg-background px-3 py-2 shadow-xl"
            style={{
              left: tooltip.screenX,
              top: tooltip.screenY - 10,
              transform: "translate(-50%, -100%)",
            }}
          >
            <div className="flex items-center gap-2">
              <div
                className={`h-2 w-2 rounded-full ${tooltip.point.state ? "bg-green-500" : "bg-red-500"}`}
              />
              <span className="text-xs font-semibold">
                {tooltip.point.state ? "BẬT" : "TẮT"}
              </span>
            </div>
            <div className="mt-1 text-xs text-muted-foreground">
              {fullTimeFormatter.format(parseApiDate(tooltip.point.recorded_at))}
            </div>
            {tooltip.type === "transition" && (
              <div className="mt-1 text-xs font-medium text-primary">
                Điểm chuyển đổi
              </div>
            )}
          </div>,
          document.body
        )}
      </div>
    )
}
