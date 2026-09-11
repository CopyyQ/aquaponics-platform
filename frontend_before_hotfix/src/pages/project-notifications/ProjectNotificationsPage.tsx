import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { BellRing, Bot, Pencil, Plus, Send, Trash2 } from "lucide-react";
import { useParams } from "react-router-dom";
import { toast } from "sonner";
import { projectNotificationApi } from "@/entities/project-notification/api/project-notification-api";
import type {
  NotificationRecipient,
  NotificationSettings,
} from "@/entities/project-notification/model/types";
import { useProtectedQueryScope } from "@/features/auth/model/use-protected-query-scope";
import { NotificationRiskPolicy } from "@/features/manage-project-notifications/NotificationRiskPolicy";
import { formatBackendError } from "@/shared/api/backend-error";
import { queryKeys } from "@/shared/api/query-keys";
import { Alert, AlertDescription, AlertTitle } from "@/shared/ui/alert";
import { Button } from "@/shared/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/shared/ui/card";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/shared/ui/dialog";
import { EmptyState } from "@/shared/ui/empty-state";
import { Input } from "@/shared/ui/input";
import { Label } from "@/shared/ui/label";
import { Skeleton } from "@/shared/ui/skeleton";
import { StatusBadge } from "@/shared/ui/status-badge";
import { Switch } from "@/shared/ui/switch";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/shared/ui/table";

const key = (
  scope: readonly (string | number | boolean | null | undefined)[],
  projectId: number,
) => [...queryKeys.projects.detail(scope, projectId), "notifications"] as const;

export function ProjectNotificationsPage() {
  const projectId = Number(useParams().projectId);
  const { active, queryScope } = useProtectedQueryScope();
  const client = useQueryClient();
  const [editing, setEditing] = useState<NotificationRecipient | null | "new">(
    null,
  );
  const settings = useQuery({
    queryKey: key(queryScope, projectId),
    queryFn: () => projectNotificationApi.get(projectId),
    enabled: active && Number.isFinite(projectId),
  });
  const updateSettings = useMutation({
    mutationFn: (
      payload: Omit<NotificationSettings, "telegram_bot_configured" | "recipients">,
    ) => projectNotificationApi.update(projectId, payload),
    retry: false,
    onSuccess: (data) => {
      client.setQueryData(key(queryScope, projectId), data);
      toast.success("Đã lưu cấu hình thông báo");
    },
    onError: (error) =>
      toast.error(formatBackendError(error, "Không thể lưu cấu hình")),
  });
  const refresh = async () =>
    client.invalidateQueries({ queryKey: key(queryScope, projectId) });
  const updateRecipient = useMutation({
    mutationFn: ({
      recipient,
      payload,
    }: {
      recipient: NotificationRecipient;
      payload: Partial<NotificationRecipient>;
    }) =>
      projectNotificationApi.updateRecipient(projectId, recipient.id, payload),
    onSuccess: async () => {
      await refresh();
      toast.success("Đã cập nhật người nhận");
    },
    onError: (error) =>
      toast.error(formatBackendError(error, "Không thể cập nhật người nhận")),
  });
  const removeRecipient = useMutation({
    mutationFn: (recipientId: number) =>
      projectNotificationApi.removeRecipient(projectId, recipientId),
    onSuccess: async () => {
      await refresh();
      toast.success("Đã xóa người nhận");
    },
    onError: (error) =>
      toast.error(formatBackendError(error, "Không thể xóa người nhận")),
  });
  const testRecipient = useMutation({
    mutationFn: (recipientId: number) =>
      projectNotificationApi.testRecipient(projectId, recipientId),
    onSuccess: () => toast.success("Đã gửi tin nhắn thử"),
    onError: (error) =>
      toast.error(formatBackendError(error, "Không thể gửi tin nhắn thử")),
  });

  if (settings.isLoading) return <Skeleton className="h-[32rem]" />;
  if (settings.isError || !settings.data)
    return (
      <EmptyState
        icon={BellRing}
        title="Không thể tải cấu hình thông báo"
        description="Vui lòng thử lại hoặc kiểm tra quyền quản lý dự án."
      />
    );
  const data = settings.data;
  const saveToggle = (patch: Partial<NotificationSettings>) =>
    updateSettings.mutate({
      telegram_enabled: data.telegram_enabled,
      notify_alert_opened: data.notify_alert_opened,
      notify_alert_escalated: data.notify_alert_escalated,
      notify_alert_reminder: data.notify_alert_reminder,
      reminder_interval_minutes: data.reminder_interval_minutes,
      notify_alert_recovered: data.notify_alert_recovered,
      notify_alert_resolved: data.notify_alert_resolved,
      minimum_business_risk_level: "LOW",
      risk_extreme_enabled: data.risk_extreme_enabled,
      risk_very_high_enabled: data.risk_very_high_enabled,
      risk_high_enabled: data.risk_high_enabled,
      risk_medium_enabled: data.risk_medium_enabled,
      risk_low_medium_enabled: data.risk_low_medium_enabled,
      risk_low_enabled: data.risk_low_enabled,
      risk_policies: data.risk_policies,
      ...patch,
    });
  return (
    <div className="space-y-5">
      <div>
        <h2 className="text-2xl font-bold">Cấu hình thông báo</h2>
        <p className="text-sm text-muted-foreground">
          Quản lý Telegram theo mức độ rủi ro, sự kiện và người nhận của dự án.
        </p>
      </div>
      {!data.telegram_bot_configured ? (
        <Alert variant="destructive">
          <Bot aria-hidden="true" />
          <AlertTitle>Bot Telegram chưa được cấu hình</AlertTitle>
          <AlertDescription>
            Quản trị máy chủ cần đặt TELEGRAM_BOT_TOKEN. Token không được lưu
            trong dự án hoặc gửi về trình duyệt.
          </AlertDescription>
        </Alert>
      ) : null}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between gap-3">
            <div>
              <CardTitle>Telegram</CardTitle>
              <CardDescription>
                {data.telegram_bot_configured
                  ? "Đã cấu hình bot trên máy chủ"
                  : "Chưa cấu hình bot trên máy chủ"}
              </CardDescription>
            </div>
            <StatusBadge
              value={
                data.telegram_bot_configured ? "CONFIGURED" : "NOT_CONFIGURED"
              }
            />
          </div>
        </CardHeader>
        <CardContent className="space-y-4">
          <SettingRow
            id="telegram-enabled"
            label="Bật thông báo Telegram"
            checked={data.telegram_enabled}
            disabled={updateSettings.isPending}
            onChange={(checked) => saveToggle({ telegram_enabled: checked })}
          />
          <NotificationRiskPolicy policies={data.risk_policies} disabled={updateSettings.isPending || !data.telegram_enabled} onChange={(risk_policies) => saveToggle({ risk_policies })} />
        </CardContent>
      </Card>
      <Card>
        <CardHeader>
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <CardTitle>Người nhận Telegram</CardTitle>
              <CardDescription>
                Chat ID được lưu dạng chuỗi và có thể là ID âm của
                nhóm/supergroup.
              </CardDescription>
            </div>
            <Button onClick={() => setEditing("new")}>
              <Plus aria-hidden="true" />
              Thêm người nhận
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          {data.recipients.length ? (
            <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Tên</TableHead>
                    <TableHead>Telegram Chat ID</TableHead>
                    <TableHead>Trạng thái</TableHead>
                    <TableHead className="text-right">Thao tác</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {data.recipients.map((recipient) => (
                    <TableRow key={recipient.id}>
                      <TableCell className="font-medium">
                        {recipient.name}
                      </TableCell>
                      <TableCell className="font-mono">
                        {recipient.telegram_chat_id}
                      </TableCell>
                      <TableCell>
                        <Switch
                          aria-label={`${recipient.enabled ? "Tắt" : "Bật"} người nhận ${recipient.name}`}
                          checked={recipient.enabled}
                          disabled={updateRecipient.isPending}
                          onCheckedChange={(enabled) =>
                            updateRecipient.mutate({
                              recipient,
                              payload: { enabled },
                            })
                          }
                        />
                      </TableCell>
                      <TableCell>
                        <div className="flex justify-end gap-2">
                          <Button
                            variant="outline"
                            size="sm"
                            disabled={
                              !data.telegram_bot_configured ||
                              !recipient.enabled ||
                              testRecipient.isPending
                            }
                            onClick={() => testRecipient.mutate(recipient.id)}
                          >
                            <Send aria-hidden="true" />
                            Gửi thử
                          </Button>
                          <Button
                            variant="outline"
                            size="icon"
                            aria-label={`Sửa ${recipient.name}`}
                            onClick={() => setEditing(recipient)}
                          >
                            <Pencil aria-hidden="true" />
                          </Button>
                          <Button
                            variant="destructive"
                            size="icon"
                            aria-label={`Xóa ${recipient.name}`}
                            disabled={removeRecipient.isPending}
                            onClick={() => {
                              if (
                                window.confirm(
                                  `Xóa người nhận ${recipient.name}?`,
                                )
                              )
                                removeRecipient.mutate(recipient.id);
                            }}
                          >
                            <Trash2 aria-hidden="true" />
                          </Button>
                        </div>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          ) : (
            <EmptyState
              icon={Send}
              title="Chưa có người nhận Telegram"
              description="Thêm Telegram Chat ID để nhận cảnh báo của dự án."
              action={
                <Button onClick={() => setEditing("new")}>
                  <Plus aria-hidden="true" />
                  Thêm người nhận
                </Button>
              }
            />
          )}
        </CardContent>
      </Card>
      <RecipientDialog
        key={editing === "new" ? "new" : (editing?.id ?? "closed")}
        projectId={projectId}
        recipient={editing}
        onOpenChange={(open) => {
          if (!open) setEditing(null);
        }}
        onSaved={refresh}
      />
    </div>
  );
}

function SettingRow({
  id,
  label,
  checked,
  disabled,
  onChange,
}: {
  id: string;
  label: string;
  checked: boolean;
  disabled: boolean;
  onChange: (checked: boolean) => void;
}) {
  return (
    <div className="flex items-center justify-between gap-4">
      <Label htmlFor={id}>{label}</Label>
      <Switch
        id={id}
        checked={checked}
        disabled={disabled}
        onCheckedChange={onChange}
      />
    </div>
  );
}

function RecipientDialog({
  projectId,
  recipient,
  onOpenChange,
  onSaved,
}: {
  projectId: number;
  recipient: NotificationRecipient | null | "new";
  onOpenChange: (open: boolean) => void;
  onSaved: () => Promise<unknown>;
}) {
  const [name, setName] = useState(
    recipient && recipient !== "new" ? recipient.name : "",
  );
  const [chatId, setChatId] = useState(
    recipient && recipient !== "new" ? recipient.telegram_chat_id : "",
  );
  const open = recipient !== null;
  const mutation = useMutation({
    mutationFn: () =>
      recipient === "new"
        ? projectNotificationApi.createRecipient(projectId, {
            name: name.trim(),
            telegram_chat_id: chatId.trim(),
          })
        : projectNotificationApi.updateRecipient(projectId, recipient!.id, {
            name: name.trim(),
            telegram_chat_id: chatId.trim(),
          }),
    onSuccess: async () => {
      await onSaved();
      setName("");
      setChatId("");
      onOpenChange(false);
      toast.success(
        recipient === "new" ? "Đã thêm người nhận" : "Đã sửa người nhận",
      );
    },
    onError: (error) =>
      toast.error(formatBackendError(error, "Không thể lưu người nhận")),
  });
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>
            {recipient === "new"
              ? "Thêm người nhận Telegram"
              : "Sửa người nhận Telegram"}
          </DialogTitle>
          <DialogDescription>
            Mọi cảnh báo của dự án sẽ được gửi tới người nhận này khi đang bật.
          </DialogDescription>
        </DialogHeader>
        <div className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="recipient-name">Tên</Label>
            <Input
              id="recipient-name"
              required
              value={name}
              onChange={(event) => setName(event.target.value)}
              aria-invalid={!name.trim()}
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="recipient-chat-id">Telegram Chat ID</Label>
            <Input
              id="recipient-chat-id"
              required
              value={chatId}
              onChange={(event) => setChatId(event.target.value)}
              aria-describedby="recipient-chat-help"
              aria-invalid={!chatId.trim()}
            />
            <p
              id="recipient-chat-help"
              className="text-xs text-muted-foreground"
            >
              Có thể là ID cá nhân hoặc ID âm của nhóm, ví dụ -1001234567890.
            </p>
          </div>
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Hủy
          </Button>
          <Button
            disabled={!name.trim() || !chatId.trim() || mutation.isPending}
            onClick={() => mutation.mutate()}
          >
            {mutation.isPending ? "Đang lưu…" : "Lưu"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
