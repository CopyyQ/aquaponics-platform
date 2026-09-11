import { useEffect, useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { actuatorApi } from "@/entities/actuator/api/actuator-api";
import type { Actuator } from "@/entities/actuator/model/types";
import { useProtectedQueryScope } from "@/features/auth/model/use-protected-query-scope";
import { invalidateQueries } from "@/shared/api/query-invalidation";
import { Button } from "@/shared/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/shared/ui/dialog";
import { Input } from "@/shared/ui/input";
import { Label } from "@/shared/ui/label";
import { Textarea } from "@/shared/ui/textarea";

export function EditActuatorDialog({
  actuator,
  projectId,
  open,
  onOpenChange,
}: {
  actuator: Actuator;
  projectId: number;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  const [location, setLocation] = useState(actuator.location ?? "");
  const [notes, setNotes] = useState(actuator.notes ?? "");
  const client = useQueryClient();
  const { queryScope } = useProtectedQueryScope();
  useEffect(() => {
    if (!open) return;
    setLocation(actuator.location ?? "");
    setNotes(actuator.notes ?? "");
  }, [actuator.location, actuator.notes, open]);
  const mutation = useMutation({
    mutationFn: () =>
      actuatorApi.update(projectId, actuator.device_id, actuator.id, {
        location: location.trim() || null,
        notes: notes.trim() || null,
      }),
    onSuccess: async () => {
      await invalidateQueries.devices(
        client,
        queryScope,
        projectId,
        actuator.device_id,
      );
      onOpenChange(false);
      toast.success("Đã cập nhật cơ cấu chấp hành");
    },
    onError: () => toast.error("Không thể cập nhật Actuator"),
  });
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Sửa cơ cấu chấp hành</DialogTitle>
          <DialogDescription>
            Mã kỹ thuật và tên hiển thị được giữ ổn định để bảo toàn lịch sử
            điều khiển.
          </DialogDescription>
        </DialogHeader>
        <div className="flex flex-col gap-4">
          <div className="flex flex-col gap-2">
            <Label htmlFor={`edit-actuator-location-${actuator.id}`}>
              Vị trí lắp đặt
            </Label>
            <Input
              id={`edit-actuator-location-${actuator.id}`}
              value={location}
              onChange={(event) => setLocation(event.target.value)}
            />
          </div>
          <div className="flex flex-col gap-2">
            <Label htmlFor={`edit-actuator-notes-${actuator.id}`}>
              Ghi chú
            </Label>
            <Textarea
              id={`edit-actuator-notes-${actuator.id}`}
              value={notes}
              onChange={(event) => setNotes(event.target.value)}
            />
          </div>
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Hủy
          </Button>
          <Button
            disabled={mutation.isPending}
            onClick={() => mutation.mutate()}
          >
            {mutation.isPending ? "Đang lưu…" : "Lưu thay đổi"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
