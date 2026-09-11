import { useMutation, useQueryClient } from "@tanstack/react-query";
import { ArrowDown, ArrowUp, Layers3, Power, Trash2, Zap } from "lucide-react";
import { toast } from "sonner";
import { deviceTemplateApi } from "@/entities/device-template/api/device-template-api";
import type {
  DeviceTemplate,
  TemplateSensor,
} from "@/entities/device-template/model/types";
import { AddTemplateSensorDialog } from "@/features/manage-device-templates/components/AddTemplateSensorDialog";
import { AddTemplateActuatorDialog } from "@/features/manage-device-templates/components/AddTemplateActuatorDialog";
import { DeviceTemplateDialog } from "@/features/manage-device-templates/components/DeviceTemplateDialog";
import { EditTemplateSensorDialog } from "@/features/manage-device-templates/components/EditTemplateSensorDialog";
import { invalidateQueries } from "@/shared/api/query-invalidation";
import { Badge } from "@/shared/ui/badge";
import { Button } from "@/shared/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/shared/ui/card";

const ENERGY_CODES = [
  "OUTPUT_VOLTAGE_V",
  "INPUT_VOLTAGE_V",
  "LOAD_CURRENT_A",
  "INPUT_CURRENT_A",
  "POWER_W",
  "ENERGY_TOTAL_WH",
] as const;

export function DeviceTemplateCard({ template }: { template: DeviceTemplate }) {
  const client = useQueryClient();
  const sensors = [...template.sensors].sort(
    (left, right) => left.sort_order - right.sort_order || left.id - right.id,
  );
  const remove = useMutation({
    mutationFn: () => deviceTemplateApi.remove(template.id),
    onSuccess: async () => {
      await invalidateQueries.deviceTemplates(client);
      toast.success("Đã xóa mềm mẫu thiết bị");
    },
    onError: () => toast.error("Không thể xóa mẫu thiết bị"),
  });
  const removeSensor = useMutation({
    mutationFn: (mappingId: number) =>
      deviceTemplateApi.removeSensor(template.id, mappingId),
    onSuccess: async () => {
      await invalidateQueries.deviceTemplates(client);
      toast.success("Đã gỡ cảm biến khỏi mẫu");
    },
    onError: () => toast.error("Không thể gỡ cảm biến khỏi mẫu"),
  });
  const removeActuator = useMutation({
    mutationFn: (mappingId: number) =>
      deviceTemplateApi.removeActuator(template.id, mappingId),
    onSuccess: async () => {
      await invalidateQueries.deviceTemplates(client);
      toast.success("Đã xóa cơ cấu chấp hành khỏi mẫu thiết bị");
    },
    onError: () =>
      toast.error("Không thể xóa cơ cấu chấp hành đang được sử dụng"),
  });
  const defaults = useMutation({
    mutationFn: () => deviceTemplateApi.addEnergyDefaults(template.id),
    onSuccess: async () => {
      await invalidateQueries.deviceTemplates(client);
      toast.success("Đã bổ sung cấu hình cảm biến năng lượng mặc định");
    },
    onError: () => toast.error("Không thể bổ sung cảm biến mặc định"),
  });
  const reorder = useMutation({
    mutationFn: async ({
      sensor,
      target,
    }: {
      sensor: TemplateSensor;
      target: TemplateSensor;
    }) => {
      await deviceTemplateApi.updateSensor(template.id, sensor.id, {
        sort_order: target.sort_order,
      });
      await deviceTemplateApi.updateSensor(template.id, target.id, {
        sort_order: sensor.sort_order,
      });
    },
    onSuccess: async () => {
      await invalidateQueries.deviceTemplates(client);
      toast.success("Đã lưu thứ tự hiển thị");
    },
    onError: () => toast.error("Không thể đổi thứ tự hiển thị"),
  });
  const mappedCodes = new Set(sensors.map((sensor) => sensor.model_code));
  const missingEnergyMappings = ENERGY_CODES.filter(
    (code) => !mappedCodes.has(code),
  );
  const invalidEnergyCount = sensors.filter(
    (sensor) =>
      !ENERGY_CODES.includes(
        sensor.model_code as (typeof ENERGY_CODES)[number],
      ),
  ).length;
  const complete =
    template.device_kind !== "ENERGY_MONITOR" ||
    (missingEnergyMappings.length === 0 &&
      invalidEnergyCount === 0 &&
      sensors.length === ENERGY_CODES.length &&
      sensors.every((sensor) => sensor.is_required));
  const requiredCount = sensors.filter((sensor) => sensor.is_required).length;
  return (
    <Card
      className="flex h-full flex-col overflow-hidden"
      data-testid={
        template.code === "ENERGY_MONITOR_12V"
          ? "energy-monitor-template"
          : undefined
      }
    >
      <CardHeader className="border-b bg-muted/30">
        <div className="flex items-start justify-between gap-3">
          <div className="flex min-w-0 flex-col gap-2">
            <Badge variant="outline" className="w-fit">
              {template.code}
            </Badge>
            <CardTitle className="text-base">{template.name}</CardTitle>
            <div className="flex flex-wrap gap-2">
              <Badge
                variant={
                  template.device_kind === "ENERGY_MONITOR"
                    ? "success"
                    : "secondary"
                }
              >
                {template.device_kind}
              </Badge>
              {template.nominal_output_voltage_v ? (
                <Badge variant="outline">
                  Danh định {template.nominal_output_voltage_v} V
                </Badge>
              ) : null}
              <Badge variant={complete ? "success" : "warning"}>
                {complete ? "Cấu hình hoàn chỉnh" : "Thiếu cấu hình"}
              </Badge>
            </div>
          </div>
          <Badge variant={template.is_active ? "success" : "secondary"}>
            {template.is_active ? "Khả dụng" : "Vô hiệu hóa"}
          </Badge>
        </div>
        <CardDescription>
          {template.description || "Chưa có mô tả cho mẫu thiết bị này."}
        </CardDescription>
      </CardHeader>
      <CardContent className="flex flex-1 flex-col gap-4 pt-5">
        {template.device_kind === "ENERGY_MONITOR" && !complete ? (
          <div className="rounded-lg border border-warning bg-muted/20 p-3 text-sm">
            <strong>Thiếu:</strong>{" "}
            {missingEnergyMappings.join(", ") || "Không có"}
            {invalidEnergyCount
              ? ` · ${invalidEnergyCount} mapping ngoài chuẩn`
              : ""}
          </div>
        ) : null}
        <section aria-label="Cảm biến của mẫu thiết bị">
          <div className="flex flex-wrap items-center justify-between gap-2 text-sm">
            <span className="flex items-center gap-2 font-medium">
              <Layers3 />
              Cảm biến của mẫu thiết bị
            </span>
            <div className="flex gap-2">
              <Badge
                variant="outline"
                data-testid="energy-monitor-measurement-count"
              >
                {sensors.length} cảm biến
              </Badge>
              <Badge variant="outline">{requiredCount} bắt buộc</Badge>
              <Badge variant="outline">
                {sensors.length - requiredCount} tùy chọn
              </Badge>
            </div>
          </div>
          {sensors.length ? (
            <ol
              className="mt-2 flex flex-col gap-2"
              data-testid="device-template-sensor-list"
            >
              {sensors.map((sensor, index) => {
                const canonicalLocked =
                  template.device_kind === "ENERGY_MONITOR" &&
                  ENERGY_CODES.includes(
                    sensor.model_code as (typeof ENERGY_CODES)[number],
                  );
                return (
                  <li
                    key={sensor.id}
                    className="flex flex-col gap-3 rounded-lg border bg-background px-3 py-2 sm:flex-row sm:items-center sm:justify-between"
                  >
                    <div className="min-w-0">
                      <div className="truncate text-sm font-medium">
                        {index + 1}. {sensor.display_name || sensor.model_name}
                      </div>
                      <div className="text-xs text-muted-foreground">
                        {sensor.model_code} · {sensor.unit} ·{" "}
                        {sensor.value_type} · {sensor.measurement_semantics}
                      </div>
                      <Badge
                        className="mt-1"
                        variant={sensor.is_required ? "success" : "secondary"}
                      >
                        {sensor.is_required ? "Bắt buộc" : "Tùy chọn"}
                      </Badge>
                    </div>
                    <div className="flex items-center gap-1">
                      <EditTemplateSensorDialog
                        templateId={template.id}
                        sensor={sensor}
                        requiredLocked={canonicalLocked}
                      />
                      <Button
                        variant="ghost"
                        size="icon"
                        aria-label={`Di chuyển ${sensor.model_name} lên`}
                        disabled={index === 0 || reorder.isPending}
                        onClick={() =>
                          reorder.mutate({ sensor, target: sensors[index - 1] })
                        }
                      >
                        <ArrowUp />
                      </Button>
                      <Button
                        variant="ghost"
                        size="icon"
                        aria-label={`Di chuyển ${sensor.model_name} xuống`}
                        disabled={
                          index === sensors.length - 1 || reorder.isPending
                        }
                        onClick={() =>
                          reorder.mutate({ sensor, target: sensors[index + 1] })
                        }
                      >
                        <ArrowDown />
                      </Button>
                      <Button
                        variant="ghost"
                        size="icon"
                        aria-label={
                          canonicalLocked
                            ? `${sensor.model_name} là phép đo bắt buộc`
                            : `Gỡ ${sensor.model_name} khỏi mẫu`
                        }
                        disabled={canonicalLocked || removeSensor.isPending}
                        onClick={() => removeSensor.mutate(sensor.id)}
                      >
                        <Trash2 />
                      </Button>
                    </div>
                  </li>
                );
              })}
            </ol>
          ) : (
            <div className="mt-2 rounded-lg border border-dashed p-4 text-center text-sm text-muted-foreground">
              Mẫu chưa có cảm biến mặc định.
            </div>
          )}
        </section>
        <section aria-label="Cơ cấu chấp hành của mẫu thiết bị">
          <div className="flex flex-wrap items-center justify-between gap-2 text-sm">
            <span className="flex items-center gap-2 font-medium">
              <Power />
              Cơ cấu chấp hành
            </span>
            <strong>{template.actuators.length}</strong>
          </div>
          {template.actuators.length ? (
            <ol className="mt-2 flex flex-col gap-2">
              {[...template.actuators]
                .sort((left, right) => left.sort_order - right.sort_order)
                .map((actuator, index) => (
                  <li
                    key={actuator.id}
                    className="flex flex-col gap-3 rounded-lg border bg-background px-3 py-3 sm:flex-row sm:items-center sm:justify-between"
                  >
                    <div className="min-w-0">
                      <div className="truncate text-sm font-medium">
                        {index + 1}.{" "}
                        {actuator.default_name || actuator.model_name}
                      </div>
                      <div className="mt-1 text-xs text-muted-foreground">
                        Mã: {actuator.code} · Model: {actuator.model_name} ·
                        Loại: {actuator.actuator_type}
                      </div>
                      <div className="mt-2 flex flex-wrap gap-2">
                        <Badge
                          variant={
                            actuator.monitor_current ? "success" : "secondary"
                          }
                        >
                          {actuator.monitor_current
                            ? "Có giám sát dòng điện"
                            : "Không giám sát dòng điện"}
                        </Badge>
                        <Badge variant="outline">
                          Profile điện:{" "}
                          {actuator.electrical_profile_name || "Chưa gắn"}
                        </Badge>
                        <Badge
                          variant={
                            actuator.is_enabled ? "success" : "secondary"
                          }
                        >
                          {actuator.is_enabled ? "Đang hoạt động" : "Tạm tắt"}
                        </Badge>
                      </div>
                    </div>
                    <div className="flex items-center gap-1">
                  <AddTemplateActuatorDialog
                    templateId={template.id}
                    nextOrder={actuator.sort_order}
                    actuator={actuator}
                  />
                      <Button
                        variant="ghost"
                        size="icon"
                        aria-label={`Xóa ${actuator.default_name || actuator.model_name}`}
                        disabled={removeActuator.isPending}
                        onClick={() => {
                          if (
                            window.confirm(
                              `Xóa cơ cấu chấp hành ${actuator.default_name || actuator.model_name}?`,
                            )
                          )
                            removeActuator.mutate(actuator.id);
                        }}
                      >
                        <Trash2 />
                      </Button>
                    </div>
                  </li>
                ))}
            </ol>
          ) : (
            <div className="mt-2 rounded-lg border border-dashed p-4 text-center text-sm text-muted-foreground">
              Mẫu chưa có cơ cấu chấp hành.
            </div>
          )}
        </section>
      </CardContent>
      <CardFooter className="flex flex-wrap gap-2 border-t pt-4">
        <DeviceTemplateDialog template={template} />
        <DeviceTemplateDialog template={template} duplicate />
        <AddTemplateSensorDialog
          templateId={template.id}
          mappedModelIds={sensors.map((item) => item.sensor_model_id)}
          nextOrder={Math.max(0, ...sensors.map((item) => item.sort_order))}
        />
        {template.device_kind === "ENERGY_MONITOR" ? (
          <Button
            variant="outline"
            size="sm"
            onClick={() => defaults.mutate()}
            disabled={defaults.isPending || complete}
          >
            <Zap data-icon="inline-start" />
            Bổ sung 6 phép đo chuẩn
          </Button>
        ) : (
            <AddTemplateActuatorDialog
              templateId={template.id}
              nextOrder={
                Math.max(
                0,
                ...template.actuators.map((item) => item.sort_order),
                ) + 1
              }
            />
        )}
        <Button
          variant="outline"
          size="sm"
          className="text-destructive"
          onClick={() => remove.mutate()}
          disabled={remove.isPending}
        >
          <Trash2 data-icon="inline-start" />
          Xóa
        </Button>
      </CardFooter>
    </Card>
  );
}
