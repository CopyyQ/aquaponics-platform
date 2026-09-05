import { AlertTriangle } from "lucide-react";
import { useProjectContext } from "@/entities/project/model/project-context";
import { formatDateTime } from "@/shared/lib/date";
import { Card, CardContent, CardHeader, CardTitle } from "@/shared/ui/card";
import { EmptyState } from "@/shared/ui/empty-state";
import { StatusBadge } from "@/shared/ui/status-badge";

export function ProjectAlertsPage() {
  const project = useProjectContext();
  return (
    <div className="space-y-4">
      <div>
        <h2 className="text-2xl font-bold">Cảnh báo</h2>
        <p className="text-sm text-muted-foreground">
          Các cảnh báo gần đây thuộc riêng dự án này.
        </p>
      </div>
      {project.recent_alerts.length ? (
        <div className="grid gap-3">
          {project.recent_alerts.map((alert) => (
            <Card key={alert.id}>
              <CardHeader className="flex-row items-center justify-between gap-3">
                <CardTitle className="text-base">
                  {alert.sensor_name} · {alert.device_name}
                </CardTitle>
                <StatusBadge value={alert.severity} />
              </CardHeader>
              <CardContent>
                <p>{alert.message}</p>
                {alert.status !== "RESOLVED" ? <p className="mt-2 text-sm font-medium">
                  {alert.condition_active ? "Điều kiện hiện tại: Vẫn bất thường" : "Đã trở về ngưỡng bình thường · Chờ xác nhận khắc phục"}
                </p> : null}
                <p className="mt-2 text-xs text-muted-foreground">
                  {alert.status === "RESOLVED" ? (alert.resolved_by_user_id !== null ? "Đã khắc phục" : "Kết thúc theo dữ liệu cũ") : alert.status} · {formatDateTime(alert.started_at)}
                </p>
              </CardContent>
            </Card>
          ))}
        </div>
      ) : (
        <EmptyState
          icon={AlertTriangle}
          title="Không có cảnh báo gần đây"
          description="Dự án hiện không có cảnh báo trong read model tổng quan."
        />
      )}
    </div>
  );
}
