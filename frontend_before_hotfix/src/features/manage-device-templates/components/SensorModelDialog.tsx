import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Plus } from "lucide-react";
import { toast } from "sonner";

import { sensorModelApi } from "@/entities/sensor-model/api/sensor-model-api";
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
import { Input } from "@/shared/ui/input";
import { Label } from "@/shared/ui/label";
import { Textarea } from "@/shared/ui/textarea";

export function SensorModelDialog() {
  const [open, setOpen] = useState(false);
  const [code, setCode] = useState("");
  const [name, setName] = useState("");
  const [unit, setUnit] = useState("");
  const [description, setDescription] = useState("");
  const client = useQueryClient();
  const mutation = useMutation({
    mutationFn: () =>
      sensorModelApi.create({
        code: code.trim().toUpperCase(),
        name: name.trim(),
        unit: unit.trim(),
        description: description.trim() || null,
      }),
    onSuccess: async () => {
      await client.invalidateQueries({ queryKey: queryKeys.sensorModels.all });
      setOpen(false);
      setCode("");
      setName("");
      setUnit("");
      setDescription("");
      toast.success("Đã thêm mẫu cảm biến");
    },
    onError: () => toast.error("Không thể thêm mẫu cảm biến"),
  });

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button className="w-full sm:w-auto">
          <Plus data-icon="inline-start" />
          Thêm mẫu cảm biến
        </Button>
      </DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Thêm mẫu cảm biến</DialogTitle>
          <DialogDescription>
            Tạo Sensor Model trong catalog, không tạo cảm biến runtime.
          </DialogDescription>
        </DialogHeader>
        <form
          className="flex flex-col gap-4"
          onSubmit={(event) => {
            event.preventDefault();
            mutation.mutate();
          }}
        >
          <div className="grid gap-4 sm:grid-cols-2">
            <div className="flex flex-col gap-2">
              <Label htmlFor="sensor-model-code">Mã kỹ thuật</Label>
              <Input
                id="sensor-model-code"
                required
                pattern="[A-Z0-9_-]+"
                value={code}
                onChange={(event) => setCode(event.target.value.toUpperCase())}
              />
            </div>
            <div className="flex flex-col gap-2">
              <Label htmlFor="sensor-model-name">Tên mẫu</Label>
              <Input
                id="sensor-model-name"
                required
                value={name}
                onChange={(event) => setName(event.target.value)}
              />
            </div>
          </div>
          <div className="flex flex-col gap-2">
            <Label htmlFor="sensor-model-unit">Đơn vị</Label>
            <Input
              id="sensor-model-unit"
              required
              value={unit}
              onChange={(event) => setUnit(event.target.value)}
            />
          </div>
          <div className="flex flex-col gap-2">
            <Label htmlFor="sensor-model-description">Mô tả</Label>
            <Textarea
              id="sensor-model-description"
              value={description}
              onChange={(event) => setDescription(event.target.value)}
            />
          </div>
          <DialogFooter>
            <Button
              type="button"
              variant="outline"
              onClick={() => setOpen(false)}
            >
              Hủy
            </Button>
            <Button
              type="submit"
              disabled={
                !code.trim() ||
                !name.trim() ||
                !unit.trim() ||
                mutation.isPending
              }
            >
              {mutation.isPending ? "Đang thêm…" : "Thêm mẫu"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
