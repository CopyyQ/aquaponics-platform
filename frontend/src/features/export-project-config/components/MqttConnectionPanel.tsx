import { useMutation, useQuery } from "@tanstack/react-query";
import axios from "axios";
import { Download, RadioTower } from "lucide-react";
import type { Device } from "@/entities/device/model/types";
import { deviceApi } from "@/entities/device/api/device-api";
import { downloadBlob } from "@/shared/lib/download";
import { Badge } from "@/shared/ui/badge";
import { Button } from "@/shared/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/shared/ui/card";
import { EmptyState } from "@/shared/ui/empty-state";
import { Skeleton } from "@/shared/ui/skeleton";
import { useProtectedQueryScope } from "@/features/auth/model/use-protected-query-scope";
import { queryKeys } from "@/shared/api/query-keys";
import { formatBackendError } from "@/shared/api/backend-error";
import { toast } from "sonner";

export function MqttConnectionPanel({ device }: { device: Device }) {
  const { active, queryScope } = useProtectedQueryScope();
  const query = useQuery({
    queryKey: queryKeys.devices.mqttConfig(
      queryScope,
      device.project_id,
      device.id,
    ),
    queryFn: () => deviceApi.mqttConfig(device.project_id, device.id),
    enabled: active && device.status !== "DISABLED",
    retry: false,
    staleTime: 0,
  });
  const download = useMutation({
    mutationFn: () =>
      deviceApi.downloadMqttConfig(device.project_id, device.id),
    onSuccess: ({ blob, filename }) => downloadBlob(blob, filename),
    onError: (error) =>
      toast.error(
        formatBackendError(error, "Không thể tải file cấu hình MQTT."),
      ),
  });
  const lifecycleCode = axios.isAxiosError(query.error)
    ? (query.error.response?.data as { detail?: { code?: string } } | undefined)
        ?.detail?.code
    : undefined;
  if (
    device.status === "DISABLED" ||
    lifecycleCode === "PROJECT_OWNER_INACTIVE" ||
    lifecycleCode === "PROJECT_INACTIVE"
  ) {
    return (
      <EmptyState
        icon={RadioTower}
        title="Cấu hình MQTT đang được ẩn"
        description="Tài khoản chủ dự án, dự án hoặc thiết bị không hoạt động."
      />
    );
  }
  if (query.isLoading) return <Skeleton className="h-64" />;
  if (!query.data)
    return (
      <p className="text-sm text-destructive">Không thể tải cấu hình MQTT.</p>
    );
  const config = query.data;
  return (
    <Card>
      <CardHeader>
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div className="flex flex-col gap-1">
            <CardTitle className="flex items-center gap-2">
              <RadioTower />
              Kết nối MQTT
            </CardTitle>
            <CardDescription>
              Thiết bị publish trực tiếp tới broker trong mạng LAN thử nghiệm.
            </CardDescription>
          </div>
          <Badge variant="outline">Không xác thực · Không TLS</Badge>
        </div>
      </CardHeader>
      <CardContent className="flex flex-col gap-5">
        <dl className="grid gap-4 rounded-lg bg-muted/40 p-4 sm:grid-cols-2 xl:grid-cols-3">
          {[
            ["Broker", config.mqtt.host],
            ["Port", config.mqtt.port],
            ["Mã thiết bị", config.device.code],
            ["Telemetry topic", config.mqtt.topics.telemetry],
            ["Status topic", config.mqtt.topics.status],
            ["Command topic", config.mqtt.topics.commands],
            ["ACK topic", config.mqtt.topics.command_ack],
          ].map(([label, value]) => (
            <div key={label}>
              <dt className="text-xs text-muted-foreground">{label}</dt>
              <dd className="mt-1 break-all font-mono text-sm font-semibold">
                {value}
              </dd>
            </div>
          ))}
        </dl>
        <div>
          <h3 className="text-sm font-medium">
            Cảm biến trong cấu hình mới nhất
          </h3>
          <div className="mt-2 grid gap-2 sm:grid-cols-2">
            {config.sensors.map((sensor) => (
              <div
                key={sensor.sensor_code}
                className="rounded-lg border p-3 text-sm"
              >
                <span className="font-mono font-semibold">
                  {sensor.sensor_code}
                </span>{" "}
                · {sensor.name} ({sensor.unit})
              </div>
            ))}
            {!config.sensors.length ? (
              <p className="text-sm text-muted-foreground">
                Thiết bị chưa có cảm biến.
              </p>
            ) : null}
          </div>
        </div>
        <div>
          <h3 className="text-sm font-medium">
            Cơ cấu chấp hành đang hoạt động
          </h3>
          <div className="mt-2 grid gap-2 sm:grid-cols-2">
            {config.actuators.map((actuator) => (
              <div
                key={actuator.actuator_code}
                className="rounded-lg border p-3 text-sm"
              >
                <span className="font-mono font-semibold">
                  {actuator.actuator_code}
                </span>
                <div className="mt-1">
                  {actuator.name} · Mặc định{" "}
                  {actuator.default_state ? "Bật" : "Tắt"}
                </div>
              </div>
            ))}
            {!config.actuators.length ? (
              <p className="text-sm text-muted-foreground">
                Thiết bị chưa có cơ cấu chấp hành đang hoạt động.
              </p>
            ) : null}
          </div>
        </div>
        <Button
          className="self-start"
          disabled={download.isPending}
          onClick={() => download.mutate()}
        >
          <Download data-icon="inline-start" />
          {download.isPending ? "Đang tải…" : "Tải file JSON cấu hình"}
        </Button>
        <p className="text-xs text-muted-foreground">
          Phiên bản {config.config_version} · Sinh lúc {config.generated_at}
        </p>
        <p className="text-xs text-muted-foreground">
          Chỉ dùng cấu hình này trong LAN development; không public cổng 1883 ra
          Internet.
        </p>
      </CardContent>
    </Card>
  );
}
