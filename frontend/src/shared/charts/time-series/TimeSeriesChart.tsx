import { useEffect, useMemo, useRef, useState } from "react"

import {
  buildThresholdSegments,
  isValueInRange,
} from "@/shared/charts/time-series/time-series-segments"
import { createTimeSeriesScale } from "@/shared/charts/time-series/time-series-scale"
import type { TimeSeriesChartProps } from "@/shared/charts/time-series/time-series.types"
import { TimeSeriesSvg } from "@/shared/charts/time-series/TimeSeriesSvg"
import { formatDateTime } from "@/shared/lib/date"

const statusLabels = {
  normal: "Trong ngưỡng",
  warning: "Ngoài ngưỡng",
  critical: "Ngoài ngưỡng",
  stale: "Dữ liệu cũ",
  offline: "Mất kết nối",
  "no-data": "Chưa có dữ liệu",
} as const

function formatValue(
  value: number | null | undefined,
  unit?: string,
) {
  return value == null || !Number.isFinite(value)
    ? "—"
    : `${new Intl.NumberFormat("vi-VN", {
        maximumFractionDigits: 2,
      }).format(value)}${unit ? ` ${unit}` : ""}`
}

function Metric({
  label,
  value,
  tone,
}: {
  label: string
  value: string
  tone?: "normal" | "danger" | "muted"
}) {
  const className =
    tone === "danger"
      ? "text-destructive"
      : tone === "muted"
        ? "text-muted-foreground"
        : "text-foreground"

  return (
    <div className="min-w-0 px-3 py-2">
      <div className="text-[10px] uppercase tracking-wide text-muted-foreground">
        {label}
      </div>

      <div
        className={`mt-0.5 truncate text-sm font-semibold ${className}`}
      >
        {value}
      </div>
    </div>
  )
}

export function TimeSeriesChart({
  data,
  unit,
  title,
  currentValue,
  safeMin,
  safeMax,
  status = "normal",
  rangeLabel,
  lastUpdatedAt,
  variant = "line",
  expectedIntervalMs,
  gapMultiplier = 2.5,
}: TimeSeriesChartProps) {
  const containerRef = useRef<HTMLDivElement>(null)

  const [width, setWidth] = useState(640)

  useEffect(() => {
    const container = containerRef.current

    if (!container) {
      return
    }

    const update = (nextWidth: number) => {
      setWidth(
        Math.max(
          280,
          Math.floor(nextWidth),
        ),
      )
    }

    update(
      container.getBoundingClientRect().width,
    )

    if (typeof ResizeObserver === "undefined") {
      return
    }

    const observer = new ResizeObserver(([entry]) => {
      if (entry) {
        update(entry.contentRect.width)
      }
    })

    observer.observe(container)

    return () => {
      observer.disconnect()
    }
  }, [])

  const series = useMemo(
    () =>
      buildThresholdSegments(data, {
        safeMin,
        safeMax,
        expectedIntervalMs,
        gapMultiplier,
      }),
    [
      data,
      expectedIntervalMs,
      gapMultiplier,
      safeMax,
      safeMin,
    ],
  )

  const scale = useMemo(
    () =>
      series.points.length
        ? createTimeSeriesScale(
            series.points,
            width,
            safeMin,
            safeMax,
          )
        : null,
    [
      safeMax,
      safeMin,
      series.points,
      width,
    ],
  )

  if (!scale) {
    return (
      <div className="flex min-h-40 flex-col items-center justify-center rounded-lg border border-dashed bg-muted/20 p-4 text-center">
        <span
          aria-hidden="true"
          className="mb-2 size-2.5 rounded-full bg-muted-foreground"
        />

        <div className="text-sm font-medium">
          Chưa có dữ liệu
        </div>

        <p className="mt-1 text-xs text-muted-foreground">
          Hệ thống chưa nhận được bản ghi
          {title ? ` của ${title}` : ""}.
        </p>
      </div>
    )
  }

  const values = series.points.map(
    (point) => point.value,
  )

  const shownCurrent =
    currentValue ??
    values.at(-1) ??
    null

  const average =
    values.reduce(
      (sum, value) => sum + value,
      0,
    ) / values.length

  const outside =
    shownCurrent !== null &&
    !isValueInRange(
      shownCurrent,
      safeMin,
      safeMax,
    )

  const displayedStatus =
    outside ? "critical" : status

  const statusTone =
    outside ||
    status === "warning" ||
    status === "critical"
      ? "danger"
      : status === "offline" ||
          status === "no-data"
        ? "muted"
        : "normal"

  return (
    <section className="flex min-w-0 flex-col gap-2 p-3">
      <div className="grid grid-cols-2 divide-x divide-y overflow-hidden rounded-lg border bg-muted/20 sm:grid-cols-4 sm:divide-y-0">
        <Metric
          label="Hiện tại"
          value={formatValue(
            shownCurrent,
            unit,
          )}
          tone={statusTone}
        />

        <Metric
          label="Trung bình"
          value={formatValue(
            average,
            unit,
          )}
        />

        <Metric
          label="Min / Max"
          value={`${formatValue(
            Math.min(...values),
            unit,
          )} / ${formatValue(
            Math.max(...values),
            unit,
          )}`}
        />

        <Metric
          label="Trạng thái"
          value={
            statusLabels[
              displayedStatus
            ]
          }
          tone={statusTone}
        />
      </div>

      <p className="sr-only">
        {title ? `${title}. ` : ""}
        Giá trị hiện tại{" "}
        {formatValue(
          shownCurrent,
          unit,
        )}
        . Trạng thái{" "}
        {
          statusLabels[
            displayedStatus
          ]
        }
        .
        {rangeLabel
          ? ` Khoảng thời gian ${rangeLabel}.`
          : ""}
        {series.gaps.length
          ? ` Có ${series.gaps.length} khoảng mất dữ liệu.`
          : ""}
        {lastUpdatedAt
          ? ` Cập nhật ${formatDateTime(lastUpdatedAt)}.`
          : ""}
      </p>

      <div
        ref={containerRef}
        className="w-full min-w-0 overflow-hidden rounded-lg border bg-background p-1.5"
      >
        <TimeSeriesSvg
          series={series}
          scale={scale}
          safeMin={safeMin}
          safeMax={safeMax}
          step={
            variant === "step" ||
            variant === "state"
          }
          title={
            title
              ? `Biểu đồ ${title}`
              : "Biểu đồ cảm biến"
          }
          unit={unit}
        />
      </div>
    </section>
  )
}