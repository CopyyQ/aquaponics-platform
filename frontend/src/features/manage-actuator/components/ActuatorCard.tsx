import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { MoreHorizontal, Pencil, Power, PowerOff, Trash2 } from "lucide-react";
import { toast } from "sonner";
import { actuatorApi } from "@/entities/actuator/api/actuator-api";
import type { Actuator } from "@/entities/actuator/model/types";
import { useProtectedQueryScope } from "@/features/auth/model/use-protected-query-scope";
import { invalidateQueries } from "@/shared/api/query-invalidation";
import { formatDateTime } from "@/shared/lib/date";
import { Badge } from "@/shared/ui/badge";
import { Button } from "@/shared/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/shared/ui/card";
import { EditActuatorDialog } from "@/features/edit-actuator/components/EditActuatorDialog";
import { RemoveActuatorDialog } from "@/features/remove-actuator-from-device/components/RemoveActuatorDialog";
import { ActuatorFeedbackDialog } from "@/features/manage-actuator/components/ActuatorFeedbackDialog";
import { ActuatorElectricalPanel } from "@/features/manage-actuator/components/ActuatorElectricalPanel";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuGroup,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/shared/ui/dropdown-menu";

export function ActuatorCard({
  actuator,
  projectId,
  deviceStatus,
  deviceName,
}: {
  actuator: Actuator;
  projectId: number;
  deviceStatus: string;
  deviceName: string;
}) {
  const [editOpen, setEditOpen] = useState(false);
  const [removeOpen, setRemoveOpen] = useState(false);
  const [feedbackOpen, setFeedbackOpen] = useState(false);
  const client = useQueryClient();
  const { queryScope } = useProtectedQueryScope();
  const mutation = useMutation({
    mutationFn: (desiredState: boolean) =>
      actuatorApi.command(
        projectId,
        actuator.device_id,
        actuator.id,
        desiredState,
      ),
    onSuccess: async (command) => {
      await invalidateQueries.devices(
        client,
        queryScope,
        projectId,
        actuator.device_id,
      );
      toast.success(
        command.desired_state ? "Đã gửi lệnh bật" : "Đã gửi lệnh tắt",
        { description: "Đang chờ thiết bị xác nhận." },
      );
    },
    onError: () => toast.error("Không thể gửi lệnh điều khiển"),
  });
  const lifecycle = useMutation({
    mutationFn: () =>
      actuator.is_enabled
        ? actuatorApi.disable(
            projectId,
            actuator.device_id,
            actuator.id,
            "Tắt từ trang quản trị",
          )
        : actuatorApi.activate(projectId, actuator.device_id, actuator.id),
    onSuccess: async () => {
      await invalidateQueries.devices(
        client,
        queryScope,
        projectId,
        actuator.device_id,
      );
      toast.success(
        actuator.is_enabled
          ? "Đã vô hiệu hóa Actuator"
          : "Đã kích hoạt Actuator",
      );
    },
    onError: () => toast.error("Không thể cập nhật trạng thái quản lý"),
  });
  const pending =
    actuator.last_command_at !== null &&
    actuator.desired_state !== actuator.reported_state;
  const state = !actuator.is_enabled
    ? "Không khả dụng"
    : pending
      ? "Đang xử lý"
      : actuator.reported_state === true
        ? "Đang bật"
        : actuator.reported_state === false
          ? "Đang tắt"
          : "Chưa xác định";
  const controlsDisabled =
    deviceStatus !== "ONLINE" ||
    pending ||
    mutation.isPending ||
    !actuator.is_enabled;
  return (
    <>
      <Card>
        <CardHeader className="flex-row items-start justify-between gap-3">
          <div className="min-w-0">
            <CardTitle className="text-base">{actuator.name}</CardTitle>
            <p className="mt-1 break-all font-mono text-xs text-muted-foreground">
              {actuator.code}
            </p>
          </div>
          <div className="flex items-center gap-2">
            <Badge variant={actuator.is_enabled ? "secondary" : "outline"}>
              {actuator.is_enabled ? "Đang sử dụng" : "Đã vô hiệu hóa"}
            </Badge>
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button
                  variant="ghost"
                  size="icon-sm"
                  aria-label={`Mở thao tác cho ${actuator.name}`}
                >
                  <MoreHorizontal />
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end">
                <DropdownMenuGroup>
                  <DropdownMenuItem onSelect={() => setEditOpen(true)}>
                    <Pencil />
                    Sửa vị trí và ghi chú
                  </DropdownMenuItem>
                  <DropdownMenuItem onSelect={() => setFeedbackOpen(true)}>
                    Sửa giám sát điện
                  </DropdownMenuItem>
                  <DropdownMenuItem
                    disabled={controlsDisabled}
                    onSelect={() => mutation.mutate(true)}
                  >
                    <Power />
                    Bật
                  </DropdownMenuItem>
                  <DropdownMenuItem
                    disabled={controlsDisabled}
                    onSelect={() => mutation.mutate(false)}
                  >
                    <PowerOff />
                    Tắt
                  </DropdownMenuItem>
                  <DropdownMenuItem
                    disabled={lifecycle.isPending}
                    onSelect={() => lifecycle.mutate()}
                  >
                    {actuator.is_enabled ? "Vô hiệu hóa" : "Kích hoạt lại"}
                  </DropdownMenuItem>
                </DropdownMenuGroup>
                <DropdownMenuSeparator />
                <DropdownMenuGroup>
                  <DropdownMenuItem
                    className="text-destructive focus:text-destructive"
                    disabled={pending}
                    onSelect={() => setRemoveOpen(true)}
                  >
                    <Trash2 />
                    Xóa khỏi thiết bị
                  </DropdownMenuItem>
                </DropdownMenuGroup>
              </DropdownMenuContent>
            </DropdownMenu>
          </div>
        </CardHeader>
        <CardContent className="flex flex-col gap-4">
          <div className="flex items-center justify-between gap-3">
            <div className="flex items-center gap-2">
              {state === "Đang bật" ? <Power /> : <PowerOff />}
              <span className="font-medium">{state}</span>
            </div>
            <span className="text-sm text-muted-foreground">
              {formatDateTime(actuator.last_reported_at)}
            </span>
          </div>
          {pending ? (
            <p className="text-xs text-muted-foreground">
              Yêu cầu: {actuator.desired_state ? "Bật" : "Tắt"} · Thực tế:{" "}
              {actuator.reported_state === null
                ? "Chưa xác định"
                : actuator.reported_state
                  ? "Đang bật"
                  : "Đang tắt"}
            </p>
          ) : null}
          <div className="text-sm text-muted-foreground">
            {actuator.location || "Chưa đặt vị trí lắp đặt"}
          </div>
          <ActuatorElectricalPanel electrical={actuator.electrical_feedbacks} />
          <div className="flex flex-wrap gap-2 border-t pt-4">
            <Button type="button" variant="outline" size="sm" onClick={() => setFeedbackOpen(true)}>
              <Pencil aria-hidden="true" />Sửa
            </Button>
            <Button type="button" variant="outline" size="sm" disabled={lifecycle.isPending} onClick={() => lifecycle.mutate()}>
              {actuator.is_enabled ? "Vô hiệu hóa" : "Kích hoạt lại"}
            </Button>
          </div>
        </CardContent>
      </Card>
      <EditActuatorDialog
        actuator={actuator}
        projectId={projectId}
        open={editOpen}
        onOpenChange={setEditOpen}
      />
      <RemoveActuatorDialog
        actuator={actuator}
        projectId={projectId}
        deviceName={deviceName}
        open={removeOpen}
        onOpenChange={setRemoveOpen}
      />
      <ActuatorFeedbackDialog actuator={actuator} projectId={projectId} open={feedbackOpen} onOpenChange={setFeedbackOpen} />
    </>
  );
}
