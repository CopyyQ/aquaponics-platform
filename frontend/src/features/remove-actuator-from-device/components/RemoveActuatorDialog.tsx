import { useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";

import { actuatorApi } from "@/entities/actuator/api/actuator-api";
import type { Actuator } from "@/entities/actuator/model/types";
import { useProtectedQueryScope } from "@/features/auth/model/use-protected-query-scope";
import { formatBackendError } from "@/shared/api/backend-error";
import { invalidateQueries } from "@/shared/api/query-invalidation";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/shared/ui/alert-dialog";

export function RemoveActuatorDialog({
  actuator,
  projectId,
  deviceName,
  open,
  onOpenChange,
}: {
  actuator: Actuator;
  projectId: number;
  deviceName: string;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  const client = useQueryClient();
  const { queryScope } = useProtectedQueryScope();
  const mutation = useMutation({
    mutationFn: () =>
      actuatorApi.remove(projectId, actuator.device_id, actuator.id),
    onSuccess: async () => {
      await invalidateQueries.devices(
        client,
        queryScope,
        projectId,
        actuator.device_id,
      );
      onOpenChange(false);
      toast.success("Đã xóa cơ cấu chấp hành khỏi thiết bị");
    },
    onError: (error) =>
      toast.error(
        formatBackendError(
          error,
          "Không thể xóa cơ cấu chấp hành khỏi thiết bị.",
        ),
      ),
  });

  const currentState =
    actuator.reported_state === null
      ? "Chưa xác định"
      : actuator.reported_state
        ? "Đang bật"
        : "Đang tắt";

  return (
    <AlertDialog open={open} onOpenChange={onOpenChange}>
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle>
            Xóa cơ cấu chấp hành khỏi thiết bị?
          </AlertDialogTitle>
          <AlertDialogDescription>
            Cơ cấu chấp hành sẽ không còn xuất hiện trong danh sách vận hành và
            không thể nhận lệnh điều khiển. Lịch sử điều khiển vẫn được giữ lại.
          </AlertDialogDescription>
        </AlertDialogHeader>
        <dl className="grid gap-2 rounded-lg border p-3 text-sm">
          <div className="flex justify-between gap-4">
            <dt className="text-muted-foreground">Cơ cấu</dt>
            <dd className="text-right font-medium">{actuator.name}</dd>
          </div>
          <div className="flex justify-between gap-4">
            <dt className="text-muted-foreground">Thiết bị</dt>
            <dd className="text-right font-medium">{deviceName}</dd>
          </div>
          <div className="flex justify-between gap-4">
            <dt className="text-muted-foreground">Trạng thái hiện tại</dt>
            <dd className="text-right font-medium">{currentState}</dd>
          </div>
        </dl>
        <AlertDialogFooter>
          <AlertDialogCancel disabled={mutation.isPending}>
            Hủy
          </AlertDialogCancel>
          <AlertDialogAction
            variant="destructive"
            disabled={mutation.isPending}
            onClick={() => mutation.mutate()}
          >
            {mutation.isPending ? "Đang xóa…" : "Xóa khỏi thiết bị"}
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  );
}
