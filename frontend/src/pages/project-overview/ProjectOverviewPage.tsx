import {
  AlertTriangle,
  CircleAlert,
  Cpu,
  RadioTower,
  Siren,
  Wifi,
} from "lucide-react";
import { Link } from "react-router-dom";
import { useProjectContext } from "@/entities/project/model/project-context";
import {
  electricalQualityLabel,
} from "@/entities/actuator/lib/actuator-electrical";
import { ActuatorStatusCard } from "@/pages/project-overview/ActuatorStatusCard";
import { formatDateTime, formatRelative } from "@/shared/lib/date";
import { Badge } from "@/shared/ui/badge";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/shared/ui/card";

const healthTone = (status: string) =>
  status === "CRITICAL"
    ? "destructive"
    : status === "WARNING"
      ? "warning"
      : "success";
const severityLabel = (severity: string) =>
  severity === "CRITICAL"
    ? "Nghiêm trọng"
    : severity === "HIGH"
      ? "Cao"
      : severity === "WARNING"
        ? "Cảnh báo"
        : "Thông tin";
const qualityLabel = electricalQualityLabel;

export function ProjectOverviewPage() {
  const item = useProjectContext();
  const health = item.health;
  const actuatorInventory =
    (item as typeof item & { actuator_inventory?: Record<string, number> })
      .actuator_inventory ?? {};
  const actuators = item.actuators ?? [];
  const energyDevices = (
    item as typeof item & {
      energy_devices_summary?: {
        count: number;
        items: Array<{ id: number; name: string; status: string }>;
      };
    }
  ).energy_devices_summary;
  const metrics = [
    [
      "Thiết bị đang kết nối",
      `${item.inventory.devices_online}/${item.inventory.devices_enabled}`,
      Wifi,
      "success",
    ],
    [
      "Thiết bị mất kết nối",
      item.inventory.devices_offline,
      Cpu,
      item.inventory.devices_offline ? "danger" : "neutral",
    ],
    [
      "Cảm biến có dữ liệu hợp lệ",
      `${item.inventory.sensors_reporting}/${item.inventory.sensors_enabled}`,
      RadioTower,
      "success",
    ],
    [
      "Cơ cấu đang phản hồi",
      `${actuatorInventory.responding ?? 0}/${actuatorInventory.total ?? 0}`,
      Siren,
      "success",
    ],
    [
      "Cơ cấu lỗi hoặc không đồng bộ",
      actuatorInventory.failed ?? actuatorInventory.out_of_sync ?? 0,
      AlertTriangle,
      (actuatorInventory.failed ?? actuatorInventory.out_of_sync ?? 0)
        ? "danger"
        : "neutral",
    ],
    [
      "Vấn đề cần xử lý",
      item.attention.length,
      CircleAlert,
      item.attention.length ? "warning" : "success",
    ],
  ] as const;

  return (
    <div className="flex flex-col gap-6">
      <Card className="overflow-hidden border-primary/20">
        <CardContent className="grid gap-6 p-6 lg:grid-cols-[1.5fr_1fr]">
          <div>
            <div className="flex flex-wrap items-center gap-2">
              <Badge>{item.project.code}</Badge>
              <Badge variant={healthTone(health.status)}>{health.label}</Badge>
              <Badge variant="outline">
                {item.project.status === "ACTIVE"
                  ? "Đang hoạt động"
                  : "Không hoạt động"}
              </Badge>
            </div>
            <h1 className="mt-3 text-3xl font-semibold tracking-tight">
              {item.project.name}
            </h1>
            <p className="mt-2 max-w-2xl text-muted-foreground">
              {item.project.description || "Chưa có mô tả cho dự án."}
            </p>
            <p className="mt-4 text-sm text-muted-foreground">
              {item.project.location || "Chưa có địa điểm"} · Telemetry nhận
              cuối {formatRelative(item.freshness.last_received_at)}
            </p>
            <div className="mt-5 flex flex-wrap gap-2">
              <Link
                to="../monitoring"
                className="rounded-md bg-primary px-3 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90"
              >
                Giám sát dự án
              </Link>
              <Link
                to="../devices"
                className="rounded-md border px-3 py-2 text-sm font-medium hover:bg-muted"
              >
                Quản lý thiết bị
              </Link>
              <Link
                to="../members"
                className="rounded-md border px-3 py-2 text-sm font-medium hover:bg-muted"
              >
                Quản lý thành viên
              </Link>
            </div>
          </div>
          <div className="rounded-xl bg-muted/30 p-5">
            <p className="text-sm text-muted-foreground">Kết luận vận hành</p>
            <h2 className="mt-2 text-2xl font-semibold">{health.label}</h2>
            <p className="mt-2 text-sm text-muted-foreground">
              {health.reasons.length
                ? `${item.attention.length} vấn đề cần xử lý.`
                : "Không có vấn đề cần xử lý."}
            </p>
            <ul className="mt-3 flex flex-col gap-2 text-sm text-muted-foreground">
              {health.reasons.slice(0, 3).map((reason) => (
                <li key={reason.code}>• {reason.message}</li>
              ))}
            </ul>
          </div>
        </CardContent>
      </Card>
      <section className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
        {metrics.map(([label, value, Icon, tone]) => (
          <Card key={label}>
            <CardContent className="flex items-start justify-between p-5">
              <div>
                <p className="text-sm text-muted-foreground">{label}</p>
                <strong className="mt-1 block text-2xl tabular-nums">
                  {value}
                </strong>
              </div>
              <Icon
                className={
                  tone === "danger"
                    ? "text-destructive"
                    : tone === "warning"
                      ? "text-amber-600"
                      : "text-primary"
                }
                aria-hidden="true"
              />
            </CardContent>
          </Card>
        ))}
      </section>
      <section className="grid gap-5 xl:grid-cols-[minmax(0,1.1fr)_minmax(320px,0.9fr)]">
        <Card>
          <CardHeader>
            <CardTitle>Ưu tiên xử lý</CardTitle>
            <CardDescription>
              Vấn đề đã được sắp xếp theo mức độ nguy cơ.
            </CardDescription>
          </CardHeader>
          <CardContent className="flex flex-col gap-3">
            {item.attention.slice(0, 5).map((attention) => (
              <div key={attention.id} className="rounded-lg border p-4">
                <div className="flex flex-wrap items-center gap-2">
                  <Badge
                    variant={
                      attention.severity === "CRITICAL"
                        ? "destructive"
                        : attention.severity === "HIGH"
                          ? "destructive"
                          : "warning"
                    }
                  >
                    {severityLabel(attention.severity)}
                  </Badge>
                  <span className="font-medium">{attention.title}</span>
                </div>
                <p className="mt-2 text-sm text-muted-foreground">
                  {attention.description}
                </p>
                <div className="mt-2 flex flex-wrap items-center justify-between gap-2 text-xs text-muted-foreground">
                  <span>
                    {attention.last_seen_at
                      ? formatDateTime(attention.last_seen_at)
                      : "Chưa có thời điểm"}
                  </span>
                  {attention.device_id ? (
                    <Link
                      className="font-medium text-primary hover:underline"
                      to={`../devices/${attention.device_id}`}
                    >
                      Xem đối tượng
                    </Link>
                  ) : null}
                </div>
              </div>
            ))}
            {!item.attention.length ? (
              <p className="rounded-lg border border-dashed p-5 text-center text-sm text-muted-foreground">
                Không có vấn đề cần xử lý.
              </p>
            ) : null}
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle>Độ phủ và chất lượng dữ liệu</CardTitle>
            <CardDescription>
              Dữ liệu cũ, thiếu và ngoài miền được tách riêng.
            </CardDescription>
          </CardHeader>
          <CardContent className="flex flex-col gap-4">
            <div>
              <p className="text-3xl font-semibold">
                {item.freshness.reporting_sensors}/
                {item.freshness.expected_sensors}
              </p>
              <p className="text-sm text-muted-foreground">
                cảm biến đang gửi dữ liệu hợp lệ
              </p>
            </div>
            <div className="h-2 overflow-hidden rounded-full bg-muted">
              <div
                className="h-full rounded-full bg-primary"
                style={{
                  width: `${Math.round(item.freshness.coverage_ratio * 100)}%`,
                }}
              />
            </div>
            <div className="grid grid-cols-2 gap-3 text-sm">
              <Info
                label="Dữ liệu cũ"
                value={String(item.inventory.sensors_stale)}
              />
              <Info
                label="Mất dữ liệu"
                value={String(item.inventory.sensors_offline)}
              />
              <Info
                label="Cảnh báo mở"
                value={String(item.alerts.open_total)}
              />
              <Info
                label="Telemetry cuối"
                value={formatDateTime(item.freshness.last_received_at)}
              />
            </div>
          </CardContent>
        </Card>
      </section>
      {energyDevices?.count ? (
        <Card>
          <CardHeader>
            <CardTitle>Thiết bị năng lượng</CardTitle>
            <CardDescription>
              Chỉ là tóm tắt; biểu đồ công suất nằm tại trang thiết bị.
            </CardDescription>
          </CardHeader>
          <CardContent className="flex flex-col gap-3">
            {energyDevices.items.map((device) => (
              <div
                key={device.id}
                className="flex flex-wrap items-center justify-between gap-3 rounded-lg border p-4"
              >
                <div>
                  <p className="font-medium">{device.name}</p>
                  <p className="text-sm text-muted-foreground">
                    {device.status === "ONLINE"
                      ? "Đang kết nối"
                      : device.status === "OFFLINE"
                        ? "Mất kết nối"
                        : "Đang chờ kết nối"}
                  </p>
                </div>
                <Link
                  className="text-sm font-medium text-primary hover:underline"
                  to={`../devices/${device.id}`}
                >
                  Xem thiết bị năng lượng
                </Link>
              </div>
            ))}
          </CardContent>
        </Card>
      ) : null}
      <Card>
        <CardHeader>
          <CardTitle>Trạng thái cơ cấu chấp hành</CardTitle>
          <CardDescription>
            Kết nối, lệnh, trạng thái báo về và phản hồi điện được hiển thị độc
            lập.
          </CardDescription>
        </CardHeader>
        <CardContent>
          {actuators.length ? (
            <div className="grid gap-4 xl:grid-cols-2">
              {actuators.slice(0, 8).map((actuator) => (
                <ActuatorStatusCard key={actuator.id} actuator={actuator} />
              ))}
            </div>
          ) : (
            <p className="rounded-lg border border-dashed p-5 text-center text-sm text-muted-foreground">
              Dự án chưa có cơ cấu chấp hành.
            </p>
          )}
        </CardContent>
      </Card>
      <Card>
        <CardHeader>
          <CardTitle>Tình trạng cảm biến và dữ liệu đo</CardTitle>
          <CardDescription>
            Giá trị ngoài miền kỹ thuật không được tính như dữ liệu hợp lệ.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
            {item.measurement_groups.slice(0, 8).map((group) => (
              <div key={group.model_code} className="rounded-lg border p-4">
                <div className="flex items-start justify-between gap-2">
                  <div>
                    <p className="font-medium">{group.name}</p>
                    <p className="text-xs text-muted-foreground">
                      {group.model_code}
                    </p>
                  </div>
                  <Badge
                    variant={
                      group.quality === "OUT_OF_RANGE"
                        ? "destructive"
                        : group.quality === "VALID"
                          ? "success"
                          : "warning"
                    }
                  >
                    {qualityLabel(group.quality)}
                  </Badge>
                </div>
                <p className="mt-4 text-2xl font-semibold tabular-nums">
                  {group.quality === "OUT_OF_RANGE"
                    ? String(group.latest_value ?? "—")
                    : group.latest_value === null
                      ? "—"
                      : `${group.latest_value} ${group.unit}`}
                </p>
                <p className="mt-1 text-xs text-muted-foreground">
                  {group.quality_reason ||
                    `${group.reporting_sensors}/${group.expected_sensors} cảm biến · ${formatDateTime(group.latest_at)}`}
                </p>
              </div>
            ))}
          </div>
          {!item.measurement_groups.length ? (
            <p className="p-6 text-center text-sm text-muted-foreground">
              Dự án chưa có cảm biến.
            </p>
          ) : null}
        </CardContent>
      </Card>
      <Card>
        <CardHeader>
          <CardTitle>Thông tin dự án</CardTitle>
          <CardDescription>
            Thông tin quản trị đặt sau tình trạng vận hành.
          </CardDescription>
        </CardHeader>
        <CardContent className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <Info label="Chủ sở hữu" value={item.owner?.full_name ?? "—"} />
          <Info
            label="Thành viên"
            value={String(item.inventory.members_total)}
          />
          <Info
            label="Telemetry nhận cuối"
            value={formatDateTime(item.freshness.last_received_at)}
          />
          <Info
            label="Cập nhật"
            value={formatDateTime(item.project.updated_at)}
          />
        </CardContent>
      </Card>
    </div>
  );
}
function Info({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <p className="text-xs text-muted-foreground">{label}</p>
      <p className="mt-1 font-medium">{value}</p>
    </div>
  );
}
