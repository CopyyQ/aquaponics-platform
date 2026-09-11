import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { RadioTower } from "lucide-react";
import { Link, useParams } from "react-router-dom";
import { deviceApi } from "@/entities/device/api/device-api";
import { projectApi } from "@/entities/project/api/project-api";
import { sensorApi } from "@/entities/sensor/api/sensor-api";
import { actuatorApi } from "@/entities/actuator/api/actuator-api";
import { sensorModelApi } from "@/entities/sensor-model/api/sensor-model-api";
import { MqttConnectionPanel } from "@/features/export-project-config/components/MqttConnectionPanel";
import { SensorCard } from "@/features/manage-sensor-lifecycle/components/SensorCard";
import { SensorFormDialog } from "@/features/create-sensor/components/SensorFormDialog";
import { ActuatorCard } from "@/features/manage-actuator/components/ActuatorCard";
import { ActuatorFormDialog } from "@/features/create-actuator/components/ActuatorFormDialog";
import { EditDeviceDialog } from "@/features/edit-device/components/EditDeviceDialog";
import { useAuthStore } from "@/features/auth/model/auth-store";
import { useProtectedQueryScope } from "@/features/auth/model/use-protected-query-scope";
import { queryKeys } from "@/shared/api/query-keys";
import { canManageInfrastructure } from "@/features/auth/lib/permission-policy";
import { formatDateTime } from "@/shared/lib/date";
import { Card, CardContent } from "@/shared/ui/card";
import { EmptyState } from "@/shared/ui/empty-state";
import { PageHeader } from "@/shared/ui/page-header";
import { Skeleton } from "@/shared/ui/skeleton";
import { StatusBadge } from "@/shared/ui/status-badge";
import { Button } from "@/shared/ui/button";
import { invalidateQueries } from "@/shared/api/query-invalidation";
import { toast } from "sonner";
import { EnergyMonitorDashboard } from "@/widgets/energy-monitor-dashboard/EnergyMonitorDashboard";

export function DeviceDetailPage() {
  const deviceId = Number(useParams().deviceId);
  const projectId = Number(useParams().projectId);
  const role = useAuthStore((state) => state.user?.system_role);
  const { active, queryScope } = useProtectedQueryScope();
  const client = useQueryClient();
  const enabled =
    active && Number.isFinite(deviceId) && Number.isFinite(projectId);
  const overview = useQuery({
    queryKey: queryKeys.devices.detail(queryScope, projectId, deviceId),
    queryFn: () => deviceApi.overview(deviceId),
    enabled,
  });
  const sensors = useQuery({
    queryKey: [
      ...queryKeys.devices.sensors(queryScope, projectId, deviceId),
      { includeDisabled: role === "ADMIN" },
    ],
    queryFn: () => sensorApi.listByDevice(deviceId, role === "ADMIN"),
    enabled: enabled && overview.data?.device.device_kind !== "ENERGY_MONITOR",
  });
  const actuators = useQuery({
    queryKey: [
      ...queryKeys.actuators.list(queryScope, projectId, deviceId),
      { includeDisabled: role === "ADMIN" },
    ],
    queryFn: () => actuatorApi.list(projectId, deviceId, role === "ADMIN"),
    enabled: enabled && overview.data?.device.device_kind !== "ENERGY_MONITOR",
    refetchInterval: (query) =>
      query.state.data?.some(
        (actuator) =>
          actuator.is_enabled &&
          actuator.desired_state !== actuator.reported_state,
      )
        ? 3000
        : false,
  });
  const models = useQuery({
    queryKey: queryKeys.sensorModels.list(queryScope),
    queryFn: sensorModelApi.list,
    enabled: active && overview.data?.device.device_kind !== "ENERGY_MONITOR",
  });
  const lifecycle = useMutation({
    mutationFn: () => {
      const currentDevice = overview.data?.device;
      if (!currentDevice) throw new Error("Device chưa sẵn sàng");
      return currentDevice.is_enabled
        ? projectApi.disableDevice(projectId, deviceId, "Tắt từ trang quản trị")
        : projectApi.activateDevice(projectId, deviceId);
    },
    onSuccess: async () => {
      await invalidateQueries.devices(client, queryScope, projectId, deviceId);
      toast.success(
        overview.data?.device.is_enabled
          ? "Đã vô hiệu hóa Device"
          : "Đã kích hoạt Device",
      );
    },
    onError: () => toast.error("Không thể cập nhật Device"),
  });
  if (overview.isLoading) return <Skeleton className="h-96" />;
  if (
    overview.isError ||
    !overview.data ||
    overview.data.project?.id !== projectId
  )
    return (
      <EmptyState
        icon={RadioTower}
        title="Không tìm thấy thiết bị"
        description="Thiết bị không tồn tại trong dự án này hoặc bạn không có quyền xem."
      />
    );
  const device = overview.data.device;
  const isEnergyMonitor = device.device_kind === "ENERGY_MONITOR";
  return (
    <div className="flex flex-col gap-7">
      <nav
        aria-label="Breadcrumb"
        className="flex flex-wrap items-center gap-2 text-sm text-muted-foreground"
      >
        <Link to="/admin/users" className="hover:underline">
          Danh mục khách hàng
        </Link>
        <span>→</span>
        {overview.data.owner ? (
          <>
            <Link
              to={`/admin/users/${overview.data.owner.id}`}
              className="hover:underline"
            >
              {overview.data.owner.full_name}
            </Link>
            <span>→</span>
          </>
        ) : null}
        {overview.data.project ? (
          <>
            <Link
              to={`/admin/projects/${overview.data.project.id}/overview`}
              className="hover:underline"
            >
              {overview.data.project.name}
            </Link>
            <span>→</span>
          </>
        ) : null}
        <span className="text-foreground">{device.name}</span>
      </nav>
      <PageHeader
        title={device.name}
        description={
          device.location || device.description || "Chưa có mô tả vị trí"
        }
        actions={
          <div className="flex flex-wrap items-center gap-2">
            <StatusBadge value={device.status} />
            {role === "ADMIN" ? (
              <>
                <EditDeviceDialog device={device} projectId={projectId} />
                <Button
                  variant="outline"
                  size="sm"
                  disabled={lifecycle.isPending}
                  onClick={() => lifecycle.mutate()}
                >
                  {device.is_enabled ? "Vô hiệu hóa" : "Kích hoạt lại"}
                </Button>
              </>
            ) : null}
          </div>
        }
      />
      {isEnergyMonitor ? <EnergyMonitorDashboard projectId={projectId} deviceId={deviceId} projectName={overview.data.project?.name} /> : <>
      <Card>
        <CardContent className="grid gap-5 p-5 sm:grid-cols-2 xl:grid-cols-4">
          <div>
            <div className="text-xs uppercase text-muted-foreground">
              Mã thiết bị
            </div>
            <div className="mt-1 font-mono font-semibold">{device.code}</div>
          </div>
          <div>
            <div className="text-xs uppercase text-muted-foreground">Dự án</div>
            <div className="mt-1 font-medium">
              {overview.data.project?.name ?? "—"}
            </div>
          </div>
          <div>
            <div className="text-xs uppercase text-muted-foreground">
              Khách hàng sở hữu
            </div>
            <div className="mt-1 font-medium">
              {overview.data.owner?.full_name ?? "—"}
            </div>
          </div>
          <div>
            <div className="text-xs uppercase text-muted-foreground">
              Nhận dữ liệu cuối
            </div>
            <div className="mt-1 font-medium">
              {formatDateTime(device.last_seen_at)}
            </div>
          </div>
          <div>
            <div className="text-xs uppercase text-muted-foreground">
              Số cảm biến
            </div>
            <div className="mt-1 font-semibold">
              {sensors.data?.length ?? 0}
            </div>
          </div>
        </CardContent>
      </Card>
      <MqttConnectionPanel device={device} />
      {role === "ADMIN" ? (
        <section>
          <PageHeader
            title="Cơ cấu chấp hành"
            description="Trạng thái bật/tắt là trạng thái vận hành, tách biệt với trạng thái quản lý."
            actions={
              <ActuatorFormDialog projectId={projectId} deviceId={deviceId} />
            }
          />
          <div className="mt-5 grid gap-4 md:grid-cols-2">
            {actuators.isLoading ? (
              <Skeleton className="h-48" />
            ) : actuators.isError ? (
              <EmptyState
                icon={RadioTower}
                title="Không thể tải cơ cấu chấp hành"
                description="Vui lòng thử lại."
              />
            ) : actuators.data?.length ? (
              actuators.data.map((actuator) => (
                <ActuatorCard
                  key={actuator.id}
                  actuator={actuator}
                  projectId={projectId}
                  deviceStatus={device.status}
                  deviceName={device.name}
                />
              ))
            ) : (
              <EmptyState
                icon={RadioTower}
                title="Chưa có cơ cấu chấp hành"
                description="Thêm cơ cấu chấp hành để quản lý đầu ra bật/tắt của thiết bị."
                action={
                  <ActuatorFormDialog
                    projectId={projectId}
                    deviceId={deviceId}
                  />
                }
              />
            )}
          </div>
        </section>
      ) : null}
      <section>
        <PageHeader
          title="Cảm biến thuộc thiết bị"
          description="Mỗi mã cảm biến là duy nhất trong phạm vi thiết bị."
          actions={
            canManageInfrastructure(role) ? (
              <SensorFormDialog deviceId={deviceId} projectId={projectId} />
            ) : undefined
          }
        />
        <div className="mt-5">
          {sensors.isLoading ? (
            <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
              {Array.from({ length: 3 }).map((_, index) => (
                <Skeleton key={index} className="h-60" />
              ))}
            </div>
          ) : sensors.isError ? (
            <EmptyState
              icon={RadioTower}
              title="Không thể tải cảm biến"
              description="Vui lòng thử lại."
            />
          ) : sensors.data?.length ? (
            <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
              {sensors.data.map((sensor) => (
                <SensorCard
                  key={sensor.id}
                  sensor={sensor}
                  projectId={projectId}
                  admin={role === "ADMIN"}
                  unit={
                    models.data?.find(
                      (item) => item.id === sensor.sensor_model_id,
                    )?.unit
                  }
                />
              ))}
            </div>
          ) : (
            <EmptyState
              icon={RadioTower}
              title="Chưa có cảm biến"
              description="Thêm cảm biến từ catalog cấu hình để bắt đầu nhận telemetry."
              action={
                canManageInfrastructure(role) ? (
                  <SensorFormDialog deviceId={deviceId} projectId={projectId} />
                ) : undefined
              }
            />
          )}
        </div>
      </section>
      </>}
    </div>
  );
}
