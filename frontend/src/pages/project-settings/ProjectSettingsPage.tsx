import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ClipboardCopy, ExternalLink, Globe2 } from "lucide-react";
import { useParams } from "react-router-dom";
import { toast } from "sonner";
import { projectNotificationApi } from "@/entities/project-notification/api/project-notification-api";
import { getRemoteMonitoringRuntime } from "@/entities/project-notification/api/remote-monitoring-runtime";
import type { PublicSettings } from "@/entities/project-notification/model/types";
import { useProtectedQueryScope } from "@/features/auth/model/use-protected-query-scope";
import { formatBackendError } from "@/shared/api/backend-error";
import { Button } from "@/shared/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/shared/ui/card";
import { EmptyState } from "@/shared/ui/empty-state";
import { Label } from "@/shared/ui/label";
import { Skeleton } from "@/shared/ui/skeleton";
import { Switch } from "@/shared/ui/switch";

export function ProjectSettingsPage() {
  const projectId = Number(useParams().projectId);
  const { active, queryScope } = useProtectedQueryScope();
  const client = useQueryClient();
  const queryKey = [
    "project-public-settings",
    ...queryScope,
    projectId,
  ] as const;
  const settings = useQuery({
    queryKey,
    queryFn: () => projectNotificationApi.getPublicSettings(projectId),
    enabled: active && Number.isFinite(projectId),
  });
  if (settings.isLoading) return <Skeleton className="h-80" />;
  if (!settings.data)
    return (
      <EmptyState
        icon={Globe2}
        title="Không thể tải cài đặt công khai"
        description="Vui lòng kiểm tra quyền quản lý dự án."
      />
    );
  return (
    <PublicSettingsForm
      key={`${settings.data.enabled}`}
      projectId={projectId}
      initial={settings.data}
      onSaved={(value) => client.setQueryData(queryKey, value)}
    />
  );
}

function PublicSettingsForm({
  projectId,
  initial,
  onSaved,
}: {
  projectId: number;
  initial: PublicSettings;
  onSaved: (value: typeof initial) => void;
}) {
  const [enabled, setEnabled] = useState(initial.enabled);
  const runtime = useQuery({
    queryKey: ["remote-monitoring-runtime"],
    queryFn: getRemoteMonitoringRuntime,
    retry: false,
    refetchInterval: 5_000,
  });
  const tunnelUrl = runtime.data?.status === "running" ? runtime.data.url : "";
  const tunnelCommand = "cloudflared tunnel --url http://127.0.0.1:8088";
  const mutation = useMutation({
    mutationFn: () =>
      projectNotificationApi.updatePublicSettings(projectId, {
        enabled,
      }),
    onSuccess: (value) => {
      onSaved(value);
      toast.success("Đã lưu cài đặt theo dõi công khai");
    },
    onError: (error) =>
      toast.error(formatBackendError(error, "Không thể lưu cài đặt công khai")),
  });
  return (
    <div className="space-y-5">
      <div>
        <h2 className="text-2xl font-bold">Cài đặt dự án</h2>
        <p className="text-sm text-muted-foreground">
          Quản lý màn hình giám sát chỉ đọc được chia sẻ qua Cloudflare Quick Tunnel.
        </p>
      </div>
      <Card>
        <CardHeader>
          <CardTitle>Theo dõi từ xa</CardTitle>
          <CardDescription>
            Cho phép xem màn hình Giám sát của dự án từ Internet ở chế độ chỉ đọc.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-5">
          <div className="flex items-center justify-between gap-4">
            <Label htmlFor="public-enabled">Bật theo dõi từ xa</Label>
            <Switch
              id="public-enabled"
              checked={enabled}
              onCheckedChange={setEnabled}
              disabled={!initial.remote_monitoring_available}
              aria-describedby="remote-monitoring-scope"
            />
          </div>
          <div id="remote-monitoring-scope" className="grid gap-3 rounded-md border p-4 text-sm sm:grid-cols-2">
            <div><p className="font-medium">Phạm vi chia sẻ</p><p className="text-muted-foreground">Giám sát dự án</p></div>
            <div><p className="font-medium">Quyền truy cập</p><p className="text-muted-foreground">Chỉ đọc</p></div>
            <div><p className="font-medium">Có thể xem</p><p className="text-muted-foreground">Thiết bị, cảm biến, năng lượng, biểu đồ và cảnh báo</p></div>
            <div><p className="font-medium">Không thể</p><p className="text-muted-foreground">Điều khiển, cấu hình, MQTT, thành viên hoặc Telegram</p></div>
          </div>
          {initial.enabled ? <div className="space-y-3 rounded-md border p-4">
            <div aria-live="polite">
              <p className="font-medium">Cloudflare Quick Tunnel</p>
              <p className="text-sm text-muted-foreground">
                {tunnelUrl ? `Đang hoạt động: ${tunnelUrl}` : "Tunnel chưa chạy. Khởi động trên máy chủ bằng lệnh dưới đây."}
              </p>
            </div>
            <code className="block overflow-x-auto rounded bg-muted px-3 py-2 text-xs">{tunnelCommand}</code>
            <div className="flex flex-wrap gap-2">
              <Button type="button" variant="outline" onClick={() => {
                void navigator.clipboard.writeText(tunnelCommand).then(
                  () => toast.success("Đã sao chép lệnh Cloudflare Quick Tunnel"),
                  () => toast.error("Không thể sao chép lệnh"),
                )
              }}>
                <ClipboardCopy aria-hidden="true" />Sao chép lệnh chạy tunnel
              </Button>
              {tunnelUrl ? <Button asChild variant="outline">
                <a href={tunnelUrl} target="_blank" rel="noreferrer">
                  Mở giám sát từ xa
                  <ExternalLink aria-hidden="true" />
                </a>
              </Button> : <Button type="button" variant="outline" disabled aria-describedby="tunnel-unavailable">
                Mở giám sát từ xa
                <ExternalLink aria-hidden="true" />
              </Button>}
            </div>
            {!tunnelUrl ? <p id="tunnel-unavailable" className="text-xs text-muted-foreground">Nút mở sẽ khả dụng tự động khi script nhận được URL `trycloudflare.com`.</p> : null}
          </div> : null}
        </CardContent>
        <CardFooter>
          <Button
            disabled={!initial.remote_monitoring_available || mutation.isPending}
            onClick={() => mutation.mutate()}
          >
            {mutation.isPending ? "Đang lưu…" : "Lưu cài đặt"}
          </Button>
        </CardFooter>
      </Card>
    </div>
  );
}
