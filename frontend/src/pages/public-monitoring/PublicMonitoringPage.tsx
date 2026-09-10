import { useState } from "react"
import { useQuery } from "@tanstack/react-query"
import {
  Activity,
  AlertTriangle,
  Eye,
  Power,
  RadioTower,
  RotateCcw,
} from "lucide-react"

import {
  getCommandStatus,
  getDesiredStateLabel,
  getReportedStateLabel,
  isAwaitingActuatorConfirmation,
} from "@/entities/actuator/lib/actuator-monitoring"

import { publicMonitoringApi } from "@/entities/project/api/public-monitoring-api"

import { getSensorConnectionStatus } from "@/entities/sensor/lib/get-sensor-connection-status"
import { formatSensorValue } from "@/entities/sensor/lib/format-sensor-value"
import { getSensorValueStatus } from "@/entities/sensor/lib/get-sensor-value-status"

import {
  monitoringExpectedInterval,
  monitoringRangeLabel,
} from "@/entities/telemetry/lib/monitoring-range"

import type {
  CoreId,
  MonitoringActuator,
  MonitoringDevice,
  MonitoringRange,
  MonitoringSensor,
} from "@/entities/telemetry/model/project-monitoring"

import type { MonitoringDialogTab } from "@/features/view-device-monitoring-history/model/monitoring-dialog.types"

import { MonitoringRangeSelector } from "@/features/view-device-monitoring-history/ui/MonitoringRangeSelector"

import { TimeSeriesChart } from "@/shared/charts/time-series"
import { formatDateTime } from "@/shared/lib/date"

import { Badge } from "@/shared/ui/badge"
import { Button } from "@/shared/ui/button"

import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/shared/ui/card"

import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/shared/ui/dialog"

import { EmptyState } from "@/shared/ui/empty-state"

import {
  Select,
  SelectContent,
  SelectGroup,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/shared/ui/select"

import { Skeleton } from "@/shared/ui/skeleton"
import { StatusBadge } from "@/shared/ui/status-badge"

import {
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
} from "@/shared/ui/tabs"

import { ProjectMonitoringView } from "@/widgets/project-monitoring/ProjectMonitoringView"

/* ==========================================================================
 * Helpers
 * ========================================================================== */

function displayValue(
  value: number | null | undefined,
  unit: string,
) {
  if (value === null || value === undefined) {
    return "—"
  }

  return `${new Intl.NumberFormat("vi-VN", {
    maximumFractionDigits: 2,
  }).format(value)} ${unit}`
}

/* ==========================================================================
 * Connection badge
 * ========================================================================== */

function ConnectionBadge({
  status,
}: {
  status: MonitoringDevice["connection_status"]
}) {
  const display =
    getSensorConnectionStatus(status)

  const variant =
    display.tone === "success"
      ? "success"
      : display.tone === "offline"
        ? "destructive"
        : display.tone === "warning"
          ? "warning"
          : "secondary"

  return (
    <Badge variant={variant}>
      {display.label}
    </Badge>
  )
}

/* ==========================================================================
 * Actuator connection badge
 * ========================================================================== */

function ActuatorConnectionBadge({
  status,
}: {
  status: MonitoringActuator["connection_status"]
}) {
  const display =
    getSensorConnectionStatus(status)

  const variant =
    display.tone === "success"
      ? "success"
      : display.tone === "offline"
        ? "destructive"
        : display.tone === "warning"
          ? "warning"
          : "secondary"

  return (
    <Badge variant={variant}>
      {display.label}
    </Badge>
  )
}

/* ==========================================================================
 * Actuator state badge
 * ========================================================================== */

function ActuatorStateBadge({
  state,
}: {
  state: boolean | null
}) {
  return (
    <Badge
      variant={
        state === true
          ? "success"
          : state === false
            ? "secondary"
            : "outline"
      }
    >
      {getReportedStateLabel(state)}
    </Badge>
  )
}

/* ==========================================================================
 * Actuator command badge
 * ========================================================================== */

function ActuatorCommandBadge({
  actuator,
}: {
  actuator: MonitoringActuator
}) {
  const command =
    getCommandStatus(
      actuator.latest_command?.status ?? null,
    )

  const variant =
    command.tone === "danger"
      ? "destructive"
      : command.tone === "success"
        ? "success"
        : command.tone === "warning"
          ? "warning"
          : "secondary"

  return (
    <Badge variant={variant}>
      {command.label}
    </Badge>
  )
}

/* ==========================================================================
 * Sensor Resource Button
 * ========================================================================== */

function SensorResourceButton({
  sensor,
  selected,
  onSelect,
}: {
  sensor: MonitoringSensor
  selected: boolean
  onSelect: () => void
}) {
  const valueStatus =
    getSensorValueStatus(
      sensor.latest?.value ?? null,
      sensor.lower_threshold,
      sensor.upper_threshold,
    )

  return (
    <button
      type="button"
      aria-pressed={selected}
      data-selected={selected}
      className="
        flex
        w-full
        flex-col
        gap-1
        rounded-lg
        border
        p-3
        text-left
        transition-colors
        hover:bg-accent
        focus-visible:ring-2
        focus-visible:ring-ring
        data-[selected=true]:border-primary
        data-[selected=true]:bg-accent
      "
      onClick={onSelect}
    >
      <span className="line-clamp-2 text-sm font-medium">
        {sensor.name}
      </span>

      <span className="text-sm font-semibold tabular-nums">
        {formatSensorValue(
          sensor.latest?.value ?? null,
          sensor.unit,
        )}
      </span>

      <span className="text-xs text-muted-foreground">
        {valueStatus.label}

        {" · "}

        {sensor.latest
          ? formatDateTime(
              sensor.latest.recorded_at,
            )
          : "Chưa có dữ liệu"}
      </span>
    </button>
  )
}

/* ==========================================================================
 * Actuator Resource Button
 * ========================================================================== */

function ActuatorResourceButton({
  actuator,
  selected,
  onSelect,
}: {
  actuator: MonitoringActuator
  selected: boolean
  onSelect: () => void
}) {
  const command =
    getCommandStatus(
      actuator.latest_command?.status ?? null,
    )

  const awaiting =
    isAwaitingActuatorConfirmation(
      actuator.desired_state,
      actuator.reported_state,
      actuator.latest_command?.status ?? null,
    )

  return (
    <button
      type="button"
      aria-pressed={selected}
      data-selected={selected}
      className="
        flex
        w-full
        flex-col
        gap-2
        rounded-lg
        border
        p-3
        text-left
        transition-colors
        hover:bg-accent
        focus-visible:ring-2
        focus-visible:ring-ring
        data-[selected=true]:border-primary
        data-[selected=true]:bg-accent
      "
      onClick={onSelect}
    >
      <span className="line-clamp-2 text-sm font-medium">
        {actuator.name}
      </span>

      <div className="flex flex-wrap gap-2">
        <ActuatorStateBadge
          state={actuator.reported_state}
        />

        <Badge variant="outline">
          {command.label}
        </Badge>
      </div>

      {awaiting ? (
        <span className="text-xs text-muted-foreground">
          Đang chờ thiết bị xác nhận.
        </span>
      ) : null}

      <span className="text-xs text-muted-foreground">
        {actuator.last_reported_at
          ? formatDateTime(
              actuator.last_reported_at,
            )
          : "Chưa có dữ liệu"}
      </span>
    </button>
  )
}

/* ==========================================================================
 * Resource Select
 * ========================================================================== */

function ResourceSelect({
  resources,
  value,
  onValueChange,
}: {
  resources: Array<{
    id: CoreId
    name: string
  }>
  value: CoreId | null
  onValueChange: (id: CoreId) => void
}) {
  if (!resources.length) {
    return null
  }

  return (
    <div className="lg:hidden">
      <Select
        value={
          value === null
            ? undefined
            : String(value)
        }
        onValueChange={(next: string) => {
          const resource = resources.find((item) => String(item.id) === next)
          if (resource) onValueChange(resource.id)
        }}
      >
        <SelectTrigger
          aria-label="Chọn tài nguyên"
        >
          <SelectValue
            placeholder="Chọn tài nguyên"
          />
        </SelectTrigger>

        <SelectContent>
          <SelectGroup>
            {resources.map(
              (resource) => (
                <SelectItem
                  key={resource.id}
                  value={String(
                    resource.id,
                  )}
                >
                  {resource.name}
                </SelectItem>
              ),
            )}
          </SelectGroup>
        </SelectContent>
      </Select>
    </div>
  )
}

/* ==========================================================================
 * Actuator state visual
 *
 * Đây là visualization trạng thái hiện tại.
 * Không giả lập lịch sử ON/OFF.
 * ========================================================================== */

function ActuatorStateVisual({
  actuator,
}: {
  actuator: MonitoringActuator
}) {
  const state =
    actuator.reported_state

  return (
    <Card>
      <CardHeader>
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <CardTitle className="text-base">
              Trạng thái thực tế
            </CardTitle>

            <CardDescription>
              Trạng thái cuối thiết bị
              đã báo về hệ thống.
            </CardDescription>
          </div>

          <ActuatorStateBadge
            state={state}
          />
        </div>
      </CardHeader>

      <CardContent className="space-y-4">
        <div className="relative h-20 overflow-hidden rounded-lg border bg-muted/20">
          <div className="absolute inset-y-0 left-1/2 w-px bg-border" />

          <div className="absolute inset-y-0 left-0 flex w-1/2 items-center justify-center">
            <span
              className={
                state === false
                  ? "text-xl font-bold"
                  : "text-sm text-muted-foreground"
              }
            >
              TẮT
            </span>
          </div>

          <div className="absolute inset-y-0 right-0 flex w-1/2 items-center justify-center">
            <span
              className={
                state === true
                  ? "text-xl font-bold"
                  : "text-sm text-muted-foreground"
              }
            >
              BẬT
            </span>
          </div>

          {state === false ? (
            <div className="pointer-events-none absolute inset-y-0 left-0 w-1/2 bg-muted-foreground/10" />
          ) : null}

          {state === true ? (
            <div className="pointer-events-none absolute inset-y-0 right-0 w-1/2 bg-primary/10" />
          ) : null}
        </div>

        <p className="text-xs text-muted-foreground">
          Cập nhật cuối:{" "}
          {actuator.last_reported_at
            ? formatDateTime(
                actuator.last_reported_at,
              )
            : "Chưa có dữ liệu"}
        </p>
      </CardContent>
    </Card>
  )
}

/* ==========================================================================
 * Actuator Dashboard
 * ========================================================================== */

function ActuatorDashboard({
  actuator,
}: {
  actuator: MonitoringActuator
}) {
  const command =
    getCommandStatus(
      actuator.latest_command?.status ?? null,
    )

  const awaiting =
    isAwaitingActuatorConfirmation(
      actuator.desired_state,
      actuator.reported_state,
      actuator.latest_command?.status ?? null,
    )

  return (
    <div className="space-y-4">
      {/* ================================================================ */}
      {/* Summary cards                                                    */}
      {/* ================================================================ */}

      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <Card>
          <CardHeader className="pb-3">
            <CardDescription>
              Kết nối
            </CardDescription>

            <div className="pt-1">
              <ActuatorConnectionBadge
                status={
                  actuator.connection_status
                }
              />
            </div>
          </CardHeader>
        </Card>

        <Card>
          <CardHeader className="pb-3">
            <CardDescription>
              Trạng thái yêu cầu
            </CardDescription>

            <CardTitle className="text-xl">
              {getDesiredStateLabel(
                actuator.desired_state,
              )}
            </CardTitle>
          </CardHeader>
        </Card>

        <Card>
          <CardHeader className="pb-3">
            <CardDescription>
              Trạng thái thực tế
            </CardDescription>

            <CardTitle className="text-xl">
              {getReportedStateLabel(
                actuator.reported_state,
              )}
            </CardTitle>
          </CardHeader>
        </Card>

        <Card>
          <CardHeader className="pb-3">
            <CardDescription>
              Lệnh gần nhất
            </CardDescription>

            <div className="pt-1">
              <ActuatorCommandBadge
                actuator={actuator}
              />
            </div>
          </CardHeader>
        </Card>
      </div>

      {/* ================================================================ */}
      {/* Synchronization                                                  */}
      {/* ================================================================ */}

      <Card>
        <CardHeader>
          <CardTitle className="text-base">
            Đồng bộ trạng thái
          </CardTitle>

          <CardDescription>
            So sánh trạng thái yêu cầu
            và trạng thái thực tế thiết bị
            đã báo về.
          </CardDescription>
        </CardHeader>

        <CardContent className="space-y-4">
          <div className="grid gap-3 sm:grid-cols-2">
            <div className="rounded-lg border p-4">
              <p className="text-xs text-muted-foreground">
                Trạng thái yêu cầu
              </p>

              <p className="mt-2 text-2xl font-semibold">
                {getDesiredStateLabel(
                  actuator.desired_state,
                )}
              </p>
            </div>

            <div className="rounded-lg border p-4">
              <p className="text-xs text-muted-foreground">
                Trạng thái thực tế
              </p>

              <p className="mt-2 text-2xl font-semibold">
                {getReportedStateLabel(
                  actuator.reported_state,
                )}
              </p>
            </div>
          </div>

          {awaiting ? (
            <div className="rounded-lg border border-dashed p-3">
              <p className="text-sm font-medium">
                Đang chờ thiết bị xác nhận
              </p>

              <p className="mt-1 text-xs text-muted-foreground">
                Trạng thái mong muốn
                chưa khớp với trạng thái
                thực tế thiết bị báo về.
              </p>
            </div>
          ) : null}
        </CardContent>
      </Card>

      {/* ================================================================ */}
      {/* Current state                                                     */}
      {/* ================================================================ */}

      <ActuatorStateVisual
        actuator={actuator}
      />

      {/* ================================================================ */}
      {/* Runtime information                                               */}
      {/* ================================================================ */}

      <Card>
        <CardHeader>
          <CardTitle className="text-base">
            Thông tin vận hành
          </CardTitle>
        </CardHeader>

        <CardContent className="space-y-3">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <span className="text-sm text-muted-foreground">
              Kết nối
            </span>

            <ActuatorConnectionBadge
              status={
                actuator.connection_status
              }
            />
          </div>

          <div className="flex flex-wrap items-center justify-between gap-3">
            <span className="text-sm text-muted-foreground">
              Yêu cầu
            </span>

            <span className="text-sm font-semibold">
              {getDesiredStateLabel(
                actuator.desired_state,
              )}
            </span>
          </div>

          <div className="flex flex-wrap items-center justify-between gap-3">
            <span className="text-sm text-muted-foreground">
              Thực tế
            </span>

            <ActuatorStateBadge
              state={
                actuator.reported_state
              }
            />
          </div>

          <div className="flex flex-wrap items-center justify-between gap-3">
            <span className="text-sm text-muted-foreground">
              Lệnh gần nhất
            </span>

            <ActuatorCommandBadge
              actuator={actuator}
            />
          </div>

          <div className="flex flex-wrap items-center justify-between gap-3">
            <span className="text-sm text-muted-foreground">
              Cập nhật cuối
            </span>

            <span className="text-sm font-medium">
              {actuator.last_reported_at
                ? formatDateTime(
                    actuator.last_reported_at,
                  )
                : "Chưa có dữ liệu"}
            </span>
          </div>

          {command.tone === "danger" ? (
            <div className="rounded-lg border border-dashed p-3">
              <p className="text-xs text-muted-foreground">
                Lệnh gần nhất đang ở
                trạng thái cần chú ý.
              </p>
            </div>
          ) : null}
        </CardContent>
      </Card>

      {/* ================================================================ */}
      {/* History placeholder                                               */}
      {/* ================================================================ */}

      <div className="flex min-h-48 flex-col items-center justify-center gap-3 rounded-lg border border-dashed bg-muted/10 p-6 text-center">
        <Activity
          className="size-7 text-muted-foreground"
          aria-hidden="true"
        />

        <div className="space-y-1">
          <p className="text-sm font-semibold">
            Biểu đồ lịch sử bật/tắt
          </p>

          <p className="mx-auto max-w-lg text-xs text-muted-foreground">
            Public Monitoring chưa expose
            actuator-history.
          </p>

          <p className="mx-auto max-w-lg text-xs text-muted-foreground">
            Dashboard hiện chỉ sử dụng
            trạng thái thực tế từ backend,
            không tạo lịch sử giả.
          </p>
        </div>
      </div>

      <div className="rounded-lg border border-dashed bg-muted/20 p-3 text-center text-xs text-muted-foreground">
        Theo dõi từ xa · Chỉ đọc ·
        Không thể điều khiển cơ cấu chấp hành
      </div>
    </div>
  )
}

/* ==========================================================================
 * Public Device Monitoring Dialog
 * ========================================================================== */

function PublicDeviceMonitoringDialog({
  open,
  device,
  tab,
  resourceId,
  range,
  onOpenChange,
  onTabChange,
  onResourceChange,
  onRangeChange,
}: {
  open: boolean
  device: MonitoringDevice | null
  tab: MonitoringDialogTab
  resourceId: CoreId | null
  range: MonitoringRange
  onOpenChange: (open: boolean) => void
  onTabChange: (
    tab: MonitoringDialogTab,
  ) => void
  onResourceChange: (
    resourceId: CoreId,
  ) => void
  onRangeChange: (
    range: MonitoringRange,
  ) => void
}) {
  const resources =
    tab === "sensors"
      ? device?.sensors ?? []
      : device?.actuators ?? []

  const selectedResourceId =
    resources.some(
      (resource) =>
        resource.id === resourceId,
    )
      ? resourceId
      : resources[0]?.id ?? null

  const selectedSensor =
    tab === "sensors"
      ? device?.sensors.find(
          (sensor) =>
            sensor.id ===
            selectedResourceId,
        ) ?? null
      : null

  const selectedActuator =
    tab === "actuators"
      ? device?.actuators.find(
          (actuator) =>
            actuator.id ===
            selectedResourceId,
        ) ?? null
      : null

  const sensorHistory =
    useQuery({
      queryKey: [
        "public-monitoring",
        "device-dialog",
        "sensor-series",
        device?.id,
        range,
      ],

      queryFn: () =>
        publicMonitoringApi.telemetrySeries(
          range,
        ),

      enabled:
        open &&
        device !== null &&
        tab === "sensors",

      staleTime: 30_000,
    })

  const selectedSensorSeries =
    sensorHistory.data?.series.find(
      (item) =>
        item.sensor_id ===
        selectedSensor?.id,
    )

  return (
    <Dialog
      open={open}
      onOpenChange={onOpenChange}
    >
      <DialogContent
        className="
          flex
          max-h-[calc(100dvh-1rem)]
          max-w-[min(1380px,calc(100vw-1rem))]
          flex-col
          gap-4
          overflow-hidden
          p-4
          sm:max-h-[calc(100dvh-2rem)]
          sm:p-6
        "
      >
        <DialogHeader className="pr-8">
          <div className="flex flex-wrap items-center gap-2">
            <DialogTitle>
              Theo dõi:{" "}
              {device?.name ??
                "Thiết bị"}
            </DialogTitle>

            {device ? (
              <ConnectionBadge
                status={
                  device.connection_status
                }
              />
            ) : null}

            <Badge variant="outline">
              Chỉ đọc
            </Badge>
          </div>

          <DialogDescription>
            {device?.location ??
              "Chưa cập nhật vị trí"}

            {" · "}

            Cập nhật cuối:{" "}

            {device?.last_seen_at
              ? formatDateTime(
                  device.last_seen_at,
                )
              : "Chưa có dữ liệu"}
          </DialogDescription>
        </DialogHeader>

        <MonitoringRangeSelector
          range={range}
          onRangeChange={
            onRangeChange
          }
        />

        <Tabs
          value={tab}
          onValueChange={(
            value: string,
          ) => {
            onTabChange(
              value as MonitoringDialogTab,
            )
          }}
          className="flex min-h-0 flex-1 flex-col"
        >
          <TabsList className="w-full sm:w-fit">
            <TabsTrigger
              value="sensors"
              className="flex-1 sm:flex-none"
            >
              Cảm biến (
              {device?.sensors.length ?? 0}
              )
            </TabsTrigger>

            <TabsTrigger
              value="actuators"
              className="flex-1 sm:flex-none"
            >
              Cơ cấu chấp hành (
              {device?.actuators.length ?? 0}
              )
            </TabsTrigger>
          </TabsList>

          <div className="mt-3 min-h-0 flex-1 overflow-y-auto">
            {/* ============================================================ */}
            {/* Sensor tab                                                   */}
            {/* ============================================================ */}

            <TabsContent
              value="sensors"
              className="mt-0"
            >
              {!device?.sensors.length ? (
                <div className="flex min-h-64 items-center justify-center rounded-lg border border-dashed text-sm text-muted-foreground">
                  Thiết bị chưa có cảm biến.
                </div>
              ) : (
                <div className="grid gap-4 lg:grid-cols-[280px_minmax(0,1fr)]">
                  <ResourceSelect
                    resources={
                      device.sensors
                    }
                    value={
                      selectedResourceId
                    }
                    onValueChange={
                      onResourceChange
                    }
                  />

                  <div className="hidden max-h-[min(62dvh,640px)] flex-col gap-2 overflow-y-auto lg:flex">
                    {device.sensors.map(
                      (sensor) => (
                        <SensorResourceButton
                          key={sensor.id}
                          sensor={sensor}
                          selected={
                            sensor.id ===
                            selectedResourceId
                          }
                          onSelect={() => {
                            onResourceChange(
                              sensor.id,
                            )
                          }}
                        />
                      ),
                    )}
                  </div>

                  <div className="min-w-0">
                    {sensorHistory.isPending ? (
                      <Skeleton className="h-80" />
                    ) : sensorHistory.isError ? (
                      <div className="flex min-h-64 flex-col items-center justify-center gap-3 rounded-lg border border-dashed p-6 text-center">
                        <AlertTriangle
                          aria-hidden="true"
                        />

                        <p className="text-sm">
                          Không thể tải dữ liệu cảm biến.
                        </p>

                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => {
                            void sensorHistory.refetch()
                          }}
                        >
                          <RotateCcw className="size-4" />

                          Thử lại
                        </Button>
                      </div>
                    ) : selectedSensor &&
                      selectedSensorSeries
                        ?.points.length ? (
                      <TimeSeriesChart
                        data={
                          selectedSensorSeries
                            .points.map(
                              (point) => ({
                                timestamp:
                                  point.recorded_at,

                                value:
                                  point.value,
                              }),
                            )
                        }
                        unit={
                          selectedSensor.unit
                        }
                        title={
                          selectedSensor.name
                        }
                        currentValue={
                          selectedSensor.latest
                            ?.value ?? null
                        }
                        safeMin={
                          selectedSensor
                            .lower_threshold
                        }
                        safeMax={
                          selectedSensor
                            .upper_threshold
                        }
                        status={
                          selectedSensor
                            .connection_status ===
                          "OFFLINE"
                            ? "offline"
                            : "normal"
                        }
                        rangeLabel={
                          monitoringRangeLabel(
                            range,
                          )
                        }
                        lastUpdatedAt={
                          selectedSensor.latest
                            ?.recorded_at
                        }
                        expectedIntervalMs={
                          monitoringExpectedInterval(
                            range,
                          )
                        }
                      />
                    ) : (
                      <div className="flex min-h-64 flex-col items-center justify-center gap-2 rounded-lg border border-dashed p-6 text-center text-sm text-muted-foreground">
                        <RadioTower
                          aria-hidden="true"
                        />

                        <p>
                          Chưa có dữ liệu đo
                          trong khoảng đã chọn.
                        </p>
                      </div>
                    )}
                  </div>
                </div>
              )}
            </TabsContent>

            {/* ============================================================ */}
            {/* Actuator tab                                                 */}
            {/* ============================================================ */}

            <TabsContent
              value="actuators"
              className="mt-0"
            >
              {!device?.actuators.length ? (
                <div className="flex min-h-64 flex-col items-center justify-center gap-2 rounded-lg border border-dashed p-6 text-center">
                  <Power
                    className="size-6 text-muted-foreground"
                    aria-hidden="true"
                  />

                  <p className="text-sm font-medium">
                    Thiết bị chưa có
                    cơ cấu chấp hành.
                  </p>
                </div>
              ) : (
                <div className="grid gap-4 lg:grid-cols-[280px_minmax(0,1fr)]">
                  <ResourceSelect
                    resources={
                      device.actuators
                    }
                    value={
                      selectedResourceId
                    }
                    onValueChange={
                      onResourceChange
                    }
                  />

                  <div className="hidden max-h-[min(62dvh,640px)] flex-col gap-2 overflow-y-auto lg:flex">
                    {device.actuators.map(
                      (actuator) => (
                        <ActuatorResourceButton
                          key={actuator.id}
                          actuator={actuator}
                          selected={
                            actuator.id ===
                            selectedResourceId
                          }
                          onSelect={() => {
                            onResourceChange(
                              actuator.id,
                            )
                          }}
                        />
                      ),
                    )}
                  </div>

                  <div className="min-w-0">
                    {selectedActuator ? (
                      <ActuatorDashboard
                        actuator={
                          selectedActuator
                        }
                      />
                    ) : (
                      <div className="flex min-h-64 flex-col items-center justify-center gap-2 rounded-lg border border-dashed p-6 text-center text-sm text-muted-foreground">
                        <Activity
                          aria-hidden="true"
                        />

                        <p>
                          Chưa có dữ liệu
                          cơ cấu chấp hành.
                        </p>
                      </div>
                    )}
                  </div>
                </div>
              )}
            </TabsContent>
          </div>
        </Tabs>
      </DialogContent>
    </Dialog>
  )
}

/* ==========================================================================
 * Public Actuator Card
 * ========================================================================== */

function PublicActuatorCard({
  device,
  actuator,
  onOpen,
}: {
  device: MonitoringDevice
  actuator: MonitoringActuator
  onOpen: () => void
}) {
  const command =
    getCommandStatus(
      actuator.latest_command?.status ?? null,
    )

  const awaiting =
    isAwaitingActuatorConfirmation(
      actuator.desired_state,
      actuator.reported_state,
      actuator.latest_command?.status ?? null,
    )

  return (
    <Card className="overflow-hidden">
      <CardHeader>
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0">
            <CardTitle className="text-base">
              {actuator.name}
            </CardTitle>

            <CardDescription className="mt-1">
              {device.name}
            </CardDescription>
          </div>

          <ActuatorConnectionBadge
            status={
              actuator.connection_status
            }
          />
        </div>
      </CardHeader>

      <CardContent className="space-y-4">
        <div className="grid grid-cols-2 gap-3">
          <div className="rounded-lg border p-3">
            <p className="text-xs text-muted-foreground">
              Yêu cầu
            </p>

            <p className="mt-1 text-lg font-semibold">
              {getDesiredStateLabel(
                actuator.desired_state,
              )}
            </p>
          </div>

          <div className="rounded-lg border p-3">
            <p className="text-xs text-muted-foreground">
              Thực tế
            </p>

            <div className="mt-2">
              <ActuatorStateBadge
                state={
                  actuator.reported_state
                }
              />
            </div>
          </div>
        </div>

        <div className="space-y-2 rounded-lg bg-muted/30 p-3">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <span className="text-xs text-muted-foreground">
              Lệnh gần nhất
            </span>

            <Badge
              variant={
                command.tone === "danger"
                  ? "destructive"
                  : command.tone === "success"
                    ? "success"
                    : command.tone === "warning"
                      ? "warning"
                      : "secondary"
              }
            >
              {command.label}
            </Badge>
          </div>

          <div className="flex flex-wrap items-center justify-between gap-2">
            <span className="text-xs text-muted-foreground">
              Cập nhật cuối
            </span>

            <span className="text-xs font-medium">
              {actuator.last_reported_at
                ? formatDateTime(
                    actuator.last_reported_at,
                  )
                : "Chưa có dữ liệu"}
            </span>
          </div>
        </div>

        {awaiting ? (
          <div className="rounded-lg border border-dashed p-3">
            <p className="text-xs text-muted-foreground">
              Đang chờ thiết bị xác nhận
              trạng thái yêu cầu.
            </p>
          </div>
        ) : null}

        {actuator.connection_status ===
        "OFFLINE" ? (
          <p className="text-xs text-muted-foreground">
            Trạng thái trên là dữ liệu cuối
            trước khi mất kết nối.
          </p>
        ) : null}

        <Button
          type="button"
          variant="outline"
          className="w-full"
          onClick={onOpen}
        >
          <Eye className="size-4" />

          Xem dashboard
        </Button>
      </CardContent>
    </Card>
  )
}

/* ==========================================================================
 * Public Monitoring Page
 * ========================================================================== */

export function PublicMonitoringPage() {
  const [range, setRange] =
    useState<MonitoringRange>("24h")

  const [
    monitoringDeviceId,
    setMonitoringDeviceId,
  ] = useState<CoreId | null>(null)

  const [
    monitoringTab,
    setMonitoringTab,
  ] = useState<MonitoringDialogTab>(
    "sensors",
  )

  const [
    monitoringResourceId,
    setMonitoringResourceId,
  ] = useState<CoreId | null>(null)

  /* ------------------------------------------------------------------------
   * Public overview
   * ------------------------------------------------------------------------ */

  const overview =
    useQuery({
      queryKey: [
        "public-monitoring",
        "overview",
      ],

      queryFn:
        publicMonitoringApi.overview,

      refetchInterval: () =>
        document.visibilityState ===
        "visible"
          ? 60_000
          : false,

      refetchIntervalInBackground:
        false,

      staleTime: 30_000,
    })

  /* ------------------------------------------------------------------------
   * Sensor series
   * ------------------------------------------------------------------------ */

  const series =
    useQuery({
      queryKey: [
        "public-monitoring",
        "telemetry-series",
        range,
      ],

      queryFn: () =>
        publicMonitoringApi.telemetrySeries(
          range,
        ),

      enabled:
        Boolean(
          overview.data,
        ),

      staleTime: 30_000,
    })

  /* ------------------------------------------------------------------------
   * Energy
   * ------------------------------------------------------------------------ */

  const energy =
    overview.data?.energy

  const power =
    useQuery({
      queryKey: [
        "public-monitoring",
        "power-series",
        energy?.device.code,
        range,
      ],

      queryFn: () =>
        publicMonitoringApi.powerSeries(
          energy!.device.code,
          range,
        ),

      enabled:
        Boolean(energy),

      staleTime: 30_000,
    })

  /* ------------------------------------------------------------------------
   * Selected device
   * ------------------------------------------------------------------------ */

  const selectedDevice =
    overview.data?.devices.find(
      (device) =>
        device.id ===
        monitoringDeviceId,
    ) ?? null

  /* ------------------------------------------------------------------------
   * All project actuators
   *
   * Sau khi backend bỏ:
   * public_device["actuators"] = []
   *
   * thì danh sách thật sẽ xuất hiện tại đây.
   * ------------------------------------------------------------------------ */

  const projectActuators =
    overview.data?.devices.flatMap(
      (device) =>
        device.actuators.map(
          (actuator) => ({
            device,
            actuator,
          }),
        ),
    ) ?? []

  /* ------------------------------------------------------------------------
   * Dialog
   * ------------------------------------------------------------------------ */

  const openMonitoring = (
    deviceId: CoreId,
    tab: MonitoringDialogTab,
    resourceId?: CoreId,
  ) => {
    setMonitoringDeviceId(
      deviceId,
    )

    setMonitoringTab(
      tab,
    )

    setMonitoringResourceId(
      resourceId ?? null,
    )
  }

  const closeMonitoring = () => {
    setMonitoringDeviceId(
      null,
    )

    setMonitoringResourceId(
      null,
    )

    setMonitoringTab(
      "sensors",
    )
  }

  /* ------------------------------------------------------------------------
   * Refresh
   * ------------------------------------------------------------------------ */

  const refetch = () => {
    void Promise.all([
      overview.refetch(),
      series.refetch(),

      energy
        ? power.refetch()
        : Promise.resolve(),
    ])
  }

  /* ------------------------------------------------------------------------
   * Loading
   * ------------------------------------------------------------------------ */

  if (overview.isLoading) {
    return (
      <main
        className="mx-auto max-w-7xl space-y-5 p-4 sm:p-6 lg:p-8"
        aria-busy="true"
      >
        <Skeleton className="h-28" />

        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <Skeleton className="h-28" />
          <Skeleton className="h-28" />
          <Skeleton className="h-28" />
          <Skeleton className="h-28" />
        </div>

        <Skeleton className="h-96" />

        <span className="sr-only">
          Đang tải Theo dõi từ xa
        </span>
      </main>
    )
  }

  /* ------------------------------------------------------------------------
   * Error
   * ------------------------------------------------------------------------ */

  if (
    overview.isError ||
    !overview.data
  ) {
    return (
      <main className="grid min-h-screen place-items-center p-6">
        <EmptyState
          icon={AlertTriangle}
          title="Theo dõi từ xa chưa khả dụng"
          description="Dự án chưa bật Theo dõi từ xa hoặc deployment chưa cấu hình Project."
        />
      </main>
    )
  }

  const data =
    overview.data

  const isRefetching =
    overview.isFetching ||
    series.isFetching ||
    power.isFetching

  return (
    <>
      <main className="min-h-screen bg-muted/20">
        <div className="mx-auto max-w-7xl space-y-8 p-4 sm:p-6 lg:p-8">

          {/* ============================================================= */}
          {/* Header                                                        */}
          {/* ============================================================= */}

          <header className="space-y-1">
            <p className="text-sm font-medium text-primary">
              Aquaponics Platform · Theo dõi từ xa
            </p>

            <p className="text-sm text-muted-foreground">
              Theo dõi thiết bị,
              cảm biến,
              cơ cấu chấp hành
              và năng lượng ở chế độ chỉ đọc.
            </p>
          </header>

          {/* ============================================================= */}
          {/* Project Monitoring                                            */}
          {/* ============================================================= */}

          <ProjectMonitoringView
            project={data.project}
            summary={data.summary}
            devices={data.devices}
            mode="public-readonly"
            isRefetching={
              isRefetching
            }
            onRefresh={
              refetch
            }
            onOpenMonitoring={
              openMonitoring
            }
          />

          {/* ============================================================= */}
          {/* Actuator section                                              */}
          {/* ============================================================= */}

          <section
            aria-labelledby="public-actuators"
            className="space-y-4"
          >
            <div>
              <div className="flex items-center gap-2">
                <Power
                  className="size-5"
                  aria-hidden="true"
                />

                <h2
                  id="public-actuators"
                  className="text-xl font-semibold"
                >
                  Cơ cấu chấp hành
                </h2>
              </div>

              <p className="mt-1 text-sm text-muted-foreground">
                Theo dõi trạng thái kết nối,
                trạng thái yêu cầu,
                trạng thái thực tế
                và lệnh gần nhất.
              </p>
            </div>

            {projectActuators.length ? (
              <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
                {projectActuators.map(
                  ({
                    device,
                    actuator,
                  }) => (
                    <PublicActuatorCard
                      key={`${device.id}-${actuator.id}`}
                      device={device}
                      actuator={actuator}
                      onOpen={() => {
                        openMonitoring(
                          device.id,
                          "actuators",
                          actuator.id,
                        )
                      }}
                    />
                  ),
                )}
              </div>
            ) : (
              <EmptyState
                icon={Power}
                title="Chưa có cơ cấu chấp hành"
                description="Public Overview chưa trả về cơ cấu chấp hành cho dự án."
              />
            )}
          </section>

          {/* ============================================================= */}
          {/* Range                                                         */}
          {/* ============================================================= */}

          <section
            aria-labelledby="remote-history"
            className="space-y-3"
          >
            <div className="flex flex-wrap items-end justify-between gap-4">
              <div>
                <h2
                  id="remote-history"
                  className="text-xl font-semibold"
                >
                  Lịch sử dữ liệu
                </h2>

                <p className="mt-1 text-sm text-muted-foreground">
                  Chọn khoảng thời gian
                  để xem biểu đồ cảm biến
                  và công suất.
                </p>
              </div>

              <MonitoringRangeSelector
                range={range}
                onRangeChange={setRange}
              />
            </div>
          </section>

          {/* ============================================================= */}
          {/* Sensor charts                                                 */}
          {/* ============================================================= */}

          <section
            aria-labelledby="remote-sensors"
            className="space-y-4"
          >
            <div>
              <h2
                id="remote-sensors"
                className="text-xl font-semibold"
              >
                Biểu đồ cảm biến
              </h2>

              <p className="text-sm text-muted-foreground">
                Dữ liệu thiếu không được
                thay bằng 0.
              </p>
            </div>

            {series.isPending ? (
              <div className="grid gap-4 lg:grid-cols-2">
                <Skeleton className="h-80" />
                <Skeleton className="h-80" />
              </div>
            ) : series.isError ? (
              <EmptyState
                icon={AlertTriangle}
                title="Không thể tải biểu đồ cảm biến"
                description="Không thể tải dữ liệu lịch sử trong khoảng đã chọn."
              />
            ) : data.sensors.length ? (
              <div className="grid gap-4 lg:grid-cols-2">
                {data.sensors.map(
                  (sensor) => {
                    const sensorSeries =
                      series.data?.series.find(
                        (item) =>
                          item.sensor_id ===
                          sensor.id,
                      )

                    const points =
                      sensorSeries?.points ?? []

                    return (
                      <Card
                        key={`${sensor.device_code}-${sensor.code}`}
                      >
                        <CardHeader>
                          <div className="flex items-start justify-between gap-3">
                            <div>
                              <CardTitle className="text-base">
                                {sensor.name}
                              </CardTitle>

                              <CardDescription>
                                {sensor.device_code}
                                {" · "}
                                {sensor.code}
                              </CardDescription>
                            </div>

                            <StatusBadge
                              value={
                                sensor.connection_status ===
                                "OFFLINE"
                                  ? "OFFLINE"
                                  : sensor.latest
                                        ?.quality ??
                                    "NO_DATA"
                              }
                            />
                          </div>
                        </CardHeader>

                        <CardContent>
                          {points.length ? (
                            <TimeSeriesChart
                              title={
                                sensor.name
                              }
                              unit={
                                sensor.unit
                              }
                              currentValue={
                                sensor.latest
                                  ?.value ?? null
                              }
                              rangeLabel={
                                monitoringRangeLabel(
                                  range,
                                )
                              }
                              lastUpdatedAt={
                                sensor.latest
                                  ?.recorded_at ??
                                null
                              }
                              expectedIntervalMs={
                                monitoringExpectedInterval(
                                  range,
                                )
                              }
                              status={
                                sensor.connection_status ===
                                "OFFLINE"
                                  ? "offline"
                                  : "normal"
                              }
                              data={
                                points.map(
                                  (point) => ({
                                    timestamp:
                                      point.recorded_at,

                                    value:
                                      point.value,
                                  }),
                                )
                              }
                            />
                          ) : (
                            <div className="flex min-h-64 flex-col items-center justify-center gap-2 rounded-lg border border-dashed p-6 text-center">
                              <RadioTower
                                className="size-6 text-muted-foreground"
                                aria-hidden="true"
                              />

                              <p className="text-sm font-medium">
                                Chưa có dữ liệu
                              </p>

                              <p className="text-xs text-muted-foreground">
                                Không có dữ liệu trong{" "}
                                {monitoringRangeLabel(
                                  range,
                                )}
                                .
                              </p>
                            </div>
                          )}
                        </CardContent>
                      </Card>
                    )
                  },
                )}
              </div>
            ) : (
              <EmptyState
                icon={Activity}
                title="Chưa có cảm biến"
                description="Dự án chưa có cảm biến đang hoạt động."
              />
            )}
          </section>

          {/* ============================================================= */}
          {/* Energy Monitor                                                */}
          {/* ============================================================= */}

          {energy ? (
            <section
              aria-labelledby="remote-energy"
              className="space-y-4"
            >
              <div>
                <h2
                  id="remote-energy"
                  className="text-xl font-semibold"
                >
                  Thiết bị năng lượng
                </h2>

                <p className="text-sm text-muted-foreground">
                  {energy.device.name}
                  {" · "}
                  {energy.device.connectivity}
                </p>
              </div>

              <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
                {Object.values(
                  energy.measurements,
                ).map(
                  (item) => (
                    <Card
                      key={
                        item.model_code
                      }
                    >
                      <CardHeader className="pb-2">
                        <CardTitle className="text-base">
                          {item.name}
                        </CardTitle>

                        <CardDescription>
                          {item.freshness}
                          {" · "}
                          {item.quality}
                        </CardDescription>
                      </CardHeader>

                      <CardContent>
                        <p className="text-2xl font-semibold tabular-nums">
                          {displayValue(
                            item.display_value,
                            item.unit,
                          )}
                        </p>

                        {energy.device.connectivity ===
                        "OFFLINE" ? (
                          <p className="mt-2 text-xs text-muted-foreground">
                            Dữ liệu cuối trước khi
                            thiết bị mất kết nối.
                          </p>
                        ) : null}
                      </CardContent>
                    </Card>
                  ),
                )}
              </div>

              <Card>
                <CardHeader>
                  <CardTitle>
                    Công suất tiêu thụ
                  </CardTitle>

                  <CardDescription>
                    POWER_W trung bình theo bucket;
                    khoảng thời gian không có dữ liệu
                    vẫn được giữ là khoảng trống.
                  </CardDescription>
                </CardHeader>

                <CardContent>
                  {power.isPending ? (
                    <Skeleton className="h-72" />
                  ) : power.isError ? (
                    <EmptyState
                      icon={AlertTriangle}
                      title="Không thể tải biểu đồ công suất"
                      description="Không thể tải dữ liệu POWER_W."
                    />
                  ) : power.data?.points.length ? (
                    <TimeSeriesChart
                      title="Công suất tiêu thụ"
                      unit="W"
                      currentValue={
                        energy.measurements
                          .power
                          ?.display_value ??
                        null
                      }
                      rangeLabel={
                        monitoringRangeLabel(
                          range,
                        )
                      }
                      lastUpdatedAt={
                        energy.device
                          .last_received_at
                      }
                      expectedIntervalMs={
                        monitoringExpectedInterval(
                          range,
                        )
                      }
                      status={
                        energy.device.connectivity ===
                        "OFFLINE"
                          ? "offline"
                          : "normal"
                      }
                      data={
                        power.data.points.map(
                          (point) => ({
                            timestamp:
                              point.bucket_time,

                            value:
                              point.avg_value,
                          }),
                        )
                      }
                    />
                  ) : (
                    <div className="flex min-h-64 items-center justify-center rounded-lg border border-dashed p-6 text-center text-sm text-muted-foreground">
                      Chưa có dữ liệu công suất
                      trong khoảng đã chọn.
                    </div>
                  )}
                </CardContent>
              </Card>
            </section>
          ) : null}
        </div>
      </main>

      {/* ================================================================ */}
      {/* Device Monitoring Dialog                                         */}
      {/* ================================================================ */}

      <PublicDeviceMonitoringDialog
        open={
          selectedDevice !== null
        }
        device={
          selectedDevice
        }
        tab={
          monitoringTab
        }
        resourceId={
          monitoringResourceId
        }
        range={
          range
        }
        onOpenChange={(
          open: boolean,
        ) => {
          if (!open) {
            closeMonitoring()
          }
        }}
        onTabChange={(
          tab: MonitoringDialogTab,
        ) => {
          setMonitoringTab(tab)

          setMonitoringResourceId(
            null,
          )
        }}
        onResourceChange={(
          resourceId: CoreId,
        ) => {
          setMonitoringResourceId(
            resourceId,
          )
        }}
        onRangeChange={(
          nextRange: MonitoringRange,
        ) => {
          setRange(nextRange)
        }}
      />
    </>
  )
}
