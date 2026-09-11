import { useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  CheckCircle2,
  CirclePower,
  Clock3,
  Gauge,
  Pencil,
  Save,
  Trash2,
} from "lucide-react";
import { Link, useNavigate, useParams } from "react-router-dom";
import {
  createCommand,
  deleteActuator,
  getActuator,
  getDevice,
  getMonitoringActuatorHistory,
  listActuatorCommands,
  listActuatorReadings,
  queryKeys,
  updateActuator,
} from "@/api/resources";
import type { ActuatorUpdate, MonitoringRange } from "@/api/contracts";
import { errorMessage } from "@/api/client";
import { useAuth } from "@/app/auth";
import {
  actuatorStateLabel,
  commandStatusLabel,
  desiredStateLabel,
  synchronizationLabel,
} from "@/entities/actuator/lib/actuator-semantics";
import { AlertScenarioSection } from "@/features/alert-scenarios/AlertScenarioSection";
import { ActuatorOperationChart } from "@/features/view-device-monitoring-history/ui/ActuatorOperationChart";
import { MonitoringRangeSelector } from "@/features/view-device-monitoring-history/ui/MonitoringRangeSelector";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "@/shared/ui/alert-dialog";
import { Badge } from "@/shared/ui/badge";
import { Button } from "@/shared/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/shared/ui/card";
import { EmptyState } from "@/shared/ui/empty-state";
import { Input } from "@/shared/ui/input";
import { Label } from "@/shared/ui/label";
import { Skeleton } from "@/shared/ui/skeleton";
import { StatusBadge } from "@/shared/ui/status-badge";
import { Switch } from "@/shared/ui/switch";
import { Textarea } from "@/shared/ui/textarea";

export function ActuatorDetailPage() {
  const params = useParams();
  const systemId = params.systemId ?? "";
  const deviceId = params.deviceId ?? "";
  const actuatorId = params.actuatorId ?? "";
  const validIds = Boolean(systemId && deviceId && actuatorId);
  const { can } = useAuth();
  const client = useQueryClient();
  const navigate = useNavigate();
  const [editing, setEditing] = useState(false);
  const [showAllHistory, setShowAllHistory] = useState(false);
  const [range, setRange] = useState<MonitoringRange>("24h");
  const [editDraft, setEditDraft] = useState<ActuatorUpdate>({});
  const actuator = useQuery({
    queryKey: queryKeys.actuator(systemId, deviceId, actuatorId),
    queryFn: () => getActuator(systemId, deviceId, actuatorId),
    enabled: validIds,
    refetchInterval: 10_000,
  });
  const device = useQuery({
    queryKey: queryKeys.device(systemId, deviceId),
    queryFn: () => getDevice(systemId, deviceId),
    enabled: validIds,
    refetchInterval: 10_000,
  });
  const operation = useQuery({
    queryKey: queryKeys.monitoringActuatorHistory(systemId, deviceId, range),
    queryFn: () => getMonitoringActuatorHistory(systemId, deviceId, range),
    enabled: validIds && can("actuators.readings.read"),
    refetchInterval: 15_000,
  });
  const readings = useQuery({
    queryKey: queryKeys.actuatorReadings(systemId, deviceId, actuatorId, 50),
    queryFn: () => listActuatorReadings(systemId, deviceId, actuatorId, 50),
    enabled: validIds && can("actuators.readings.read"),
    refetchInterval: 15_000,
  });
  const commands = useQuery({
    queryKey: queryKeys.actuatorCommands(systemId, deviceId, actuatorId, 20),
    queryFn: () => listActuatorCommands(systemId, deviceId, actuatorId, 20),
    enabled: validIds && can("actuators.commands.read"),
    refetchInterval: 5_000,
  });
  useEffect(() => {
    if (actuator.data)
      setEditDraft({
        name: actuator.data.name,
        code: actuator.data.code,
        location: actuator.data.location,
        notes: actuator.data.notes,
        is_enabled: actuator.data.is_enabled,
      });
  }, [actuator.data]);
  const refreshRuntime = async () => {
    await Promise.all([
      client.invalidateQueries({
        queryKey: queryKeys.actuator(systemId, deviceId, actuatorId),
      }),
      client.invalidateQueries({
        queryKey: queryKeys.actuatorCommands(
          systemId,
          deviceId,
          actuatorId,
          20,
        ),
      }),
      client.invalidateQueries({
        queryKey: queryKeys.device(systemId, deviceId),
      }),
      client.invalidateQueries({
        queryKey: queryKeys.monitoringLatest(systemId),
      }),
      client.invalidateQueries({
        queryKey: queryKeys.monitoringActuatorHistory(
          systemId,
          deviceId,
          range,
        ),
      }),
      client.invalidateQueries({ queryKey: queryKeys.scada(systemId) }),
    ]);
  };
  const command = useMutation({
    mutationFn: (desired_state: boolean) =>
      createCommand(systemId, deviceId, actuatorId, { desired_state }),
    onSuccess: refreshRuntime,
  });
  const saveActuator = useMutation({
    mutationFn: () => updateActuator(systemId, deviceId, actuatorId, editDraft),
    onSuccess: async () => {
      await refreshRuntime();
      setEditing(false);
    },
  });
  const removeActuator = useMutation({
    mutationFn: () => deleteActuator(systemId, deviceId, actuatorId),
    onSuccess: async () => {
      await client.invalidateQueries({
        queryKey: queryKeys.device(systemId, deviceId),
      });
      navigate(`/aquaponics-systems/${systemId}/devices/${deviceId}`);
    },
  });
  if (!validIds)
    return (
      <EmptyState
        icon={CirclePower}
        title="Đường dẫn Actuator không hợp lệ"
        description="System, Device và Actuator ID phải là UUID hợp lệ."
      />
    );
  if (actuator.isLoading || device.isLoading)
    return <Skeleton className="h-96" />;
  if (actuator.isError || !actuator.data || device.isError || !device.data)
    return (
      <EmptyState
        icon={CirclePower}
        title="Không thể tải Actuator"
        description={errorMessage(actuator.error ?? device.error)}
      />
    );
  const value = actuator.data;
  const sync = synchronizationLabel(value.desired_state, value.reported_state);
  const history = operation.data?.items.find(
    (item) => item.actuator_id === actuatorId,
  );
  const recentReadings = showAllHistory
    ? readings.data
    : readings.data?.slice(0, 10);
  const recentCommands = showAllHistory
    ? commands.data
    : commands.data?.slice(0, 10);
  const latestAt =
    history?.readings.at(-1)?.recorded_at ??
    history?.points.at(-1)?.recorded_at ??
    null;
  return (
    <div className="space-y-6">
      <header className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-sm text-muted-foreground">
            <Link
              className="text-primary hover:underline"
              to={`/aquaponics-systems/${systemId}/devices/${deviceId}`}
            >
              Device
            </Link>{" "}
            / Actuator
          </p>
          <div className="mt-1 flex flex-wrap items-center gap-3">
            <h1 className="text-balance text-2xl font-semibold">
              {value.name}
            </h1>
            <StatusBadge value={device.data.status} />
          </div>
          <p className="mt-1 text-sm text-muted-foreground">
            {value.code} ·{" "}
            {value.location ?? device.data.location ?? "Chưa đặt vị trí"}
          </p>
          <Badge
            className="mt-2"
            variant={value.is_enabled ? "success" : "secondary"}
          >
            {value.is_enabled ? "Đã kích hoạt" : "Vô hiệu hóa"}
          </Badge>
        </div>
        <div className="flex flex-wrap gap-2">
          {can("actuators.update") ? (
            <Button
              variant="outline"
              onClick={() => setEditing((current) => !current)}
            >
              <Pencil />
              Chỉnh sửa
            </Button>
          ) : null}
          {can("actuators.delete") ? (
            <AlertDialog>
              <AlertDialogTrigger asChild>
                <Button variant="destructive">
                  <Trash2 />
                  Xoá
                </Button>
              </AlertDialogTrigger>
              <AlertDialogContent>
                <AlertDialogHeader>
                  <AlertDialogTitle>Xoá {value.name}?</AlertDialogTitle>
                  <AlertDialogDescription>
                    Actuator sẽ bị xoá khỏi Device hiện tại.
                  </AlertDialogDescription>
                </AlertDialogHeader>
                <AlertDialogFooter>
                  <AlertDialogCancel>Huỷ</AlertDialogCancel>
                  <AlertDialogAction
                    variant="destructive"
                    onClick={() => removeActuator.mutate()}
                  >
                    Xoá
                  </AlertDialogAction>
                </AlertDialogFooter>
              </AlertDialogContent>
            </AlertDialog>
          ) : null}
        </div>
      </header>
      {editing ? (
        <form
          className="grid gap-4 rounded-xl border bg-card p-5 sm:grid-cols-2"
          onSubmit={(event) => {
            event.preventDefault();
            saveActuator.mutate();
          }}
        >
          <TextField
            id="actuator-name"
            label="Tên Actuator"
            value={editDraft.name ?? ""}
            onChange={(name) => setEditDraft((draft) => ({ ...draft, name }))}
          />
          <TextField
            id="actuator-code"
            label="Mã Actuator"
            value={editDraft.code ?? ""}
            onChange={(code) =>
              setEditDraft((draft) => ({ ...draft, code: code.toUpperCase() }))
            }
          />
          <TextField
            id="actuator-location"
            label="Vị trí"
            value={editDraft.location ?? ""}
            onChange={(location) =>
              setEditDraft((draft) => ({ ...draft, location }))
            }
          />
          <div>
            <Label htmlFor="actuator-notes">Ghi chú</Label>
            <Textarea
              id="actuator-notes"
              className="mt-1"
              value={editDraft.notes ?? ""}
              onChange={(event) =>
                setEditDraft((draft) => ({
                  ...draft,
                  notes: event.target.value,
                }))
              }
            />
          </div>
          <label className="flex items-center gap-3 text-sm">
            <Switch
              checked={editDraft.is_enabled ?? value.is_enabled}
              onCheckedChange={(is_enabled) =>
                setEditDraft((draft) => ({ ...draft, is_enabled }))
              }
            />
            Đã kích hoạt
          </label>
          <div className="flex justify-end gap-2">
            <Button
              type="button"
              variant="ghost"
              onClick={() => setEditing(false)}
            >
              Huỷ
            </Button>
            <Button type="submit" disabled={saveActuator.isPending}>
              <Save />
              Lưu
            </Button>
          </div>
          {saveActuator.isError ? (
            <p role="alert" className="text-sm text-destructive sm:col-span-2">
              {errorMessage(saveActuator.error)}
            </p>
          ) : null}
        </form>
      ) : null}
      <section aria-labelledby="live-operation">
        <h2
          id="live-operation"
          className="mb-3 text-balance text-lg font-semibold"
        >
          Vận hành hiện tại
        </h2>
        <div className="grid gap-4 sm:grid-cols-3">
          <Info
            label="Trạng thái"
            value={actuatorStateLabel(value.reported_state)}
          />
          <Info
            label="Điện áp"
            value={value.voltage_v == null ? "—" : `${value.voltage_v} V`}
          />
          <Info
            label="Dòng điện"
            value={value.current_a == null ? "—" : `${value.current_a} A`}
          />
        </div>
        <div className="mt-3 text-sm text-muted-foreground">
          <p>{desiredStateLabel(value.desired_state)}</p>
          <p
            className={
              sync === "Chưa đồng bộ" ? "font-medium text-amber-700" : ""
            }
          >
            {sync === "Chưa đồng bộ" ? "⚠ " : ""}
            {sync}
          </p>
          <p>
            Cập nhật gần nhất:{" "}
            {latestAt
              ? new Date(latestAt).toLocaleString("vi-VN")
              : "Chưa có dữ liệu"}
          </p>
        </div>
      </section>
      <MonitoringRangeSelector range={range} onRangeChange={setRange} />
      {operation.isLoading ? (
        <Skeleton className="h-80" />
      ) : operation.isError ? (
        <EmptyState
          icon={Gauge}
          title="Không thể tải biểu đồ vận hành"
          description={errorMessage(operation.error)}
        />
      ) : (
        <ActuatorOperationChart
          actuatorName={value.name}
          states={history?.points ?? []}
          readings={history?.readings ?? []}
          startTime={operation.data?.start_at}
          endTime={operation.data?.end_at}
        />
      )}
      {can("actuators.commands.create") ? (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <CirclePower className="size-5 text-primary" />
              Điều khiển vận hành
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="flex flex-wrap gap-3">
              <Button
                onClick={() => command.mutate(true)}
                disabled={command.isPending}
              >
                <CheckCircle2 />
                Bật
              </Button>
              <Button
                variant="outline"
                onClick={() => command.mutate(false)}
                disabled={command.isPending}
              >
                Tắt
              </Button>
            </div>
            <p className="text-sm">
              Trạng thái thực tế: {actuatorStateLabel(value.reported_state)} ·
              Yêu cầu hiện tại: {desiredStateLabel(value.desired_state)} ·{" "}
              {sync}
            </p>
            {command.isError ? (
              <p role="alert" className="text-sm text-destructive">
                {errorMessage(command.error)}
              </p>
            ) : null}
          </CardContent>
        </Card>
      ) : null}
      {can("actuators.thresholds.read") ? (
        <AlertScenarioSection
          target="ACTUATOR"
          systemId={systemId}
          deviceId={deviceId}
          resourceId={actuatorId}
          canCreate={can("actuators.thresholds.create")}
          canUpdate={can("actuators.thresholds.update")}
          canDelete={can("actuators.thresholds.delete")}
        />
      ) : null}
      <section>
        <div className="mb-3 flex items-center justify-between">
          <h2 className="text-balance text-lg font-semibold">Lịch sử</h2>
          {(readings.data?.length ?? 0) > 10 ||
          (commands.data?.length ?? 0) > 10 ? (
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setShowAllHistory((shown) => !shown)}
            >
              {showAllHistory ? "Thu gọn" : "Xem thêm"}
            </Button>
          ) : null}
        </div>
        <div className="grid gap-5 xl:grid-cols-2">
          <HistoryCard title="Điện áp & dòng điện" icon={Gauge}>
            {recentReadings?.length ? (
              recentReadings.map((item) => (
                <div
                  key={item.id}
                  className="flex items-center justify-between gap-3 border-b py-3 last:border-0"
                >
                  <span className="tabular-nums">
                    {item.voltage_v ?? "—"} V · {item.current_a ?? "—"} A
                  </span>
                  <span className="text-xs text-muted-foreground">
                    {new Date(item.recorded_at).toLocaleString("vi-VN")}
                  </span>
                </div>
              ))
            ) : (
              <p className="text-sm text-muted-foreground">Chưa có dữ liệu.</p>
            )}
          </HistoryCard>
          <HistoryCard title="Lệnh điều khiển" icon={Clock3}>
            {recentCommands?.length ? (
              recentCommands.map((item) => (
                <div
                  key={item.command_id}
                  className="flex items-center justify-between gap-3 border-b py-3 last:border-0"
                >
                  <span>
                    {item.desired_state ? "Bật" : "Tắt"} ·{" "}
                    {commandStatusLabel(item.status)}
                  </span>
                  <span className="text-xs text-muted-foreground">
                    {new Date(item.requested_at).toLocaleString("vi-VN")}
                  </span>
                </div>
              ))
            ) : (
              <p className="text-sm text-muted-foreground">Chưa có lệnh.</p>
            )}
          </HistoryCard>
        </div>
      </section>
    </div>
  );
}

function Info({ label, value }: { label: string; value: string }) {
  return (
    <Card>
      <CardContent className="p-4">
        <p className="text-xs text-muted-foreground">{label}</p>
        <p className="mt-1 text-2xl font-semibold tabular-nums">{value}</p>
      </CardContent>
    </Card>
  );
}
function HistoryCard({
  title,
  icon: Icon,
  children,
}: {
  title: string;
  icon: typeof Clock3;
  children: React.ReactNode;
}) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Icon className="size-5 text-primary" />
          {title}
        </CardTitle>
      </CardHeader>
      <CardContent>{children}</CardContent>
    </Card>
  );
}
function TextField({
  id,
  label,
  value,
  onChange,
}: {
  id: string;
  label: string;
  value: string;
  onChange: (value: string) => void;
}) {
  return (
    <div>
      <Label htmlFor={id}>{label}</Label>
      <Input
        id={id}
        className="mt-1"
        value={value}
        onChange={(event) => onChange(event.target.value)}
        required
      />
    </div>
  );
}
