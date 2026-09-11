import {
  useEffect,
  useMemo,
  useRef,
  useState,
  type PointerEvent,
} from "react";

import type {
  MonitoringActuatorElectricalPoint,
  MonitoringActuatorHistoryPoint,
} from "@/api/contracts";
import { actuatorStateLabel } from "@/entities/actuator/lib/actuator-semantics";
import {
  buildActuatorOperationTimeline,
  type ActuatorOperationPoint,
} from "../lib/actuator-operation-timeline";

const DAY_MS = 24 * 60 * 60 * 1000;
const HOUR_MS = 60 * 60 * 1000;
const MINUTE_MS = 60 * 1000;
const Y_TICKS = [0, 2, 4, 6, 8, 10, 12];
const MAX_STATE_BUCKETS = 480;
const MIN_TIME_TICK_GAP_PX = 118;
const ELECTRICAL_BUCKET_PX = 2;
const MIN_VIEWPORT_MS = 60 * 1000;

interface Props {
  actuatorName: string;
  states: MonitoringActuatorHistoryPoint[];
  readings: MonitoringActuatorElectricalPoint[];
  startTime?: string;
  endTime?: string;
}

export type StateInterval = {
  start: number;
  end: number;
  state: boolean | null;
};

export type StateRibbonKind = "ON" | "OFF" | "UNKNOWN" | "MIXED";

export type StateRibbonSegment = {
  start: number;
  end: number;
  kind: StateRibbonKind;
  onDuration: number;
  offDuration: number;
  unknownDuration: number;
  transitionCount: number;
};

type Viewport = {
  start: number;
  end: number;
};

type ChartSize = {
  width: number;
  height: number;
  dpr: number;
};

type ChartMetrics = ChartSize & {
  left: number;
  right: number;
  top: number;
  bottom: number;
  plotWidth: number;
  plotHeight: number;
  stateTop: number;
  stateHeight: number;
};

type ThemePalette = {
  foreground: string;
  mutedForeground: string;
  border: string;
  muted: string;
  background: string;
  primary: string;
  primaryForeground: string;
  voltage: string;
  current: string;
  destructive: string;
};

type DragState = {
  pointerId: number;
  startClientX: number;
  viewport: Viewport;
  moved: boolean;
};

type PendingPointer = {
  clientX: number;
  clientY: number;
};

export function ActuatorOperationChart({
  actuatorName,
  states,
  readings,
  startTime,
  endTime,
}: Props) {
  const points = useMemo(
    () => buildActuatorOperationTimeline(states, readings),
    [states, readings],
  );

  const fullDomain = useMemo(
    () => resolveFullDomain(points, startTime, endTime),
    [points, startTime, endTime],
  );

  const [viewport, setViewport] = useState<Viewport>(fullDomain);
  const [chartSize, setChartSize] = useState<ChartSize>({
    width: 960,
    height: 420,
    dpr: 1,
  });
  const [activeIndex, setActiveIndex] = useState<number | null>(null);

  const containerRef = useRef<HTMLDivElement | null>(null);
  const baseCanvasRef = useRef<HTMLCanvasElement | null>(null);
  const overlayCanvasRef = useRef<HTMLCanvasElement | null>(null);
  const previousFullDomainRef = useRef(fullDomain);
  const viewportRef = useRef(viewport);
  const activeIndexRef = useRef<number | null>(null);
  const dragRef = useRef<DragState | null>(null);
  const pendingPointerRef = useRef<PendingPointer | null>(null);
  const pointerRafRef = useRef<number | null>(null);
  const panRafRef = useRef<number | null>(null);
  const pendingPanXRef = useRef<number | null>(null);

  useEffect(() => {
    viewportRef.current = viewport;
  }, [viewport]);

  useEffect(() => {
    activeIndexRef.current = activeIndex;
  }, [activeIndex]);

  useEffect(() => {
    const canvas = overlayCanvasRef.current;
    if (!canvas || !points.length || !isFiniteViewport(fullDomain)) return;

    const handleWheelNative = (event: WheelEvent) => {
      // Wheel/trackpad gestures that start over the chart belong exclusively
      // to the chart. A non-passive native listener is required so browsers
      // actually honor preventDefault() and do not scroll the page behind it.
      event.preventDefault();
      event.stopPropagation();

      const rect = canvas.getBoundingClientRect();
      const pointerRatio = clamp(
        (event.clientX - rect.left) / Math.max(1, rect.width),
        0,
        1,
      );
      const current = viewportRef.current;
      const currentSpan = current.end - current.start;
      const fullSpan = fullDomain.end - fullDomain.start;
      if (currentSpan <= 0 || fullSpan <= 0) return;

      const deltaY = normalizeWheelDelta(event);
      const zoomFactor = Math.exp(deltaY * 0.0015);
      const minimumSpan = Math.min(
        fullSpan,
        Math.max(MIN_VIEWPORT_MS, fullSpan / 4000),
      );
      const nextSpan = clamp(currentSpan * zoomFactor, minimumSpan, fullSpan);
      const anchorTime = current.start + pointerRatio * currentSpan;

      const next = clampViewport(
        {
          start: anchorTime - pointerRatio * nextSpan,
          end: anchorTime + (1 - pointerRatio) * nextSpan,
        },
        fullDomain,
      );

      viewportRef.current = next;
      setViewport(next);
    };

    canvas.addEventListener("wheel", handleWheelNative, { passive: false });
    return () => canvas.removeEventListener("wheel", handleWheelNative);
  }, [fullDomain.start, fullDomain.end, points.length]);

  useEffect(() => {
    const previous = previousFullDomainRef.current;
    previousFullDomainRef.current = fullDomain;

    setViewport((current) => {
      if (!isFiniteViewport(fullDomain)) return fullDomain;
      if (!isFiniteViewport(previous)) return fullDomain;

      const previousSpan = Math.max(1, previous.end - previous.start);
      const currentSpan = Math.max(1, current.end - current.start);
      const epsilon = Math.max(1, previousSpan * 0.002);
      const wasFullRange =
        Math.abs(current.start - previous.start) <= epsilon &&
        Math.abs(current.end - previous.end) <= epsilon;
      const wasPinnedToLatest = Math.abs(current.end - previous.end) <= epsilon;

      if (wasFullRange) return fullDomain;

      if (wasPinnedToLatest) {
        return clampViewport(
          {
            start: fullDomain.end - currentSpan,
            end: fullDomain.end,
          },
          fullDomain,
        );
      }

      return clampViewport(current, fullDomain);
    });
  }, [fullDomain.start, fullDomain.end]);

  useEffect(() => {
    const element = containerRef.current;
    if (!element) return;

    const updateSize = () => {
      const width = Math.max(280, Math.round(element.getBoundingClientRect().width));
      const height = width < 480 ? 330 : width < 760 ? 370 : 420;
      const dpr = Math.min(2, Math.max(1, window.devicePixelRatio || 1));

      setChartSize((previous) =>
        previous.width === width &&
        previous.height === height &&
        previous.dpr === dpr
          ? previous
          : { width, height, dpr },
      );
    };

    updateSize();

    if (typeof ResizeObserver === "undefined") {
      window.addEventListener("resize", updateSize);
      return () => window.removeEventListener("resize", updateSize);
    }

    const observer = new ResizeObserver(updateSize);
    observer.observe(element);
    return () => observer.disconnect();
  }, []);

  const metrics = useMemo(() => buildChartMetrics(chartSize), [chartSize]);

  const fullIntervals = useMemo(
    () => buildStateIntervals(points, fullDomain.start, fullDomain.end),
    [points, fullDomain.start, fullDomain.end],
  );

  const visibleIntervals = useMemo(
    () => clipStateIntervals(fullIntervals, viewport.start, viewport.end),
    [fullIntervals, viewport.start, viewport.end],
  );

  const ribbonSegments = useMemo(
    () =>
      buildStateRibbonSegments(
        visibleIntervals,
        viewport.start,
        viewport.end,
        metrics.plotWidth,
      ),
    [visibleIntervals, viewport.start, viewport.end, metrics.plotWidth],
  );

  const visiblePointRange = useMemo(
    () => findPointRange(points, viewport.start, viewport.end),
    [points, viewport.start, viewport.end],
  );

  const visualPoints = useMemo(
    () =>
      downsampleElectricalPoints(
        points,
        viewport.start,
        viewport.end,
        metrics.plotWidth,
      ),
    [points, viewport.start, viewport.end, metrics.plotWidth],
  );

  const timeTicks = useMemo(
    () =>
      buildAdaptiveTimeTicks(
        viewport.start,
        viewport.end,
        metrics.plotWidth,
      ),
    [viewport.start, viewport.end, metrics.plotWidth],
  );

  const stateSummary = useMemo(
    () => summarizeStateIntervals(visibleIntervals),
    [visibleIntervals],
  );

  const currentState = useMemo(
    () => findStateInterval(fullIntervals, fullDomain.end)?.state ?? null,
    [fullIntervals, fullDomain.end],
  );

  const transitionTimes = useMemo(
    () => getKnownTransitionTimes(visibleIntervals),
    [visibleIntervals],
  );

  const showTransitionLines =
    viewport.end - viewport.start <= DAY_MS &&
    transitionTimes.length > 0 &&
    transitionTimes.length <= 40;

  const rawVisibleCount = Math.max(0, visiblePointRange.end - visiblePointRange.start);
  const activePoint = activeIndex === null ? null : points[activeIndex] ?? null;
  const isZoomed = !sameViewport(viewport, fullDomain);

  useEffect(() => {
    const canvas = baseCanvasRef.current;
    const host = containerRef.current;
    if (!canvas || !host || metrics.width <= 0 || metrics.height <= 0) return;

    const palette = readThemePalette(host);
    prepareCanvas(canvas, metrics);
    drawBaseChart(canvas, {
      metrics,
      palette,
      viewport,
      visualPoints,
      ribbonSegments,
      transitionTimes: showTransitionLines ? transitionTimes : [],
      timeTicks,
    });
  }, [
    metrics,
    viewport,
    visualPoints,
    ribbonSegments,
    transitionTimes,
    showTransitionLines,
    timeTicks,
  ]);

  useEffect(() => {
    const canvas = overlayCanvasRef.current;
    if (!canvas) return;
    prepareCanvas(canvas, metrics);
    clearCanvas(canvas, metrics);

    if (activePoint && activePoint.time >= viewport.start && activePoint.time <= viewport.end) {
      drawOverlay(canvas, activePoint, metrics, viewport);
    }
  }, [metrics, viewport, activePoint]);

  useEffect(
    () => () => {
      if (pointerRafRef.current !== null) cancelAnimationFrame(pointerRafRef.current);
      if (panRafRef.current !== null) cancelAnimationFrame(panRafRef.current);
    },
    [],
  );

  if (!points.length || !isFiniteViewport(fullDomain)) {
    return (
      <div className="rounded-xl border border-dashed p-8 text-center text-sm text-muted-foreground">
        Chưa có dữ liệu vận hành trong khoảng đã chọn.
      </div>
    );
  }

  const scheduleHover = (clientX: number, clientY: number) => {
    pendingPointerRef.current = { clientX, clientY };
    if (pointerRafRef.current !== null) return;

    pointerRafRef.current = requestAnimationFrame(() => {
      pointerRafRef.current = null;
      const pending = pendingPointerRef.current;
      const canvas = overlayCanvasRef.current;
      if (!pending || !canvas) return;

      const rect = canvas.getBoundingClientRect();
      const localX = clamp(pending.clientX - rect.left, metrics.left, metrics.width - metrics.right);
      const time = xToTime(localX, metrics, viewportRef.current);
      const range = findPointRange(points, viewportRef.current.start, viewportRef.current.end);
      const index = binarySearchNearestPoint(points, time, range.start, range.end);

      clearCanvas(canvas, metrics);
      if (index === null) {
        if (activeIndexRef.current !== null) setActiveIndex(null);
        return;
      }

      const point = points[index];
      drawOverlay(canvas, point, metrics, viewportRef.current);

      if (activeIndexRef.current !== index) {
        activeIndexRef.current = index;
        setActiveIndex(index);
      }
    });
  };

  const schedulePan = (clientX: number) => {
    pendingPanXRef.current = clientX;
    if (panRafRef.current !== null) return;

    panRafRef.current = requestAnimationFrame(() => {
      panRafRef.current = null;
      const drag = dragRef.current;
      const latestX = pendingPanXRef.current;
      const canvas = overlayCanvasRef.current;
      if (!drag || latestX === null || !canvas) return;

      const rect = canvas.getBoundingClientRect();
      const dx = latestX - drag.startClientX;
      if (Math.abs(dx) >= 3) drag.moved = true;

      const span = drag.viewport.end - drag.viewport.start;
      const delta = -(dx / Math.max(1, rect.width)) * span;
      const next = clampViewport(
        {
          start: drag.viewport.start + delta,
          end: drag.viewport.end + delta,
        },
        fullDomain,
      );

      viewportRef.current = next;
      setViewport(next);
    });
  };

  const handlePointerDown = (event: PointerEvent<HTMLCanvasElement>) => {
    if (event.button !== 0) return;
    event.preventDefault();
    event.stopPropagation();
    event.currentTarget.setPointerCapture(event.pointerId);
    dragRef.current = {
      pointerId: event.pointerId,
      startClientX: event.clientX,
      viewport: viewportRef.current,
      moved: false,
    };
  };

  const handlePointerMove = (event: PointerEvent<HTMLCanvasElement>) => {
    if (dragRef.current) {
      event.preventDefault();
      event.stopPropagation();
    }
    const drag = dragRef.current;
    if (drag && drag.pointerId === event.pointerId) {
      schedulePan(event.clientX);
      return;
    }
    scheduleHover(event.clientX, event.clientY);
  };

  const handlePointerUp = (event: PointerEvent<HTMLCanvasElement>) => {
    const drag = dragRef.current;
    if (drag) {
      event.preventDefault();
      event.stopPropagation();
    }
    if (!drag || drag.pointerId !== event.pointerId) return;
    dragRef.current = null;
    pendingPanXRef.current = null;
    if (event.currentTarget.hasPointerCapture(event.pointerId)) {
      event.currentTarget.releasePointerCapture(event.pointerId);
    }
    scheduleHover(event.clientX, event.clientY);
  };

  const handlePointerLeave = () => {
    if (dragRef.current) return;
    pendingPointerRef.current = null;
    const canvas = overlayCanvasRef.current;
    if (canvas) clearCanvas(canvas, metrics);
    activeIndexRef.current = null;
    setActiveIndex(null);
  };


  const resetViewport = () => {
    viewportRef.current = fullDomain;
    setViewport(fullDomain);
  };

  return (
    <section
      className="rounded-xl border bg-card p-4 sm:p-5"
      aria-label={`Biểu đồ vận hành ${actuatorName}`}
    >
      <div className="mb-3 flex flex-wrap items-start justify-between gap-3">
        <div>
          <h3 className="text-balance text-lg font-semibold">Biểu đồ vận hành</h3>
          <p className="text-pretty text-sm text-muted-foreground">
            Trạng thái Bật/Tắt, điện áp và dòng điện theo cùng một trục thời gian.
          </p>
        </div>

        <CurrentStateBadge state={currentState} />
      </div>

      <div className="mb-3 flex flex-wrap items-center justify-between gap-3 rounded-lg border bg-muted/20 px-3 py-2">
        <div className="flex flex-wrap gap-x-4 gap-y-1 text-xs">
          <StateLegend kind="ON" label="Bật" />
          <StateLegend kind="OFF" label="Tắt" />
          <StateLegend kind="UNKNOWN" label="Không xác định" />
          <StateLegend kind="MIXED" label="Có chuyển trạng thái" />
          <Legend className="border-sky-600" label="Điện áp (V)" />
          <Legend className="border-amber-600 border-dashed" label="Dòng điện (A)" />
        </div>

        <div className="flex flex-wrap items-center gap-3 text-[11px] text-muted-foreground">
          <span>
            Bật <strong className="text-foreground">{formatDuration(stateSummary.onDuration)}</strong>
          </span>
          <span>
            Tắt <strong className="text-foreground">{formatDuration(stateSummary.offDuration)}</strong>
          </span>
          {stateSummary.unknownDuration > 0 ? (
            <span>
              Không xác định{" "}
              <strong className="text-foreground">
                {formatDuration(stateSummary.unknownDuration)}
              </strong>
            </span>
          ) : null}
        </div>
      </div>

      <div className="mb-2 flex flex-wrap items-center justify-between gap-2 text-xs text-muted-foreground">
        <div className="flex flex-wrap items-center gap-3">
          <span>{formatViewport(viewport)}</span>
        </div>
        {isZoomed ? (
          <button
            type="button"
            className="rounded-md border bg-background px-2.5 py-1 text-xs font-medium text-foreground hover:bg-muted"
            onClick={resetViewport}
          >
            Toàn khoảng
          </button>
        ) : null}
      </div>

      <div
        ref={containerRef}
        className="relative w-full overflow-hidden rounded-lg border bg-background overscroll-contain"
        style={{ height: chartSize.height, overscrollBehavior: "contain" }}
      >
        <canvas
          ref={baseCanvasRef}
          className="absolute inset-0 block h-full w-full"
          role="img"
          aria-label="Biểu đồ vận hành: dải trạng thái phía trên; điện áp và dòng điện phía dưới"
        />
        <canvas
          ref={overlayCanvasRef}
          className="absolute inset-0 block h-full w-full cursor-crosshair touch-none select-none overscroll-contain"
          style={{ touchAction: "none", overscrollBehavior: "contain" }}
          tabIndex={0}
          aria-label="Kéo ngang để di chuyển theo thời gian, cuộn chuột để phóng to hoặc thu nhỏ, nhấp đúp để trở về toàn khoảng"
          onPointerDown={handlePointerDown}
          onPointerMove={handlePointerMove}
          onPointerUp={handlePointerUp}
          onPointerCancel={handlePointerUp}
          onPointerLeave={handlePointerLeave}
          onDoubleClick={resetViewport}
          onFocus={() => {
            const range = findPointRange(points, viewport.start, viewport.end);
            const index = range.end > range.start ? range.end - 1 : null;
            if (index !== null) setActiveIndex(index);
          }}
          onBlur={() => {
            const canvas = overlayCanvasRef.current;
            if (canvas) clearCanvas(canvas, metrics);
            setActiveIndex(null);
          }}
        />

        {activePoint ? (
          <Tooltip
            point={activePoint}
            interval={findStateInterval(visibleIntervals, activePoint.time)}
            ribbonSegment={findRibbonSegment(ribbonSegments, activePoint.time)}
          />
        ) : null}
      </div>
    </section>
  );
}

export function buildStateIntervals(
  points: Pick<ActuatorOperationPoint, "time" | "reportedState">[],
  domainStart: number,
  domainEnd: number,
): StateInterval[] {
  if (domainEnd <= domainStart) return [];

  let currentState: boolean | null = null;
  for (const point of points) {
    if (!Number.isFinite(point.time)) continue;
    if (point.time > domainStart) break;
    if (point.reportedState !== null) currentState = point.reportedState;
  }

  const intervals: StateInterval[] = [];
  let cursor = domainStart;

  for (const point of points) {
    if (!Number.isFinite(point.time)) continue;
    if (point.time <= domainStart) continue;
    if (point.time > domainEnd) break;
    if (point.reportedState === null) continue;
    if (point.reportedState === currentState) continue;

    if (point.time > cursor) {
      intervals.push({ start: cursor, end: point.time, state: currentState });
    }

    cursor = point.time;
    currentState = point.reportedState;
  }

  if (cursor < domainEnd) {
    intervals.push({ start: cursor, end: domainEnd, state: currentState });
  }

  return mergeAdjacentIntervals(intervals);
}

export function buildStateRibbonSegments(
  intervals: StateInterval[],
  domainStart: number,
  domainEnd: number,
  plotWidth: number,
): StateRibbonSegment[] {
  if (!intervals.length || domainEnd <= domainStart || plotWidth <= 0) return [];

  const span = domainEnd - domainStart;
  const maxByPixels = Math.max(
    1,
    Math.min(MAX_STATE_BUCKETS, Math.floor(plotWidth / 2.5)),
  );
  const shouldAggregate = span >= 14 * DAY_MS || intervals.length > maxByPixels;

  if (!shouldAggregate) {
    return intervals.map((interval) => ({
      start: interval.start,
      end: interval.end,
      kind:
        interval.state === true
          ? "ON"
          : interval.state === false
            ? "OFF"
            : "UNKNOWN",
      onDuration: interval.state === true ? interval.end - interval.start : 0,
      offDuration: interval.state === false ? interval.end - interval.start : 0,
      unknownDuration: interval.state === null ? interval.end - interval.start : 0,
      transitionCount: 0,
    }));
  }

  const bucketCount = maxByPixels;
  const bucketSize = span / bucketCount;
  const transitions = getKnownTransitionTimes(intervals);
  const buckets: StateRibbonSegment[] = [];
  let intervalIndex = 0;
  let transitionIndex = 0;

  for (let bucketIndex = 0; bucketIndex < bucketCount; bucketIndex += 1) {
    const start = domainStart + bucketIndex * bucketSize;
    const end =
      bucketIndex === bucketCount - 1
        ? domainEnd
        : domainStart + (bucketIndex + 1) * bucketSize;

    while (intervalIndex < intervals.length && intervals[intervalIndex].end <= start) {
      intervalIndex += 1;
    }

    let onDuration = 0;
    let offDuration = 0;
    let unknownDuration = 0;
    let scanIndex = intervalIndex;

    while (scanIndex < intervals.length && intervals[scanIndex].start < end) {
      const interval = intervals[scanIndex];
      const overlapStart = Math.max(start, interval.start);
      const overlapEnd = Math.min(end, interval.end);
      const duration = Math.max(0, overlapEnd - overlapStart);

      if (interval.state === true) onDuration += duration;
      else if (interval.state === false) offDuration += duration;
      else unknownDuration += duration;

      if (interval.end <= end) scanIndex += 1;
      else break;
    }

    while (transitionIndex < transitions.length && transitions[transitionIndex] <= start) {
      transitionIndex += 1;
    }
    let transitionScan = transitionIndex;
    let transitionCount = 0;
    while (transitionScan < transitions.length && transitions[transitionScan] <= end) {
      transitionCount += 1;
      transitionScan += 1;
    }
    transitionIndex = transitionScan;

    const presentKinds = [onDuration > 0, offDuration > 0, unknownDuration > 0].filter(Boolean).length;
    let kind: StateRibbonKind = "UNKNOWN";
    if (presentKinds > 1) kind = "MIXED";
    else if (onDuration > 0) kind = "ON";
    else if (offDuration > 0) kind = "OFF";

    buckets.push({
      start,
      end,
      kind,
      onDuration,
      offDuration,
      unknownDuration,
      transitionCount,
    });
  }

  return mergeRibbonBuckets(buckets);
}

/**
 * Pixel-aware min/max conflation.
 *
 * Mỗi bucket rộng khoảng 2 px giữ FIRST/LAST và cực trị của cả voltage/current.
 * Vì vậy số điểm render bị chặn theo chiều rộng màn hình thay vì tăng tuyến tính
 * theo số ngày, nhưng spike điện áp/dòng điện vẫn không bị average làm mất.
 */
export function downsampleElectricalPoints(
  points: ActuatorOperationPoint[],
  domainStart: number,
  domainEnd: number,
  plotWidth: number,
): ActuatorOperationPoint[] {
  if (!points.length || domainEnd <= domainStart || plotWidth <= 0) return [];

  const range = findPointRange(points, domainStart, domainEnd);
  if (range.end <= range.start) return [];

  const bucketCount = Math.max(1, Math.floor(plotWidth / ELECTRICAL_BUCKET_PX));
  const span = domainEnd - domainStart;
  const bucketSize = span / bucketCount;
  const output: ActuatorOperationPoint[] = [];

  let currentBucket = -1;
  let first: ActuatorOperationPoint | null = null;
  let last: ActuatorOperationPoint | null = null;
  let minVoltage: ActuatorOperationPoint | null = null;
  let maxVoltage: ActuatorOperationPoint | null = null;
  let minCurrent: ActuatorOperationPoint | null = null;
  let maxCurrent: ActuatorOperationPoint | null = null;

  const flush = () => {
    if (!first) return;
    const candidates = [first, minVoltage, maxVoltage, minCurrent, maxCurrent, last]
      .filter((point): point is ActuatorOperationPoint => point !== null)
      .sort((a, b) => a.time - b.time);

    let previous: ActuatorOperationPoint | null = null;
    for (const candidate of candidates) {
      if (previous === candidate) continue;
      const tail = output.at(-1);
      if (tail === candidate) continue;
      output.push(candidate);
      previous = candidate;
    }
  };

  const resetBucket = (point: ActuatorOperationPoint, bucket: number) => {
    currentBucket = bucket;
    first = point;
    last = point;
    minVoltage = validElectricalValue(point.voltageVisual) ? point : null;
    maxVoltage = validElectricalValue(point.voltageVisual) ? point : null;
    minCurrent = validElectricalValue(point.currentVisual) ? point : null;
    maxCurrent = validElectricalValue(point.currentVisual) ? point : null;
  };

  for (let index = range.start; index < range.end; index += 1) {
    const point = points[index];
    if (!point.hasElectricalReading) continue;
    if (!validElectricalValue(point.voltageVisual) && !validElectricalValue(point.currentVisual)) continue;

    const bucket = clamp(
      Math.floor((point.time - domainStart) / Math.max(1, bucketSize)),
      0,
      bucketCount - 1,
    );

    if (currentBucket !== bucket) {
      flush();
      resetBucket(point, bucket);
      continue;
    }

    last = point;

    if (validElectricalValue(point.voltageVisual)) {
      if (!minVoltage || point.voltageVisual! < minVoltage.voltageVisual!) minVoltage = point;
      if (!maxVoltage || point.voltageVisual! > maxVoltage.voltageVisual!) maxVoltage = point;
    }

    if (validElectricalValue(point.currentVisual)) {
      if (!minCurrent || point.currentVisual! < minCurrent.currentVisual!) minCurrent = point;
      if (!maxCurrent || point.currentVisual! > maxCurrent.currentVisual!) maxCurrent = point;
    }
  }

  flush();
  return output;
}

export function buildAdaptiveTimeTicks(
  start: number,
  end: number,
  plotWidth: number,
) {
  if (end <= start) return [start];

  const span = end - start;
  const maxLabels = clamp(Math.floor(plotWidth / MIN_TIME_TICK_GAP_PX), 3, 10);
  const targetStep = span / Math.max(1, maxLabels - 1);
  const step = chooseNiceTimeStep(targetStep);
  const ticks: number[] = [start];

  let cursor = start + step;
  while (cursor < end - step * 0.35) {
    ticks.push(cursor);
    cursor += step;
  }

  if (end - ticks.at(-1)! > step * 0.2) ticks.push(end);
  else ticks[ticks.length - 1] = end;

  return ticks;
}

function resolveFullDomain(
  points: ActuatorOperationPoint[],
  startTime?: string,
  endTime?: string,
): Viewport {
  if (!points.length) return { start: 0, end: 1 };

  const rawStart = parseTime(startTime);
  const rawEnd = parseTime(endTime);
  const firstTime = points[0].time;
  const lastTime = points.at(-1)!.time;
  const start = Number.isFinite(rawStart) ? rawStart : firstTime;
  const requestedEnd = Number.isFinite(rawEnd) ? rawEnd : lastTime;
  const end = requestedEnd > start ? requestedEnd : Math.max(start + 1, lastTime);

  return { start, end };
}

function buildChartMetrics(size: ChartSize): ChartMetrics {
  const compact = size.width < 520;
  const left = compact ? 46 : 58;
  const right = compact ? 10 : 16;
  const top = compact ? 88 : 94;
  const bottom = compact ? 48 : 52;
  const stateTop = compact ? 28 : 32;
  const stateHeight = compact ? 28 : 30;

  return {
    ...size,
    left,
    right,
    top,
    bottom,
    stateTop,
    stateHeight,
    plotWidth: Math.max(1, size.width - left - right),
    plotHeight: Math.max(1, size.height - top - bottom),
  };
}

function prepareCanvas(canvas: HTMLCanvasElement, metrics: ChartMetrics) {
  const bitmapWidth = Math.max(1, Math.round(metrics.width * metrics.dpr));
  const bitmapHeight = Math.max(1, Math.round(metrics.height * metrics.dpr));

  if (canvas.width !== bitmapWidth) canvas.width = bitmapWidth;
  if (canvas.height !== bitmapHeight) canvas.height = bitmapHeight;
  canvas.style.width = `${metrics.width}px`;
  canvas.style.height = `${metrics.height}px`;

  const ctx = canvas.getContext("2d");
  if (!ctx) return;
  ctx.setTransform(metrics.dpr, 0, 0, metrics.dpr, 0, 0);
}

function clearCanvas(canvas: HTMLCanvasElement, metrics: ChartMetrics) {
  const ctx = canvas.getContext("2d");
  if (!ctx) return;
  ctx.setTransform(metrics.dpr, 0, 0, metrics.dpr, 0, 0);
  ctx.clearRect(0, 0, metrics.width, metrics.height);
}

function drawBaseChart(
  canvas: HTMLCanvasElement,
  args: {
    metrics: ChartMetrics;
    palette: ThemePalette;
    viewport: Viewport;
    visualPoints: ActuatorOperationPoint[];
    ribbonSegments: StateRibbonSegment[];
    transitionTimes: number[];
    timeTicks: number[];
  },
) {
  const { metrics, palette, viewport, visualPoints, ribbonSegments, transitionTimes, timeTicks } = args;
  const ctx = canvas.getContext("2d");
  if (!ctx) return;

  ctx.setTransform(metrics.dpr, 0, 0, metrics.dpr, 0, 0);
  ctx.clearRect(0, 0, metrics.width, metrics.height);
  ctx.lineCap = "round";
  ctx.lineJoin = "round";
  ctx.font = "11px ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, Segoe UI, sans-serif";

  drawStateLane(ctx, metrics, palette, viewport, ribbonSegments);
  drawGridAndAxes(ctx, metrics, palette, viewport, timeTicks);

  if (transitionTimes.length) {
    ctx.save();
    ctx.strokeStyle = palette.mutedForeground;
    ctx.globalAlpha = 0.18;
    ctx.setLineDash([2, 5]);
    for (const time of transitionTimes) {
      const x = timeToX(time, metrics, viewport);
      ctx.beginPath();
      ctx.moveTo(x, metrics.stateTop + metrics.stateHeight);
      ctx.lineTo(x, metrics.height - metrics.bottom);
      ctx.stroke();
    }
    ctx.restore();
  }

  drawElectricalSeries(ctx, visualPoints, metrics, viewport, "voltageVisual", palette.voltage, false);
  drawElectricalSeries(ctx, visualPoints, metrics, viewport, "currentVisual", palette.current, true);
  drawOverflowMarkers(ctx, visualPoints, metrics, viewport, palette.destructive);
}

function drawStateLane(
  ctx: CanvasRenderingContext2D,
  metrics: ChartMetrics,
  palette: ThemePalette,
  viewport: Viewport,
  segments: StateRibbonSegment[],
) {
  ctx.save();
  ctx.fillStyle = palette.mutedForeground;
  ctx.font = "600 10px ui-sans-serif, system-ui, sans-serif";
  ctx.textAlign = "right";
  ctx.textBaseline = "middle";
  ctx.fillText("TRẠNG THÁI", metrics.left - 9, metrics.stateTop + metrics.stateHeight / 2);

  roundedRectPath(ctx, metrics.left, metrics.stateTop, metrics.plotWidth, metrics.stateHeight, 6);
  ctx.fillStyle = palette.background;
  ctx.fill();
  ctx.strokeStyle = palette.border;
  ctx.lineWidth = 1;
  ctx.stroke();

  for (const segment of segments) {
    const x1 = timeToX(segment.start, metrics, viewport);
    const x2 = timeToX(segment.end, metrics, viewport);
    const width = Math.max(0.75, x2 - x1);
    const y = metrics.stateTop + 1;
    const height = metrics.stateHeight - 2;

    if (segment.kind === "ON") {
      ctx.fillStyle = palette.primary;
      ctx.fillRect(x1, y, width, height);
    } else if (segment.kind === "OFF") {
      ctx.fillStyle = palette.muted;
      ctx.fillRect(x1, y, width, height);
      ctx.strokeStyle = palette.mutedForeground;
      ctx.globalAlpha = 0.45;
      ctx.strokeRect(x1 + 0.5, y + 0.5, Math.max(0, width - 1), height - 1);
      ctx.globalAlpha = 1;
    } else if (segment.kind === "UNKNOWN") {
      drawHatchedRect(ctx, x1, y, width, height, palette.muted, palette.mutedForeground, 0.55);
    } else {
      drawHatchedRect(ctx, x1, y, width, height, palette.muted, palette.primary, 0.5);
    }

    if (width >= 62 && segments.length <= 72) {
      ctx.font = "600 10px ui-sans-serif, system-ui, sans-serif";
      ctx.textAlign = "center";
      ctx.textBaseline = "middle";
      ctx.fillStyle = segment.kind === "ON" ? palette.primaryForeground : palette.foreground;
      ctx.fillText(ribbonLabel(segment.kind), x1 + width / 2, y + height / 2);
    }
  }
  ctx.restore();
}

function drawGridAndAxes(
  ctx: CanvasRenderingContext2D,
  metrics: ChartMetrics,
  palette: ThemePalette,
  viewport: Viewport,
  timeTicks: number[],
) {
  ctx.save();
  ctx.font = "11px ui-sans-serif, system-ui, sans-serif";
  ctx.textBaseline = "middle";

  for (const tick of Y_TICKS) {
    const y = valueToY(tick, metrics);
    ctx.strokeStyle = palette.border;
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.moveTo(metrics.left, y);
    ctx.lineTo(metrics.width - metrics.right, y);
    ctx.stroke();

    ctx.fillStyle = palette.mutedForeground;
    ctx.textAlign = "right";
    ctx.fillText(String(tick), metrics.left - 10, y);
  }

  ctx.strokeStyle = palette.foreground;
  ctx.lineWidth = 1;
  ctx.beginPath();
  ctx.moveTo(metrics.left, metrics.top);
  ctx.lineTo(metrics.left, metrics.height - metrics.bottom);
  ctx.lineTo(metrics.width - metrics.right, metrics.height - metrics.bottom);
  ctx.stroke();

  const span = viewport.end - viewport.start;
  for (let index = 0; index < timeTicks.length; index += 1) {
    const time = timeTicks[index];
    const x = timeToX(time, metrics, viewport);
    ctx.beginPath();
    ctx.moveTo(x, metrics.height - metrics.bottom);
    ctx.lineTo(x, metrics.height - metrics.bottom + 5);
    ctx.stroke();

    ctx.fillStyle = palette.mutedForeground;
    ctx.textBaseline = "top";
    ctx.textAlign = index === 0 ? "left" : index === timeTicks.length - 1 ? "right" : "center";
    ctx.fillText(formatTimeTick(time, span), x, metrics.height - metrics.bottom + 10);
  }

  ctx.restore();
}

function drawElectricalSeries(
  ctx: CanvasRenderingContext2D,
  points: ActuatorOperationPoint[],
  metrics: ChartMetrics,
  viewport: Viewport,
  key: "voltageVisual" | "currentVisual",
  color: string,
  dashed: boolean,
) {
  ctx.save();
  ctx.strokeStyle = color;
  ctx.lineWidth = 2.25;
  ctx.setLineDash(dashed ? [7, 4] : []);
  ctx.beginPath();

  let drawing = false;
  for (const point of points) {
    const value = point[key];
    if (!point.hasElectricalReading || !validElectricalValue(value)) {
      drawing = false;
      continue;
    }

    const x = timeToX(point.time, metrics, viewport);
    const y = valueToY(value!, metrics);
    if (!drawing) {
      ctx.moveTo(x, y);
      drawing = true;
    } else {
      ctx.lineTo(x, y);
    }
  }

  ctx.stroke();
  ctx.restore();
}

function drawOverflowMarkers(
  ctx: CanvasRenderingContext2D,
  points: ActuatorOperationPoint[],
  metrics: ChartMetrics,
  viewport: Viewport,
  color: string,
) {
  ctx.save();
  ctx.strokeStyle = color;
  ctx.lineWidth = 2;

  for (const point of points) {
    const values = [point.voltageRaw, point.currentRaw];
    for (const value of values) {
      if (value === null || !Number.isFinite(value) || (value >= 0 && value <= 12)) continue;
      const x = timeToX(point.time, metrics, viewport);
      const y = valueToY(value > 12 ? 12 : 0, metrics);
      ctx.beginPath();
      if (value > 12) {
        ctx.moveTo(x - 4, y + 7);
        ctx.lineTo(x, y);
        ctx.lineTo(x + 4, y + 7);
      } else {
        ctx.moveTo(x - 4, y - 7);
        ctx.lineTo(x, y);
        ctx.lineTo(x + 4, y - 7);
      }
      ctx.stroke();
    }
  }

  ctx.restore();
}

function drawOverlay(
  canvas: HTMLCanvasElement,
  point: ActuatorOperationPoint,
  metrics: ChartMetrics,
  viewport: Viewport,
) {
  const ctx = canvas.getContext("2d");
  if (!ctx) return;

  const palette = readThemePalette(canvas);
  const x = timeToX(point.time, metrics, viewport);

  ctx.save();
  ctx.setTransform(metrics.dpr, 0, 0, metrics.dpr, 0, 0);
  ctx.strokeStyle = palette.mutedForeground;
  ctx.globalAlpha = 0.72;
  ctx.setLineDash([3, 3]);
  ctx.lineWidth = 1;
  ctx.beginPath();
  ctx.moveTo(x, metrics.stateTop);
  ctx.lineTo(x, metrics.height - metrics.bottom);
  ctx.stroke();
  ctx.restore();

  ctx.save();
  ctx.setTransform(metrics.dpr, 0, 0, metrics.dpr, 0, 0);
  ctx.lineWidth = 2;

  if (validElectricalValue(point.voltageVisual)) {
    drawPointMarker(ctx, x, valueToY(point.voltageVisual!, metrics), palette.background, palette.voltage);
  }
  if (validElectricalValue(point.currentVisual)) {
    drawPointMarker(ctx, x, valueToY(point.currentVisual!, metrics), palette.background, palette.current);
  }

  ctx.restore();
}

function drawPointMarker(
  ctx: CanvasRenderingContext2D,
  x: number,
  y: number,
  fill: string,
  stroke: string,
) {
  ctx.beginPath();
  ctx.arc(x, y, 4, 0, Math.PI * 2);
  ctx.fillStyle = fill;
  ctx.fill();
  ctx.strokeStyle = stroke;
  ctx.stroke();
}

function drawHatchedRect(
  ctx: CanvasRenderingContext2D,
  x: number,
  y: number,
  width: number,
  height: number,
  fill: string,
  hatch: string,
  hatchAlpha: number,
) {
  ctx.save();
  ctx.fillStyle = fill;
  ctx.fillRect(x, y, width, height);
  ctx.beginPath();
  ctx.rect(x, y, width, height);
  ctx.clip();
  ctx.strokeStyle = hatch;
  ctx.globalAlpha = hatchAlpha;
  ctx.lineWidth = 1;

  const step = 8;
  for (let offset = -height; offset < width + height; offset += step) {
    ctx.beginPath();
    ctx.moveTo(x + offset, y + height);
    ctx.lineTo(x + offset + height, y);
    ctx.stroke();
  }
  ctx.restore();
}

function roundedRectPath(
  ctx: CanvasRenderingContext2D,
  x: number,
  y: number,
  width: number,
  height: number,
  radius: number,
) {
  const r = Math.min(radius, width / 2, height / 2);
  ctx.beginPath();
  ctx.moveTo(x + r, y);
  ctx.lineTo(x + width - r, y);
  ctx.quadraticCurveTo(x + width, y, x + width, y + r);
  ctx.lineTo(x + width, y + height - r);
  ctx.quadraticCurveTo(x + width, y + height, x + width - r, y + height);
  ctx.lineTo(x + r, y + height);
  ctx.quadraticCurveTo(x, y + height, x, y + height - r);
  ctx.lineTo(x, y + r);
  ctx.quadraticCurveTo(x, y, x + r, y);
  ctx.closePath();
}

function readThemePalette(element: Element): ThemePalette {
  return {
    foreground: readCssColor(element, "--foreground", "#111827"),
    mutedForeground: readCssColor(element, "--muted-foreground", "#64748b"),
    border: readCssColor(element, "--border", "#d7dde3"),
    muted: readCssColor(element, "--muted", "#e5e7eb"),
    background: readCssColor(element, "--background", "#ffffff"),
    primary: readCssColor(element, "--primary", "#334155"),
    primaryForeground: readCssColor(element, "--primary-foreground", "#ffffff"),
    voltage: "#0284c7",
    current: "#d97706",
    destructive: readCssColor(element, "--destructive", "#dc2626"),
  };
}

function readCssColor(element: Element, name: string, fallback: string) {
  if (typeof window === "undefined") return fallback;
  const value = getComputedStyle(element).getPropertyValue(name).trim();
  if (!value) return fallback;
  if (/^(#|rgb|hsl|oklch|oklab|color\(|lab\(|lch\()/i.test(value)) return value;
  if (/^[\d.]+(?:deg)?\s/.test(value)) return `hsl(${value})`;
  return value;
}

function timeToX(time: number, metrics: ChartMetrics, viewport: Viewport) {
  const span = Math.max(1, viewport.end - viewport.start);
  return metrics.left + ((time - viewport.start) / span) * metrics.plotWidth;
}

function xToTime(x: number, metrics: ChartMetrics, viewport: Viewport) {
  const ratio = clamp((x - metrics.left) / Math.max(1, metrics.plotWidth), 0, 1);
  return viewport.start + ratio * (viewport.end - viewport.start);
}

function valueToY(value: number, metrics: ChartMetrics) {
  const clamped = clamp(value, 0, 12);
  return metrics.top + (1 - clamped / 12) * metrics.plotHeight;
}

function findPointRange(
  points: Pick<ActuatorOperationPoint, "time">[],
  start: number,
  end: number,
) {
  return {
    start: lowerBoundTime(points, start),
    end: upperBoundTime(points, end),
  };
}

function lowerBoundTime(points: Pick<ActuatorOperationPoint, "time">[], target: number) {
  let low = 0;
  let high = points.length;
  while (low < high) {
    const middle = (low + high) >>> 1;
    if (points[middle].time < target) low = middle + 1;
    else high = middle;
  }
  return low;
}

function upperBoundTime(points: Pick<ActuatorOperationPoint, "time">[], target: number) {
  let low = 0;
  let high = points.length;
  while (low < high) {
    const middle = (low + high) >>> 1;
    if (points[middle].time <= target) low = middle + 1;
    else high = middle;
  }
  return low;
}

export function binarySearchNearestPoint(
  points: Pick<ActuatorOperationPoint, "time">[],
  target: number,
  startIndex = 0,
  endIndex = points.length,
): number | null {
  if (!points.length || endIndex <= startIndex) return null;

  let low = startIndex;
  let high = endIndex;
  while (low < high) {
    const middle = (low + high) >>> 1;
    if (points[middle].time < target) low = middle + 1;
    else high = middle;
  }

  const right = clamp(low, startIndex, endIndex - 1);
  const left = Math.max(startIndex, right - 1);
  return Math.abs(points[left].time - target) <= Math.abs(points[right].time - target)
    ? left
    : right;
}

function clipStateIntervals(intervals: StateInterval[], start: number, end: number) {
  if (!intervals.length || end <= start) return [];

  let low = 0;
  let high = intervals.length;
  while (low < high) {
    const middle = (low + high) >>> 1;
    if (intervals[middle].end <= start) low = middle + 1;
    else high = middle;
  }

  const output: StateInterval[] = [];
  for (let index = low; index < intervals.length; index += 1) {
    const interval = intervals[index];
    if (interval.start >= end) break;
    output.push({
      start: Math.max(start, interval.start),
      end: Math.min(end, interval.end),
      state: interval.state,
    });
  }
  return output;
}

function mergeAdjacentIntervals(intervals: StateInterval[]): StateInterval[] {
  const merged: StateInterval[] = [];
  for (const interval of intervals) {
    const previous = merged.at(-1);
    if (
      previous &&
      previous.state === interval.state &&
      previous.end === interval.start
    ) {
      previous.end = interval.end;
    } else {
      merged.push({ ...interval });
    }
  }
  return merged;
}

function mergeRibbonBuckets(buckets: StateRibbonSegment[]): StateRibbonSegment[] {
  const merged: StateRibbonSegment[] = [];
  for (const bucket of buckets) {
    const previous = merged.at(-1);
    if (
      previous &&
      previous.kind === bucket.kind &&
      bucket.kind !== "MIXED" &&
      previous.end === bucket.start
    ) {
      previous.end = bucket.end;
      previous.onDuration += bucket.onDuration;
      previous.offDuration += bucket.offDuration;
      previous.unknownDuration += bucket.unknownDuration;
      previous.transitionCount += bucket.transitionCount;
    } else {
      merged.push({ ...bucket });
    }
  }
  return merged;
}

function getKnownTransitionTimes(intervals: StateInterval[]) {
  const transitions: number[] = [];
  for (let index = 1; index < intervals.length; index += 1) {
    const previous = intervals[index - 1];
    const current = intervals[index];
    if (
      previous.state !== null &&
      current.state !== null &&
      previous.state !== current.state
    ) {
      transitions.push(current.start);
    }
  }
  return transitions;
}

function findStateInterval(intervals: StateInterval[], time: number) {
  let low = 0;
  let high = intervals.length - 1;

  while (low <= high) {
    const middle = (low + high) >>> 1;
    const interval = intervals[middle];
    if (time < interval.start) high = middle - 1;
    else if (time > interval.end) low = middle + 1;
    else if (time === interval.end && middle < intervals.length - 1) low = middle + 1;
    else return interval;
  }
  return null;
}

function findRibbonSegment(segments: StateRibbonSegment[], time: number) {
  let low = 0;
  let high = segments.length - 1;

  while (low <= high) {
    const middle = (low + high) >>> 1;
    const segment = segments[middle];
    if (time < segment.start) high = middle - 1;
    else if (time > segment.end) low = middle + 1;
    else if (time === segment.end && middle < segments.length - 1) low = middle + 1;
    else return segment;
  }
  return null;
}

function summarizeStateIntervals(intervals: StateInterval[]) {
  return intervals.reduce(
    (summary, interval) => {
      const duration = Math.max(0, interval.end - interval.start);
      if (interval.state === true) summary.onDuration += duration;
      else if (interval.state === false) summary.offDuration += duration;
      else summary.unknownDuration += duration;
      return summary;
    },
    { onDuration: 0, offDuration: 0, unknownDuration: 0 },
  );
}

function chooseNiceTimeStep(target: number) {
  const steps = [
    5 * MINUTE_MS,
    10 * MINUTE_MS,
    15 * MINUTE_MS,
    30 * MINUTE_MS,
    HOUR_MS,
    2 * HOUR_MS,
    3 * HOUR_MS,
    6 * HOUR_MS,
    12 * HOUR_MS,
    DAY_MS,
    2 * DAY_MS,
    3 * DAY_MS,
    5 * DAY_MS,
    7 * DAY_MS,
    10 * DAY_MS,
    14 * DAY_MS,
    21 * DAY_MS,
    30 * DAY_MS,
    60 * DAY_MS,
    90 * DAY_MS,
  ];
  return steps.find((step) => step >= target) ?? Math.ceil(target / DAY_MS) * DAY_MS;
}

function clampViewport(viewport: Viewport, fullDomain: Viewport): Viewport {
  const fullSpan = Math.max(1, fullDomain.end - fullDomain.start);
  let span = clamp(viewport.end - viewport.start, 1, fullSpan);
  if (!Number.isFinite(span) || span <= 0) span = fullSpan;

  let start = viewport.start;
  let end = start + span;

  if (start < fullDomain.start) {
    start = fullDomain.start;
    end = start + span;
  }
  if (end > fullDomain.end) {
    end = fullDomain.end;
    start = end - span;
  }

  return { start, end };
}

function sameViewport(a: Viewport, b: Viewport) {
  const span = Math.max(1, b.end - b.start);
  const epsilon = span * 0.0001;
  return Math.abs(a.start - b.start) <= epsilon && Math.abs(a.end - b.end) <= epsilon;
}

function isFiniteViewport(viewport: Viewport) {
  return Number.isFinite(viewport.start) && Number.isFinite(viewport.end) && viewport.end > viewport.start;
}

function validElectricalValue(value: number | null) {
  return value !== null && Number.isFinite(value);
}

function parseTime(value?: string) {
  if (!value) return Number.NaN;
  return Date.parse(value);
}

function clamp(value: number, min: number, max: number) {
  return Math.min(max, Math.max(min, value));
}

function normalizeWheelDelta(event: WheelEvent) {
  // deltaMode: 0 = px, 1 = lines, 2 = pages. Normalize to a pixel-like
  // magnitude so mouse wheels and trackpads zoom at comparable speeds.
  if (event.deltaMode === WheelEvent.DOM_DELTA_LINE) return event.deltaY * 16;
  if (event.deltaMode === WheelEvent.DOM_DELTA_PAGE) return event.deltaY * 320;
  return event.deltaY;
}

function formatTimeTick(time: number, span: number) {
  const date = new Date(time);
  if (span <= DAY_MS) {
    return date.toLocaleTimeString("vi-VN", {
      hour: "2-digit",
      minute: "2-digit",
    });
  }
  if (span <= 45 * DAY_MS) {
    return date.toLocaleDateString("vi-VN", {
      day: "2-digit",
      month: "2-digit",
    });
  }
  return date.toLocaleDateString("vi-VN", {
    day: "2-digit",
    month: "2-digit",
    year: "2-digit",
  });
}

function formatViewport(viewport: Viewport) {
  const span = viewport.end - viewport.start;
  const options: Intl.DateTimeFormatOptions =
    span <= DAY_MS
      ? { day: "2-digit", month: "2-digit", hour: "2-digit", minute: "2-digit" }
      : { day: "2-digit", month: "2-digit", year: "numeric" };
  return `${new Date(viewport.start).toLocaleString("vi-VN", options)} → ${new Date(viewport.end).toLocaleString("vi-VN", options)}`;
}

function formatDuration(milliseconds: number) {
  if (!Number.isFinite(milliseconds) || milliseconds <= 0) return "0 phút";
  const totalMinutes = Math.floor(milliseconds / 60_000);
  const days = Math.floor(totalMinutes / (24 * 60));
  const hours = Math.floor((totalMinutes % (24 * 60)) / 60);
  const minutes = totalMinutes % 60;
  if (days > 0) return `${days} ngày ${hours} giờ`;
  if (hours > 0) return `${hours} giờ ${minutes} phút`;
  return `${Math.max(1, minutes)} phút`;
}

function ribbonLabel(kind: StateRibbonKind) {
  switch (kind) {
    case "ON":
      return "BẬT";
    case "OFF":
      return "TẮT";
    case "MIXED":
      return "BẬT/TẮT";
    default:
      return "KHÔNG XÁC ĐỊNH";
  }
}

function CurrentStateBadge({ state }: { state: boolean | null }) {
  if (state === true) {
    return (
      <span className="inline-flex items-center gap-2 rounded-full border border-primary/30 bg-primary/10 px-3 py-1.5 text-xs font-semibold text-foreground">
        <span className="h-2 w-2 rounded-full bg-primary" aria-hidden="true" />
        Hiện tại: BẬT
      </span>
    );
  }

  if (state === false) {
    return (
      <span className="inline-flex items-center gap-2 rounded-full border px-3 py-1.5 text-xs font-semibold text-muted-foreground">
        <span
          className="h-2 w-2 rounded-full border border-muted-foreground bg-background"
          aria-hidden="true"
        />
        Hiện tại: TẮT
      </span>
    );
  }

  return (
    <span className="inline-flex items-center gap-2 rounded-full border border-dashed bg-muted/30 px-3 py-1.5 text-xs font-semibold text-muted-foreground">
      <span
        className="grid h-4 w-4 place-items-center rounded-full border border-muted-foreground text-[10px] leading-none"
        aria-hidden="true"
      >
        ?
      </span>
      Hiện tại: KHÔNG XÁC ĐỊNH
    </span>
  );
}

function StateLegend({
  kind,
  label,
}: {
  kind: StateRibbonKind;
  label: string;
}) {
  const className =
    kind === "ON"
      ? "border-primary bg-primary/80"
      : kind === "OFF"
        ? "border-muted-foreground/50 bg-background"
        : kind === "UNKNOWN"
          ? "border-dashed border-muted-foreground bg-muted/50"
          : "border-primary/50 bg-muted";

  return (
    <span className="flex items-center gap-1.5">
      <span
        className={`h-2.5 w-5 rounded-sm border ${className}`}
        aria-hidden="true"
      />
      {label}
    </span>
  );
}

function Legend({ className, label }: { className: string; label: string }) {
  return (
    <span className="flex items-center gap-1.5">
      <span className={`w-5 border-t-2 ${className}`} aria-hidden="true" />
      {label}
    </span>
  );
}

function Tooltip({
  point,
  interval,
  ribbonSegment,
}: {
  point: ActuatorOperationPoint;
  interval: StateInterval | null;
  ribbonSegment: StateRibbonSegment | null;
}) {
  const overflow = [point.voltageRaw, point.currentRaw].some(
    (value) => value !== null && (value > 12 || value < 0),
  );
  const state = interval?.state ?? point.reportedState;

  return (
    <div className="pointer-events-none absolute right-3 top-3 z-10 min-w-56 rounded-lg border bg-popover/95 p-3 text-xs shadow-md backdrop-blur-sm">
      <p className="font-medium">
        {new Date(point.time).toLocaleString("vi-VN")}
      </p>

      <div className="mt-2 grid grid-cols-[auto_1fr] gap-x-3 gap-y-1">
        <span className="text-muted-foreground">Trạng thái</span>
        <span className="font-medium">
          {state === null ? "Không xác định" : actuatorStateLabel(state)}
        </span>

        <span className="text-muted-foreground">Điện áp</span>
        <span>{point.voltageRaw === null ? "—" : `${point.voltageRaw} V`}</span>

        <span className="text-muted-foreground">Dòng điện</span>
        <span>{point.currentRaw === null ? "—" : `${point.currentRaw} A`}</span>
      </div>

      {ribbonSegment?.kind === "MIXED" ? (
        <div className="mt-2 border-t pt-2 text-muted-foreground">
          <p className="font-medium text-foreground">
            Trong vùng hiển thị có chuyển trạng thái
          </p>
          <p>Bật: {formatDuration(ribbonSegment.onDuration)}</p>
          <p>Tắt: {formatDuration(ribbonSegment.offDuration)}</p>
          {ribbonSegment.unknownDuration > 0 ? (
            <p>Không xác định: {formatDuration(ribbonSegment.unknownDuration)}</p>
          ) : null}
          <p>Chuyển trạng thái: {ribbonSegment.transitionCount} lần</p>
        </div>
      ) : ribbonSegment?.kind === "UNKNOWN" ? (
        <p className="mt-2 border-t pt-2 text-muted-foreground">
          Khoảng này chưa có trạng thái phản hồi đủ rõ để kết luận Bật hoặc Tắt.
        </p>
      ) : null}

      {overflow ? (
        <p className="mt-2 text-destructive">
          Có giá trị vượt vùng hiển thị 0–12; tooltip vẫn giữ giá trị thực.
        </p>
      ) : null}
    </div>
  );
}
