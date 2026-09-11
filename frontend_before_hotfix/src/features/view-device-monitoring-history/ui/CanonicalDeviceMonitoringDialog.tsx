import { Activity, AlertTriangle, RadioTower } from "lucide-react";
import { useEffect, useState, type ReactNode } from "react";
import type {
  MonitoringActuatorHistoryRead,
  MonitoringDevice,
  MonitoringRange,
  MonitoringSeriesRead,
} from "@/api/contracts";
import type { MonitoringDialogTab } from "@/features/view-device-monitoring-history/model/monitoring-dialog.types";
import { ActuatorOperationChart } from "@/features/view-device-monitoring-history/ui/ActuatorOperationChart";
import {
  actuatorStateLabel,
  commandStatusLabel,
  connectionLabel,
  desiredStateLabel,
  synchronizationLabel,
} from "@/entities/actuator/lib/actuator-semantics";
import { MonitoringRangeSelector } from "@/features/view-device-monitoring-history/ui/MonitoringRangeSelector";
import { TimeSeriesChart } from "@/shared/charts/time-series";
import { formatDateTime } from "@/shared/lib/date";
import { Badge } from "@/shared/ui/badge";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/shared/ui/dialog";
import { Skeleton } from "@/shared/ui/skeleton";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/shared/ui/tabs";

interface Props {
  device: MonitoringDevice | null;
  series: MonitoringSeriesRead;
  actuatorHistory?: MonitoringActuatorHistoryRead;
  range: MonitoringRange;
  tab?: MonitoringDialogTab;
  resourceId?: string | null;
  loading?: boolean;
  error?: unknown;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onTabChange?: (tab: MonitoringDialogTab) => void;
  onResourceChange?: (id: string) => void;
  onRangeChange?: (range: MonitoringRange) => void;
  renderSeries?: unknown;
}

export function CanonicalDeviceMonitoringDialog({
  device,
  series,
  actuatorHistory,
  range,
  tab = "sensors",
  resourceId = null,
  loading = false,
  error,
  open,
  onOpenChange,
  onTabChange,
  onResourceChange,
  onRangeChange,
}: Props) {
  const [localTab, setLocalTab] = useState<MonitoringDialogTab>(tab);
  const [localResourceId, setLocalResourceId] = useState<string | null>(
    resourceId,
  );
  const activeTab = onTabChange ? tab : localTab;
  const resources =
    activeTab === "sensors"
      ? (device?.sensors ?? [])
      : (device?.actuators ?? []);
  const requestedResourceId = onResourceChange ? resourceId : localResourceId;
  const selectedResourceId = resources.some(
    (item) => item.id === requestedResourceId,
  )
    ? requestedResourceId
    : (resources[0]?.id ?? null);
  const selectedSensor =
    activeTab === "sensors"
      ? (device?.sensors.find((item) => item.id === selectedResourceId) ?? null)
      : null;
  const selectedActuator =
    activeTab === "actuators"
      ? (device?.actuators.find((item) => item.id === selectedResourceId) ??
        null)
      : null;

  useEffect(() => {
    if (!onTabChange) setLocalTab(tab);
  }, [tab, onTabChange]);

  useEffect(() => {
    if (!onResourceChange) setLocalResourceId(resourceId);
  }, [resourceId, onResourceChange]);

  const changeTab = (next: MonitoringDialogTab) => {
    if (onTabChange) onTabChange(next);
    else {
      setLocalTab(next);
      setLocalResourceId(null);
    }
  };
  const changeResource = (id: string) => {
    if (onResourceChange) onResourceChange(id);
    else setLocalResourceId(id);
  };
  const selectedSeries = selectedSensor
    ? series.series.find((item) => item.sensor_id === selectedSensor.id)
    : undefined;
  const selectedActuatorHistory = selectedActuator
    ? actuatorHistory?.items.find(
        (item) => item.actuator_id === selectedActuator.id,
      )
    : undefined;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="flex max-h-[calc(100dvh-1rem)] max-w-[min(1380px,calc(100vw-1rem))] flex-col gap-4 overflow-hidden p-4 sm:max-h-[calc(100dvh-2rem)] sm:p-6">
        <DialogHeader className="pr-8">
          <div className="flex flex-wrap items-center gap-2">
            <DialogTitle>Theo dõi: {device?.name ?? "Thiết bị"}</DialogTitle>
            {device ? (
              <ConnectionBadge status={device.connection_status} />
            ) : null}
          </div>
          <DialogDescription>
            {device?.location ?? "Chưa cập nhật vị trí"} · Cập nhật cuối:{" "}
            {device?.last_seen_at
              ? formatDateTime(device.last_seen_at)
              : "Chưa có dữ liệu"}
          </DialogDescription>
        </DialogHeader>
        {onRangeChange ? (
          <MonitoringRangeSelector
            range={range}
            onRangeChange={onRangeChange}
          />
        ) : null}
        <Tabs
          value={activeTab}
          onValueChange={(value) => changeTab(value as MonitoringDialogTab)}
          className="flex min-h-0 flex-1 flex-col"
        >
          <TabsList className="w-full sm:w-fit">
            <TabsTrigger value="sensors" className="flex-1 sm:flex-none">
              Cảm biến ({device?.sensors.length ?? 0})
            </TabsTrigger>
            <TabsTrigger value="actuators" className="flex-1 sm:flex-none">
              Cơ cấu chấp hành ({device?.actuators.length ?? 0})
            </TabsTrigger>
          </TabsList>
          <div className="mt-3 min-h-0 flex-1 overflow-y-auto">
            <TabsContent value="sensors" className="mt-0">
              {!device?.sensors.length ? (
                <Empty
                  icon={<RadioTower />}
                  text="Thiết bị chưa có cảm biến."
                />
              ) : (
                <div className="grid gap-4 lg:grid-cols-[280px_minmax(0,1fr)]">
                  <div className="flex max-h-[min(62dvh,640px)] flex-col gap-2 overflow-y-auto">
                    {device.sensors.map((sensor) => (
                      <button
                        key={sensor.id}
                        type="button"
                        onClick={() => changeResource(sensor.id)}
                        className={`rounded-lg border p-3 text-left transition ${sensor.id === selectedResourceId ? "border-primary bg-primary/5" : "hover:bg-muted/50"}`}
                      >
                        <div className="flex items-start justify-between gap-2">
                          <div className="min-w-0">
                            <p className="truncate font-medium">
                              {sensor.name}
                            </p>
                            <p className="truncate font-mono text-xs text-muted-foreground">
                              {sensor.code}
                            </p>
                          </div>
                          <FreshnessBadge
                            value={
                              sensor.latest?.freshness ?? sensor.data_status
                            }
                          />
                        </div>
                        <p className="mt-2 text-lg font-semibold tabular-nums">
                          {sensor.latest?.value ?? "—"}
                          {sensor.latest?.value == null
                            ? ""
                            : ` ${sensor.unit}`}
                        </p>
                      </button>
                    ))}
                  </div>
                  <div className="min-w-0">
                    {loading ? (
                      <Skeleton className="h-80" />
                    ) : error ? (
                      <Empty
                        icon={<AlertTriangle />}
                        text="Không thể tải chuỗi thời gian của cảm biến."
                      />
                    ) : selectedSensor && selectedSeries?.points.length ? (
                      <TimeSeriesChart
                        data={selectedSeries.points.map((point) => ({
                          timestamp: point.recorded_at,
                          value: point.value,
                        }))}
                        unit={selectedSensor.unit}
                        title={selectedSensor.name}
                        currentValue={selectedSensor.latest?.value ?? null}
                        safeMin={selectedSensor.lower_threshold}
                        safeMax={selectedSensor.upper_threshold}
                        status={
                          selectedSensor.latest?.freshness === "STALE"
                            ? "stale"
                            : selectedSensor.connection_status === "OFFLINE"
                              ? "offline"
                              : "normal"
                        }
                        rangeLabel={range.toUpperCase()}
                        lastUpdatedAt={
                          selectedSensor.latest?.recorded_at ?? null
                        }
                      />
                    ) : (
                      <Empty
                        icon={<RadioTower />}
                        text="Chưa có dữ liệu đo trong khoảng đã chọn."
                      />
                    )}
                  </div>
                </div>
              )}
            </TabsContent>
            <TabsContent value="actuators" className="mt-0">
              {!device?.actuators.length ? (
                <Empty
                  icon={<Activity />}
                  text="Thiết bị chưa có cơ cấu chấp hành."
                />
              ) : (
                <div className="grid gap-4 lg:grid-cols-[280px_minmax(0,1fr)]">
                  <div className="flex max-h-[min(62dvh,640px)] flex-col gap-2 overflow-y-auto">
                    {device.actuators.map((actuator) => (
                      <button
                        key={actuator.id}
                        type="button"
                        onClick={() => changeResource(actuator.id)}
                        className={`rounded-lg border p-3 text-left transition ${actuator.id === selectedResourceId ? "border-primary bg-primary/5" : "hover:bg-muted/50"}`}
                      >
                        <p className="truncate font-medium">{actuator.name}</p>
                        <p className="truncate font-mono text-xs text-muted-foreground">
                          {actuator.code}
                        </p>
                        <div className="mt-2 flex flex-wrap gap-2">
                          <Badge
                            variant={
                              actuator.reported_state === true
                                ? "success"
                                : "secondary"
                            }
                          >
                            {actuatorStateLabel(actuator.reported_state)}
                          </Badge>
                          <Badge
                            variant={
                              actuator.synchronization_status === "IN_SYNC"
                                ? "success"
                                : actuator.synchronization_status ===
                                    "OUT_OF_SYNC"
                                  ? "warning"
                                  : "outline"
                            }
                          >
                            {synchronizationLabel(
                              actuator.desired_state,
                              actuator.reported_state,
                            )}
                          </Badge>
                        </div>
                      </button>
                    ))}
                  </div>
                  {selectedActuator ? (
                    <div className="min-w-0 space-y-4">
                      <div className="space-y-4 rounded-xl border p-4">
                        <div className="flex flex-wrap items-start justify-between gap-2">
                          <div>
                            <h3 className="text-balance text-lg font-semibold">
                              {selectedActuator.name}
                            </h3>
                            <p className="text-sm text-muted-foreground">
                              {selectedActuator.code} ·{" "}
                              {selectedActuator.actuator_model ??
                                "Chưa có model"}
                            </p>
                          </div>
                          <ConnectionBadge
                            status={selectedActuator.connection_status}
                          />
                        </div>
                        <div className="grid gap-3 sm:grid-cols-3">
                          <Metric
                            label="Trạng thái"
                            value={actuatorStateLabel(
                              selectedActuator.reported_state,
                            )}
                          />
                          <Metric
                            label="Điện áp"
                            value={
                              selectedActuator.electrical.voltage.value == null
                                ? "—"
                                : `${selectedActuator.electrical.voltage.value} V`
                            }
                          />
                          <Metric
                            label="Dòng điện"
                            value={
                              selectedActuator.electrical.current.value == null
                                ? "—"
                                : `${selectedActuator.electrical.current.value} A`
                            }
                          />
                        </div>
                        <div className="text-sm text-muted-foreground">
                          <p>
                            {desiredStateLabel(selectedActuator.desired_state)}{" "}
                            ·{" "}
                            {synchronizationLabel(
                              selectedActuator.desired_state,
                              selectedActuator.reported_state,
                            )}
                          </p>
                          <p>
                            Lệnh gần nhất:{" "}
                            {commandStatusLabel(
                              selectedActuator.latest_command?.status,
                            )}
                          </p>
                        </div>
                        {selectedActuator.active_alert ? (
                          <div className="rounded-lg border border-destructive/30 bg-destructive/5 p-4 text-sm text-destructive">
                            <strong>
                              {selectedActuator.active_alert.rule_name}
                            </strong>
                            <p className="mt-1">
                              {selectedActuator.active_alert.condition_summary}
                            </p>
                          </div>
                        ) : null}
                      </div>
                      {loading ? (
                        <>
                          <Skeleton className="h-64" />
                          <Skeleton className="h-32" />
                        </>
                      ) : error ? (
                        <Empty
                          icon={<AlertTriangle />}
                          text="Không thể tải lịch sử bật/tắt của cơ cấu chấp hành."
                        />
                      ) : selectedActuatorHistory ? (
                        <>
                          <ActuatorOperationChart
                            actuatorName={selectedActuator.name}
                            states={selectedActuatorHistory.points}
                            readings={selectedActuatorHistory.readings}
                            startTime={actuatorHistory?.start_at}
                            endTime={actuatorHistory?.end_at}
                          />
                        </>
                      ) : (
                        <Empty
                          icon={<Activity />}
                          text="Chưa có lịch sử bật/tắt trong khoảng đã chọn."
                        />
                      )}
                    </div>
                  ) : null}
                </div>
              )}
            </TabsContent>
          </div>
        </Tabs>
      </DialogContent>
    </Dialog>
  );
}

function ConnectionBadge({ status }: { status: string }) {
  const label = connectionLabel(status);
  return (
    <Badge
      variant={
        status === "ONLINE"
          ? "success"
          : status === "OFFLINE"
            ? "destructive"
            : "warning"
      }
    >
      {label}
    </Badge>
  );
}

function FreshnessBadge({ value }: { value: string | null | undefined }) {
  const normalized =
    value === "FRESH"
      ? "Đang báo"
      : value === "STALE"
        ? "Dữ liệu cũ"
        : value === "OFFLINE"
          ? "Ngoại tuyến"
          : "Chưa có dữ liệu";
  return (
    <Badge
      variant={
        value === "FRESH"
          ? "success"
          : value === "STALE"
            ? "warning"
            : "secondary"
      }
    >
      {normalized}
    </Badge>
  );
}

function Empty({ icon, text }: { icon: ReactNode; text: string }) {
  return (
    <div className="flex min-h-64 flex-col items-center justify-center gap-2 rounded-lg border border-dashed p-6 text-center text-sm text-muted-foreground">
      {icon}
      <p>{text}</p>
    </div>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg border bg-muted/20 p-3">
      <p className="text-xs text-muted-foreground">{label}</p>
      <p className="mt-1 font-semibold">{value}</p>
    </div>
  );
}
