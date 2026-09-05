import { useState, type ReactNode } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Pencil, Plus } from "lucide-react";
import { toast } from "sonner";

import { actuatorModelApi } from "@/entities/actuator-model/api/actuator-model-api";
import { deviceTemplateApi } from "@/entities/device-template/api/device-template-api";
import type { TemplateActuator, TemplateActuatorInput } from "@/entities/device-template/model/types";
import { useProtectedQueryScope } from "@/features/auth/model/use-protected-query-scope";
import { formatBackendError } from "@/shared/api/backend-error";
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
import { Input } from "@/shared/ui/input";
import { Label } from "@/shared/ui/label";
import {
  Select,
  SelectContent,
  SelectGroup,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/shared/ui/select";
import { Switch } from "@/shared/ui/switch";
import { Textarea } from "@/shared/ui/textarea";

type ActuatorType = TemplateActuator["actuator_type"];
type DefaultState = "INHERIT" | "ON" | "OFF";

const TYPE_LABELS: Record<ActuatorType, string> = {
  SWITCH: "Công tắc",
  PUMP: "Bơm",
  VALVE: "Van",
  LIGHT: "Đèn",
  ALARM: "Cảnh báo",
  OTHER: "Khác",
};

export function AddTemplateActuatorDialog({
  templateId,
  nextOrder,
  actuator,
}: {
  templateId: number;
  nextOrder: number;
  actuator?: TemplateActuator;
}) {
  const [open, setOpen] = useState(false);
  const [modelId, setModelId] = useState(
    actuator ? String(actuator.actuator_model_id) : "",
  );
  const [code, setCode] = useState(actuator?.code ?? "");
  const [name, setName] = useState(actuator?.default_name ?? "");
  const [location, setLocation] = useState(actuator?.default_location ?? "");
  const [notes, setNotes] = useState(actuator?.default_notes ?? "");
  const [actuatorType, setActuatorType] = useState<ActuatorType>(
    actuator?.actuator_type ?? "SWITCH",
  );
  const [defaultState, setDefaultState] = useState<DefaultState>(
    actuator?.default_state === true
      ? "ON"
      : actuator?.default_state === false
        ? "OFF"
        : "INHERIT",
  );
  const [monitorCurrent, setMonitorCurrent] = useState(
    actuator?.monitor_current ?? false,
  );
  const [profileId, setProfileId] = useState(
    actuator?.electrical_profile_id
      ? String(actuator.electrical_profile_id)
      : "NONE",
  );
  const [sortOrder, setSortOrder] = useState(
    String(actuator?.sort_order ?? nextOrder),
  );
  const [enabled, setEnabled] = useState(actuator?.is_enabled ?? true);
  const { queryScope } = useProtectedQueryScope();
  const client = useQueryClient();
  const models = useQuery({
    queryKey: queryKeys.actuatorModels.list(queryScope),
    queryFn: actuatorModelApi.list,
    enabled: open,
  });
  const profiles = useQuery({
    queryKey: ["actuator-current-profiles", ...queryScope],
    queryFn: deviceTemplateApi.listActuatorCurrentProfiles,
    enabled: open && monitorCurrent,
  });
  const selectedModelId = Number(modelId);
  const selectedModel = models.data?.find((model) => model.id === selectedModelId);
  const availableProfiles =
    profiles.data?.filter((profile) =>
      profile.actuator_model_ids.includes(selectedModelId),
    ) ?? [];
  const makePayload = (): TemplateActuatorInput => ({
    actuator_model_id: selectedModelId,
    code: code.trim().toUpperCase(),
    default_name: name.trim() || undefined,
    default_location: location.trim() || undefined,
    default_notes: notes.trim() || undefined,
    actuator_type: actuatorType,
    default_state: defaultState === "INHERIT" ? null : defaultState === "ON",
    command_capability: "ON_OFF",
    monitor_current: monitorCurrent,
    electrical_profile_id:
      monitorCurrent && profileId !== "NONE" ? Number(profileId) : null,
    sort_order: Number(sortOrder),
    is_required: false,
    is_enabled: enabled,
  });
  const mutation = useMutation({
    mutationFn: () =>
      actuator
        ? deviceTemplateApi.updateActuator(
            templateId,
            actuator.id,
            makePayload(),
          )
        : deviceTemplateApi.addActuator(templateId, makePayload()),
    onSuccess: async () => {
      await invalidateQueries.deviceTemplates(client);
      setOpen(false);
      toast.success(
        actuator ? "Đã cập nhật cơ cấu chấp hành" : "Đã thêm cơ cấu chấp hành",
      );
    },
    onError: (error) =>
      toast.error(formatBackendError(error, "Không thể lưu cơ cấu chấp hành")),
  });
  const valid = Boolean(
    modelId &&
    /^[A-Z0-9_-]{2,80}$/.test(code.trim().toUpperCase()) &&
    name.trim() &&
    Number.isInteger(Number(sortOrder)) &&
    Number(sortOrder) >= 0,
  );

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        {actuator ? (
          <Button
            variant="ghost"
            size="icon"
            aria-label={`Chỉnh sửa ${actuator.default_name || actuator.model_name}`}
          >
            <Pencil />
          </Button>
        ) : (
          <Button variant="outline" size="sm">
            <Plus data-icon="inline-start" />
            Thêm cơ cấu chấp hành
          </Button>
        )}
      </DialogTrigger>
      <DialogContent className="max-h-[90vh] overflow-y-auto sm:max-w-2xl">
        <DialogHeader>
          <DialogTitle>
            {actuator ? "Chỉnh sửa cơ cấu chấp hành" : "Thêm cơ cấu chấp hành"}
          </DialogTitle>
          <DialogDescription>
            Chỉ lưu metadata, capability và cấu hình mặc định. Dòng điện thực tế
            luôn lấy từ telemetry runtime.
          </DialogDescription>
        </DialogHeader>
        <form
          className="grid gap-4"
          onSubmit={(event) => {
            event.preventDefault();
            mutation.mutate();
          }}
        >
          <div className="grid gap-4 sm:grid-cols-2">
            <Field
              label="Tên cơ cấu chấp hành *"
              id={`actuator-name-${templateId}-${actuator?.id ?? "new"}`}
            >
              <Input
                id={`actuator-name-${templateId}-${actuator?.id ?? "new"}`}
                required
                value={name}
                onChange={(event) => setName(event.target.value)}
              />
            </Field>
            {selectedModel ? <div className="sm:col-span-2 rounded-lg border bg-muted/30 p-3 text-sm"><p className="font-medium">Giám sát điện kế thừa từ mẫu</p><p className="mt-1 text-muted-foreground">{selectedModel.feedbacks.filter((feedback) => feedback.is_enabled).length ? `Khi tạo thiết bị sẽ tự tạo: ${selectedModel.feedbacks.filter((feedback) => feedback.is_enabled).map((feedback) => feedback.feedback_role === "SUPPLY_VOLTAGE" ? "cảm biến điện áp cấp" : "cảm biến dòng điện hoạt động").join(" và ")}.` : "Mẫu này không hỗ trợ giám sát điện."}</p></div> : null}
            <Field
              label="Mã *"
              id={`actuator-code-${templateId}-${actuator?.id ?? "new"}`}
            >
              <Input
                id={`actuator-code-${templateId}-${actuator?.id ?? "new"}`}
                required
                pattern="[A-Z0-9_-]{2,80}"
                value={code}
                onChange={(event) => setCode(event.target.value.toUpperCase())}
              />
            </Field>
            <Field
              label="Model *"
              id={`actuator-model-${templateId}-${actuator?.id ?? "new"}`}
            >
              <Select
                value={modelId}
                disabled={Boolean(actuator)}
                onValueChange={(value) => {
                  setModelId(value);
                  const model = models.data?.find(
                    (item) => item.id === Number(value),
                  );
                  if (!code.trim() && model) setCode(model.code);
                  if (!name.trim() && model) setName(model.name);
                  setProfileId("NONE");
                }}
              >
                <SelectTrigger
                  id={`actuator-model-${templateId}-${actuator?.id ?? "new"}`}
                >
                  <SelectValue placeholder="Chọn Model" />
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
            </Field>
            <Field
              label="Loại cơ cấu chấp hành *"
              id={`actuator-type-${templateId}-${actuator?.id ?? "new"}`}
            >
              <Select
                value={actuatorType}
                onValueChange={(value) =>
                  setActuatorType(value as ActuatorType)
                }
              >
                <SelectTrigger
                  id={`actuator-type-${templateId}-${actuator?.id ?? "new"}`}
                >
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {Object.entries(TYPE_LABELS).map(([value, label]) => (
                    <SelectItem key={value} value={value}>
                      {label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </Field>
            <Field
              label="Trạng thái mặc định"
              id={`actuator-state-${templateId}-${actuator?.id ?? "new"}`}
            >
              <Select
                value={defaultState}
                onValueChange={(value) =>
                  setDefaultState(value as DefaultState)
                }
              >
                <SelectTrigger
                  id={`actuator-state-${templateId}-${actuator?.id ?? "new"}`}
                >
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="INHERIT">Theo Model</SelectItem>
                  <SelectItem value="ON">Bật</SelectItem>
                  <SelectItem value="OFF">Tắt</SelectItem>
                </SelectContent>
              </Select>
            </Field>
            <Field
              label="Khả năng điều khiển"
              id={`actuator-capability-${templateId}-${actuator?.id ?? "new"}`}
            >
              <Input
                id={`actuator-capability-${templateId}-${actuator?.id ?? "new"}`}
                value="Bật / Tắt"
                disabled
              />
            </Field>
            <Field
              label="Vị trí mặc định"
              id={`actuator-location-${templateId}-${actuator?.id ?? "new"}`}
            >
              <Input
                id={`actuator-location-${templateId}-${actuator?.id ?? "new"}`}
                value={location}
                onChange={(event) => setLocation(event.target.value)}
              />
            </Field>
            <Field
              label="Thứ tự hiển thị"
              id={`actuator-order-${templateId}-${actuator?.id ?? "new"}`}
            >
              <Input
                id={`actuator-order-${templateId}-${actuator?.id ?? "new"}`}
                type="number"
                min={0}
                required
                value={sortOrder}
                onChange={(event) => setSortOrder(event.target.value)}
              />
            </Field>
          </div>
          <Field
            label="Ghi chú mặc định"
            id={`actuator-notes-${templateId}-${actuator?.id ?? "new"}`}
          >
            <Textarea
              id={`actuator-notes-${templateId}-${actuator?.id ?? "new"}`}
              value={notes}
              onChange={(event) => setNotes(event.target.value)}
            />
          </Field>
          <Setting
            label="Giám sát dòng điện"
            description="Kế thừa định nghĩa dữ liệu phản hồi từ Model và cho phép gắn Profile điện."
            checked={monitorCurrent}
            onChange={(value) => {
              setMonitorCurrent(value);
              if (!value) setProfileId("NONE");
            }}
          />
          {monitorCurrent ? (
            <Field
              label="Profile điện"
              id={`actuator-profile-${templateId}-${actuator?.id ?? "new"}`}
            >
              <Select value={profileId} onValueChange={setProfileId}>
                <SelectTrigger
                  id={`actuator-profile-${templateId}-${actuator?.id ?? "new"}`}
                >
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="NONE">Chưa gắn Profile</SelectItem>
                  {availableProfiles.map((profile) => (
                    <SelectItem key={profile.id} value={String(profile.id)}>
                      {profile.name} · {profile.code}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              {!profiles.isLoading && !availableProfiles.length ? (
                <p className="text-xs text-muted-foreground">
                  Chưa có Profile điện phù hợp với Model này.
                </p>
              ) : null}
            </Field>
          ) : null}
          <Setting
            label="Trạng thái hoạt động"
            description={
              enabled
                ? "Sẽ được tạo khi provisioning Device."
                : "Giữ cấu hình nhưng không kích hoạt actuator runtime mới."
            }
            checked={enabled}
            onChange={setEnabled}
          />
          <DialogFooter>
            <Button
              type="button"
              variant="outline"
              onClick={() => setOpen(false)}
            >
              Hủy
            </Button>
            <Button type="submit" disabled={!valid || mutation.isPending}>
              {mutation.isPending ? "Đang lưu…" : "Lưu"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}

function Field({
  label,
  id,
  children,
}: {
  label: string;
  id: string;
  children: ReactNode;
}) {
  return (
    <div className="flex flex-col gap-2">
      <Label htmlFor={id}>{label}</Label>
      {children}
    </div>
  );
}

function Setting({
  label,
  description,
  checked,
  onChange,
}: {
  label: string;
  description: string;
  checked: boolean;
  onChange: (value: boolean) => void;
}) {
  return (
    <div className="flex items-center justify-between gap-4 rounded-lg border p-3">
      <div>
        <Label>{label}</Label>
        <p className="text-xs text-muted-foreground">{description}</p>
      </div>
      <Switch checked={checked} onCheckedChange={onChange} aria-label={label} />
    </div>
  );
}
