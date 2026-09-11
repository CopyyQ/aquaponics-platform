import { useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowLeft, BellRing, Clock3, Gauge } from "lucide-react";
import { Link, useParams } from "react-router-dom";
import { sensorApi } from "@/entities/sensor/api/sensor-api";
import { sensorModelApi } from "@/entities/sensor-model/api/sensor-model-api";
import { deviceApi } from "@/entities/device/api/device-api";
import { telemetryApi } from "@/entities/telemetry/api/telemetry-api";
import { buildMonitoringWindow } from "@/entities/telemetry/lib/monitoring-range";
import type { MonitoringRange } from "@/entities/telemetry/model/project-monitoring";
import { ThresholdDialog } from "@/features/update-sensor-threshold/components/ThresholdDialog";
import { EditSensorDialog } from "@/features/edit-sensor/components/EditSensorDialog";
import { SensorChartRenderer } from "@/features/sensor-monitoring/components/SensorChartRenderer";
import { MonitoringRangeSelector } from "@/features/view-device-monitoring-history/ui/MonitoringRangeSelector";
import { useAuthStore } from "@/features/auth/model/auth-store";
import { useProtectedQueryScope } from "@/features/auth/model/use-protected-query-scope";
import { queryKeys } from "@/shared/api/query-keys";
import { canManageThresholds } from "@/features/auth/lib/permission-policy";
import { formatDateTime } from "@/shared/lib/date";
import { Button } from "@/shared/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/shared/ui/card";
import { PageHeader } from "@/shared/ui/page-header";
import { Skeleton } from "@/shared/ui/skeleton";
import { StatusBadge } from "@/shared/ui/status-badge";
import { invalidateQueries } from "@/shared/api/query-invalidation";
import { toast } from "sonner";

export function SensorDetailPage() {
  const sensorId = Number(useParams().sensorId);
  const projectId = Number(useParams().projectId);
  const routeDeviceId = Number(useParams().deviceId);
  const role = useAuthStore((state) => state.user?.system_role);
  const { active, queryScope } = useProtectedQueryScope();
  const client = useQueryClient();
  const [range, setRange] = useState<MonitoringRange>("24h");
  const sensor = useQuery({
    queryKey: queryKeys.sensors.detail(
      queryScope,
      projectId,
      routeDeviceId,
      sensorId,
    ),
    queryFn: () => sensorApi.getInProject(projectId, routeDeviceId, sensorId),
    enabled:
      active &&
      Number.isFinite(sensorId) &&
      Number.isFinite(projectId) &&
      Number.isFinite(routeDeviceId),
  });
  const deviceId = sensor.data?.device_id ?? 0;
  const device = useQuery({
    queryKey: queryKeys.devices.detail(queryScope, projectId, routeDeviceId),
    queryFn: () => deviceApi.overview(routeDeviceId),
    enabled: active && routeDeviceId > 0 && deviceId === routeDeviceId,
  });
  const models = useQuery({
    queryKey: queryKeys.sensorModels.list(queryScope),
    queryFn: sensorModelApi.list,
    enabled: active,
  });
  const { start, end } = useMemo(() => buildMonitoringWindow(range), [range]);
  const history = useQuery({
    queryKey: queryKeys.sensors.history(
      queryScope,
      projectId,
      routeDeviceId,
      sensorId,
      range,
      "AUTO",
    ),
    queryFn: () =>
      telemetryApi.history(sensorId, start.toISOString(), end.toISOString()),
    enabled:
      active &&
      sensor.data?.device_id === routeDeviceId &&
      device.data?.project?.id === projectId,
  });
  const lifecycle = useMutation({
    mutationFn: () =>
      sensor.data?.is_enabled
        ? sensorApi.disableFromDevice(
            routeDeviceId,
            sensorId,
            "Tắt từ trang quản trị",
          )
        : sensorApi.activateToDevice(routeDeviceId, sensorId),
    onSuccess: async () => {
      await invalidateQueries.sensors(
        client,
        queryScope,
        projectId,
        routeDeviceId,
        sensorId,
      );
      toast.success(
        sensor.data?.is_enabled
          ? "Đã vô hiệu hóa cảm biến"
          : "Đã kích hoạt cảm biến",
      );
    },
    onError: () => toast.error("Không thể cập nhật cảm biến"),
  });
  if (sensor.isLoading) return <Skeleton className="h-96" />;
  if (!sensor.data) return <div>Không tìm thấy cảm biến.</div>;
  const model = models.data?.find(
    (item) => item.id === sensor.data.sensor_model_id,
  );
  const devicePath = projectId
    ? `${role === "ADMIN" ? "/admin" : ""}/projects/${projectId}/devices/${sensor.data.device_id}`
    : role === "ADMIN"
      ? "/admin/overview"
      : "/projects";
  return (
    <div className="space-y-7">
      <Button asChild variant="ghost" size="sm">
        <Link to={devicePath}>
          <ArrowLeft /> Quay lại thiết bị
        </Link>
      </Button>
      <PageHeader
        title={sensor.data.name}
        description={`${sensor.data.code} · ${model?.name ?? "Cảm biến"}`}
        actions={
          <div className="flex flex-wrap gap-2">
            <StatusBadge value={sensor.data.status} />
            {role === "ADMIN" ? (
              <>
                <EditSensorDialog sensor={sensor.data} projectId={projectId} />
                <Button
                  variant="outline"
                  size="sm"
                  disabled={lifecycle.isPending}
                  onClick={() => {
                    if (
                      window.confirm(
                        sensor.data?.is_enabled
                          ? "Bạn có chắc muốn vô hiệu hóa cảm biến này? Dữ liệu lịch sử vẫn được giữ lại."
                          : "Kích hoạt lại cảm biến này?",
                      )
                    )
                      lifecycle.mutate();
                  }}
                >
                  {sensor.data.is_enabled ? "Vô hiệu hóa" : "Kích hoạt lại"}
                </Button>
              </>
            ) : null}
            {canManageThresholds(role) && (
              <ThresholdDialog sensor={sensor.data} />
            )}
          </div>
        }
      />
      <div className="grid gap-4 md:grid-cols-3">
        <Card>
          <CardContent className="p-5">
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              <Gauge className="size-4" /> Khoảng cảnh báo
            </div>
            <div className="mt-3 text-xl font-bold">
              {sensor.data.lower_threshold ?? "—"} –{" "}
              {sensor.data.upper_threshold ?? "—"} {model?.unit}
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-5">
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              <BellRing className="size-4" /> Cảnh báo
            </div>
            <div className="mt-3 text-xl font-bold">
              {sensor.data.warning_enabled ? "Đang bật" : "Đã tắt"}
            </div>
            <div className="text-xs text-muted-foreground">
              Trì hoãn {sensor.data.alert_delay_seconds} giây
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-5">
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              <Clock3 className="size-4" /> Dữ liệu gần nhất
            </div>
            <div className="mt-3 text-base font-bold">
              {formatDateTime(sensor.data.last_seen_at)}
            </div>
          </CardContent>
        </Card>
      </div>
      <Card>
        <CardHeader className="flex-row items-center justify-between">
          <div>
            <CardTitle>Biểu đồ lịch sử</CardTitle>
            <CardDescription>
              Mỗi Sensor có query và biểu đồ riêng theo loại dữ liệu.
            </CardDescription>
          </div>
          <MonitoringRangeSelector range={range} onRangeChange={setRange} />
        </CardHeader>
        <CardContent>
          {history.isLoading ? (
            <Skeleton className="h-80" />
          ) : history.isError ? (
            <div className="grid h-80 place-items-center text-sm text-destructive">
              Không thể tải dữ liệu cảm biến.
            </div>
          ) : history.data?.length ? (
            <SensorChartRenderer
              modelCode={model?.code}
              data={history.data}
              unit={model?.unit}
              safeMin={sensor.data.lower_threshold}
              safeMax={sensor.data.upper_threshold}
              lastUpdatedAt={sensor.data.last_seen_at}
            />
          ) : (
            <div className="grid h-80 place-items-center text-sm text-muted-foreground">
              Chưa có dữ liệu trong khoảng đã chọn.
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
