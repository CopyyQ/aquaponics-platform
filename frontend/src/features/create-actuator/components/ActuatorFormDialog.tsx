import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Plus } from "lucide-react";
import { toast } from "sonner";
import { actuatorApi } from "@/entities/actuator/api/actuator-api";
import { actuatorModelApi } from "@/entities/actuator-model/api/actuator-model-api";
import { useProtectedQueryScope } from "@/features/auth/model/use-protected-query-scope";
import { invalidateQueries } from "@/shared/api/query-invalidation";
import { queryKeys } from "@/shared/api/query-keys";
import { Button } from "@/shared/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/shared/ui/dialog";
import { Label } from "@/shared/ui/label";
import { Textarea } from "@/shared/ui/textarea";
import { Input } from "@/shared/ui/input";
import {
  Select,
  SelectContent,
  SelectGroup,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/shared/ui/select";

export function ActuatorFormDialog({
  projectId,
  deviceId,
}: {
  projectId: number;
  deviceId: number;
}) {
  const [open, setOpen] = useState(false);
  const [location, setLocation] = useState("");
  const [notes, setNotes] = useState("");
  const [modelId, setModelId] = useState("");
  const client = useQueryClient();
  const { queryScope } = useProtectedQueryScope();
  const models = useQuery({
    queryKey: queryKeys.actuatorModels.list(queryScope),
    queryFn: actuatorModelApi.list,
    enabled: open,
  });
  const mutation = useMutation({
    mutationFn: () =>
      actuatorApi.create(projectId, deviceId, {
        actuator_model_id: Number(modelId),
        location: location.trim() || null,
        notes: notes.trim() || null,
      }),
    onSuccess: async (actuator) => {
      await invalidateQueries.devices(client, queryScope, projectId, deviceId);
      setOpen(false);
      setLocation("");
      setNotes("");
      setModelId("");
      toast.success(`Đã thêm ${actuator.name}`);
    },
    onError: () => toast.error("Không thể thêm cơ cấu chấp hành"),
  });
  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button>
          <Plus data-icon="inline-start" />
          Thêm cơ cấu chấp hành
        </Button>
      </DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Thêm cơ cấu chấp hành</DialogTitle>
          <DialogDescription>
            Backend sẽ tự tạo định danh ổn định theo dự án, thiết bị và mẫu đã
            chọn.
          </DialogDescription>
        </DialogHeader>
        <div className="flex flex-col gap-4">
          <div className="flex flex-col gap-2">
            <Label htmlFor={`actuator-model-${deviceId}`}>
              Mẫu cơ cấu chấp hành
            </Label>
            <Select value={modelId} onValueChange={setModelId}>
              <SelectTrigger id={`actuator-model-${deviceId}`}>
                <SelectValue placeholder="Chọn mẫu cơ cấu chấp hành" />
              </SelectTrigger>
              <SelectContent>
                <SelectGroup>
                  {models.data
                    ?.filter((model) => model.is_active)
                    .map((model) => (
                      <SelectItem key={model.id} value={String(model.id)}>
                        {model.name} · {model.code}
                      </SelectItem>
                    ))}
                </SelectGroup>
              </SelectContent>
            </Select>
          </div>
          <div className="flex flex-col gap-2">
            <Label htmlFor={`actuator-location-${deviceId}`}>
              Vị trí lắp đặt
            </Label>
            <Input
              id={`actuator-location-${deviceId}`}
              value={location}
              onChange={(event) => setLocation(event.target.value)}
            />
          </div>
          <div className="flex flex-col gap-2">
            <Label htmlFor={`actuator-notes-${deviceId}`}>Ghi chú</Label>
            <Textarea
              id={`actuator-notes-${deviceId}`}
              value={notes}
              onChange={(event) => setNotes(event.target.value)}
            />
          </div>
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={() => setOpen(false)}>
            Hủy
          </Button>
          <Button
            disabled={!modelId || mutation.isPending}
            onClick={() => mutation.mutate()}
          >
            {mutation.isPending ? "Đang thêm…" : "Thêm vào thiết bị"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
