import {
  useCallback,
  useId,
  useState,
} from "react"

import type { PointerEvent as ReactPointerEvent } from "react"

import type { SegmentedTimeSeries } from "@/shared/charts/time-series/time-series.types"
import type { TimeSeriesScale } from "@/shared/charts/time-series/time-series-scale"

const axisFormatter = new Intl.DateTimeFormat(
  "vi-VN",
  {
    day: "2-digit",
    month: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  },
)

const tooltipDateFormatter = new Intl.DateTimeFormat(
  "vi-VN",
  {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hour12: false,
  },
)

/**
 * Khoảng cách tối đa từ con trỏ đến một data point
 * để tooltip được kích hoạt.
 *
 * 12 px đủ dễ hover nhưng vẫn bắt buộc chuột phải
 * thực sự nằm gần đường/điểm dữ liệu.
 */
const HIT_RADIUS = 12

const TOOLTIP_WIDTH = 205
const TOOLTIP_HEIGHT = 62
const TOOLTIP_OFFSET = 12

type ChartPoint = {
  timestamp: number
  value: number
}

type HoveredPoint = ChartPoint & {
  x: number
  y: number
}

function formatValue(
  value: number,
  unit?: string,
) {
  const formatted =
    new Intl.NumberFormat(
      "vi-VN",
      {
        maximumFractionDigits: 2,
      },
    ).format(value)

  return unit
    ? `${formatted} ${unit}`
    : formatted
}

function path(
  points: ChartPoint[],
  scale: TimeSeriesScale,
  step: boolean,
) {
  return points
    .map(
      (
        point,
        index,
      ) => {
        const x =
          scale.toX(
            point.timestamp,
          )

        const y =
          scale.toY(
            point.value,
          )

        if (!index) {
          return `M${x},${y}`
        }

        if (step) {
          const previous =
            points[index - 1]

          return `L${x},${scale.toY(previous.value)} L${x},${y}`
        }

        return `L${x},${y}`
      },
    )
    .join(" ")
}

/**
 * Chuyển vị trí pointer từ browser coordinate
 * sang coordinate thật của SVG.
 *
 * Dùng getScreenCTM() thay vì lấy tỷ lệ width thủ công,
 * nên vẫn đúng khi SVG responsive / viewBox scale.
 */
function getSvgPointerPosition(
  svg: SVGSVGElement,
  clientX: number,
  clientY: number,
) {
  const matrix =
    svg.getScreenCTM()

  if (!matrix) {
    return null
  }

  const point =
    svg.createSVGPoint()

  point.x = clientX
  point.y = clientY

  const transformed =
    point.matrixTransform(
      matrix.inverse(),
    )

  return {
    x: transformed.x,
    y: transformed.y,
  }
}

/**
 * Tìm data point có X gần con trỏ nhất.
 *
 * series.points đã theo thứ tự thời gian nên scale.toX()
 * cũng tăng dần. Binary search giúp vẫn nhanh với hàng
 * nghìn telemetry points.
 */
function findNearestPointByX(
  points: ChartPoint[],
  pointerX: number,
  scale: TimeSeriesScale,
) {
  if (
    points.length === 0
  ) {
    return null
  }

  if (
    points.length === 1
  ) {
    return (
      points[0] ?? null
    )
  }

  let left = 0
  let right =
    points.length - 1

  while (
    left <= right
  ) {
    const middle =
      Math.floor(
        (left + right) / 2,
      )

    const point =
      points[middle]

    if (!point) {
      break
    }

    const x =
      scale.toX(
        point.timestamp,
      )

    if (
      Math.abs(
        x - pointerX,
      ) < 0.001
    ) {
      return point
    }

    if (
      x < pointerX
    ) {
      left =
        middle + 1
    } else {
      right =
        middle - 1
    }
  }

  const before =
    points[
      Math.max(
        0,
        right,
      )
    ]

  const after =
    points[
      Math.min(
        points.length - 1,
        left,
      )
    ]

  if (!before) {
    return after ?? null
  }

  if (!after) {
    return before
  }

  const beforeDistance =
    Math.abs(
      scale.toX(
        before.timestamp,
      ) -
        pointerX,
    )

  const afterDistance =
    Math.abs(
      scale.toX(
        after.timestamp,
      ) -
        pointerX,
    )

  return beforeDistance <=
    afterDistance
    ? before
    : after
}

export function TimeSeriesSvg({
  series,
  scale,
  safeMin,
  safeMax,
  step = false,
  title = "Biểu đồ cảm biến",
  unit,
}: {
  series: SegmentedTimeSeries
  scale: TimeSeriesScale
  safeMin?: number | null
  safeMax?: number | null
  step?: boolean
  title?: string
  unit?: string
}) {
  const patternId =
    useId().replaceAll(
      ":",
      "",
    )

  const [
    hoveredPoint,
    setHoveredPoint,
  ] =
    useState<HoveredPoint | null>(
      null,
    )

  const labels =
    series.points.length <= 5
      ? series.points
      : [
          series.points[0],
          series.points[
            Math.floor(
              series.points.length /
                2,
            )
          ],
          series.points.at(
            -1,
          )!,
        ]

  /**
   * Hover chỉ được kích hoạt nếu con trỏ thật sự
   * nằm gần data point cả theo X lẫn Y.
   */
  const handlePointerMove =
    useCallback(
      (
        event: ReactPointerEvent<SVGSVGElement>,
      ) => {
        if (
          series.points.length ===
          0
        ) {
          setHoveredPoint(
            null,
          )
          return
        }

        const pointer =
          getSvgPointerPosition(
            event.currentTarget,
            event.clientX,
            event.clientY,
          )

        if (!pointer) {
          setHoveredPoint(
            null,
          )
          return
        }

        /**
         * Nếu pointer ở ngoài vùng plot,
         * không hiển thị tooltip.
         */
        if (
          pointer.x <
            scale.plotLeft ||
          pointer.x >
            scale.plotRight ||
          pointer.y <
            scale.plotTop ||
          pointer.y >
            scale.plotBottom
        ) {
          setHoveredPoint(
            null,
          )
          return
        }

        const nearest =
          findNearestPointByX(
            series.points,
            pointer.x,
            scale,
          )

        if (!nearest) {
          setHoveredPoint(
            null,
          )
          return
        }

        const pointX =
          scale.toX(
            nearest.timestamp,
          )

        const pointY =
          scale.toY(
            nearest.value,
          )

        /**
         * Đây là phần quan trọng:
         *
         * Không chỉ xét X.
         * Phải xét khoảng cách 2D từ chuột -> data point.
         */
        const dx =
          pointer.x - pointX

        const dy =
          pointer.y - pointY

        const distance =
          Math.sqrt(
            dx * dx +
              dy * dy,
          )

        if (
          distance >
          HIT_RADIUS
        ) {
          setHoveredPoint(
            null,
          )
          return
        }

        setHoveredPoint({
          timestamp:
            nearest.timestamp,
          value:
            nearest.value,
          x: pointX,
          y: pointY,
        })
      },
      [
        scale,
        series.points,
      ],
    )

  const handlePointerLeave =
    useCallback(() => {
      setHoveredPoint(
        null,
      )
    }, [])

  /**
   * Tính vị trí tooltip theo data point.
   *
   * Nếu bên phải không đủ chỗ -> chuyển sang trái.
   * Nếu phía trên không đủ chỗ -> đưa xuống dưới.
   */
  let tooltipX = 0
  let tooltipY = 0

  if (hoveredPoint) {
    const canShowRight =
      hoveredPoint.x +
        TOOLTIP_OFFSET +
        TOOLTIP_WIDTH <
      scale.width

    tooltipX =
      canShowRight
        ? hoveredPoint.x +
          TOOLTIP_OFFSET
        : hoveredPoint.x -
          TOOLTIP_WIDTH -
          TOOLTIP_OFFSET

    tooltipX =
      Math.max(
        4,
        Math.min(
          scale.width -
            TOOLTIP_WIDTH -
            4,
          tooltipX,
        ),
      )

    const canShowAbove =
      hoveredPoint.y -
        TOOLTIP_HEIGHT -
        TOOLTIP_OFFSET >
      0

    tooltipY =
      canShowAbove
        ? hoveredPoint.y -
          TOOLTIP_HEIGHT -
          TOOLTIP_OFFSET
        : hoveredPoint.y +
          TOOLTIP_OFFSET

    tooltipY =
      Math.max(
        4,
        Math.min(
          scale.height -
            TOOLTIP_HEIGHT -
            4,
          tooltipY,
        ),
      )
  }

  return (
    <svg
      viewBox={`0 0 ${scale.width} ${scale.height}`}
      preserveAspectRatio="xMidYMid meet"
      className="block h-auto w-full"
      role="img"
      aria-label={title}
      onPointerMove={
        handlePointerMove
      }
      onPointerLeave={
        handlePointerLeave
      }
    >
      <title>
        {title}
      </title>

      <defs>
        <pattern
          id={`gap-${patternId}`}
          width="7"
          height="7"
          patternUnits="userSpaceOnUse"
          patternTransform="rotate(45)"
        >
          <line
            x1="0"
            y1="0"
            x2="0"
            y2="7"
            stroke="currentColor"
            strokeWidth="1"
            opacity="0.18"
          />
        </pattern>
      </defs>

      {/* ======================================================== */}
      {/* Horizontal grid + Y labels                              */}
      {/* ======================================================== */}

      {Array.from({
        length: 4,
      }).map(
        (_, index) => {
          const ratio =
            index / 3

          const y =
            scale.plotTop +
            ratio *
              (scale.plotBottom -
                scale.plotTop)

          const value =
            scale.max -
            ratio *
              (scale.max -
                scale.min)

          return (
            <g key={index}>
              <line
                x1={
                  scale.plotLeft
                }
                x2={
                  scale.plotRight
                }
                y1={y}
                y2={y}
                stroke="#a7f3d0"
                strokeDasharray="3 5"
              />

              <text
                x={
                  scale.plotLeft -
                  6
                }
                y={y + 3}
                textAnchor="end"
                fontSize="9"
                fill="#065f46"
              >
                {value.toFixed(
                  2,
                )}
              </text>
            </g>
          )
        },
      )}

      {/* ======================================================== */}
      {/* Gaps                                                     */}
      {/* ======================================================== */}

      {series.gaps.map(
        (gap) => {
          const x =
            scale.toX(
              gap.start
                .timestamp,
            )

          const endX =
            scale.toX(
              gap.end
                .timestamp,
            )

          return (
            <rect
              key={gap.id}
              x={x}
              y={
                scale.plotTop
              }
              width={Math.max(
                1,
                endX - x,
              )}
              height={
                scale.plotBottom -
                scale.plotTop
              }
              fill={`url(#gap-${patternId})`}
            >
              <title>
                {`Mất dữ liệu ${Math.round(
                  gap.durationMs /
                    60_000,
                )} phút`}
              </title>
            </rect>
          )
        },
      )}

      {/* ======================================================== */}
      {/* Thresholds                                               */}
      {/* ======================================================== */}

      {[
        {
          value: safeMin,
          label:
            "Ngưỡng dưới",
        },
        {
          value: safeMax,
          label:
            "Ngưỡng trên",
        },
      ].map(
        ({
          value,
          label,
        }) =>
          value == null ? null : (
            <line
              key={label}
              x1={
                scale.plotLeft
              }
              x2={
                scale.plotRight
              }
              y1={scale.toY(
                value,
              )}
              y2={scale.toY(
                value,
              )}
              stroke="#64748b"
              strokeDasharray="6 5"
            >
              <title>
                {`${label}: ${value}`}
              </title>
            </line>
          ),
      )}

      {/* ======================================================== */}
      {/* Sensor lines                                             */}
      {/* ======================================================== */}

      {series.segments.map(
        (segment) =>
          segment.points
            .length ===
          1 ? (
            <circle
              key={
                segment.id
              }
              cx={scale.toX(
                segment
                  .points[0]
                  .timestamp,
              )}
              cy={scale.toY(
                segment
                  .points[0]
                  .value,
              )}
              r="3.5"
              fill={
                segment.tone ===
                "in-range"
                  ? "#10b981"
                  : "#ef4444"
              }
            />
          ) : (
            <path
              key={
                segment.id
              }
              d={path(
                segment.points,
                scale,
                step,
              )}
              fill="none"
              stroke={
                segment.tone ===
                "in-range"
                  ? "#10b981"
                  : "#ef4444"
              }
              strokeWidth="2"
              strokeLinejoin="round"
              strokeLinecap="round"
              vectorEffect="non-scaling-stroke"
            />
          ),
      )}

      {/* ======================================================== */}
      {/* X axis labels                                            */}
      {/* ======================================================== */}

      {labels.map(
        (point) => (
          <text
            key={
              point.timestamp
            }
            x={scale.toX(
              point.timestamp,
            )}
            y={
              scale.height -
              10
            }
            textAnchor="middle"
            fontSize="9"
            fill="#065f46"
          >
            {axisFormatter.format(
              new Date(
                point.timestamp,
              ),
            )}
          </text>
        ),
      )}

      {/* ======================================================== */}
      {/* Hovered real point                                       */}
      {/* ======================================================== */}

      {hoveredPoint ? (
        <g
          pointerEvents="none"
        >
          {/* vòng ngoài */}

          <circle
            cx={
              hoveredPoint.x
            }
            cy={
              hoveredPoint.y
            }
            r="7"
            fill="white"
            stroke="#0f172a"
            strokeWidth="1.5"
            opacity="0.95"
          />

          {/* điểm dữ liệu */}

          <circle
            cx={
              hoveredPoint.x
            }
            cy={
              hoveredPoint.y
            }
            r="3.5"
            fill="#10b981"
          />

          {/* ==================================================== */}
          {/* Tooltip                                               */}
          {/* ==================================================== */}

          <g
            transform={`translate(${tooltipX}, ${tooltipY})`}
          >
            <rect
              x="0"
              y="0"
              width={
                TOOLTIP_WIDTH
              }
              height={
                TOOLTIP_HEIGHT
              }
              rx="6"
              fill="var(--popover, white)"
              stroke="var(--border, #d1d5db)"
              strokeWidth="1"
            />

            <text
              x="10"
              y="19"
              fontSize="10"
              fontWeight="500"
              fill="var(--muted-foreground, #64748b)"
            >
              {tooltipDateFormatter.format(
                new Date(
                  hoveredPoint.timestamp,
                ),
              )}
            </text>

            <line
              x1="10"
              x2={
                TOOLTIP_WIDTH -
                10
              }
              y1="29"
              y2="29"
              stroke="var(--border, #e5e7eb)"
              strokeWidth="1"
            />

            <text
              x="10"
              y="48"
              fontSize="11"
              fill="var(--muted-foreground, #64748b)"
            >
              Giá trị
            </text>

            <text
              x={
                TOOLTIP_WIDTH -
                10
              }
              y="48"
              textAnchor="end"
              fontSize="12"
              fontWeight="700"
              fill="var(--popover-foreground, #0f172a)"
            >
              {formatValue(
                hoveredPoint.value,
                unit,
              )}
            </text>
          </g>
        </g>
      ) : null}
    </svg>
  )
}