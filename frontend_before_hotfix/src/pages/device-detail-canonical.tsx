import { useState, type FormEvent } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Activity, Cpu, Plus, Radio } from "lucide-react";
import { Link, useParams } from "react-router-dom";
import {
  createActuator,
  createSensor,
  getDevice,
  listActuatorModels,
  listSensorModels,
  queryKeys,
} from "@/api/resources";
import { useAuth } from "@/app/auth";
import type { ActuatorModel, SensorModel } from "@/api/contracts";
import { Button } from "@/shared/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/shared/ui/card";
import { EmptyState } from "@/shared/ui/empty-state";
import { Input } from "@/shared/ui/input";
import { Label } from "@/shared/ui/label";
import { Skeleton } from "@/shared/ui/skeleton";
import { StatusBadge } from "@/shared/ui/status-badge";
import { errorMessage } from "@/api/client";
import { actuatorStateLabel } from "@/entities/actuator/lib/actuator-semantics";

export function DeviceDetailCanonicalPage() {
  const params = useParams();
  const systemId = params.systemId ?? "";
  const deviceId = params.deviceId ?? "";
  const { can } = useAuth();
  const client = useQueryClient();
  const device = useQuery({
    queryKey: queryKeys.device(systemId, deviceId),
    queryFn: () => getDevice(systemId, deviceId),
    enabled: Boolean(systemId && deviceId),
  });
  const sensorModels = useQuery({
    queryKey: queryKeys.sensorModels,
    queryFn: listSensorModels,
    enabled: can("sensors.create"),
  });
  const actuatorModels = useQuery({
    queryKey: queryKeys.actuatorModels,
    queryFn: listActuatorModels,
    enabled: can("actuators.create"),
  });
  const [sensorOpen, setSensorOpen] = useState(false);
  const [actuatorOpen, setActuatorOpen] = useState(false);
  const refresh = () => {
    void client.invalidateQueries({
      queryKey: queryKeys.device(systemId, deviceId),
    });
  };
  if (device.isLoading)
    return (
      <div className="space-y-4">
        <Skeleton className="h-24" />
        <Skeleton className="h-96" />
      </div>
    );
  if (device.isError || !device.data)
    return (
      <EmptyState
        icon={Cpu}
        title="Không thể tải thiết bị"
        description={errorMessage(device.error)}
      />
    );
  const value = device.data;
  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-sm text-muted-foreground">
            <Link
              className="text-primary hover:underline"
              to={`/aquaponics-systems/${systemId}/devices`}
            >
              Thiết bị
            </Link>{" "}
            / {value.code}
          </p>
          <h2 className="mt-1 text-2xl font-semibold">{value.name}</h2>
          <p className="mt-1 text-sm text-muted-foreground">
            {value.description ?? "Không có mô tả"} ·{" "}
            {value.location ?? "Chưa đặt vị trí"}
          </p>
        </div>
        <StatusBadge value={value.status} />
      </div>
      <div className="grid gap-4 sm:grid-cols-3">
        <Info label="Mã Device" value={value.code} />
        <Info label="Cảm biến" value={String(value.sensors.length)} />
        <Info label="Cơ cấu chấp hành" value={String(value.actuators.length)} />
      </div>
      <div className="grid gap-6 xl:grid-cols-2">
        <ResourceCard
          title="Cảm biến"
          icon={Activity}
          action={
            can("sensors.create") ? (
              <Button size="sm" onClick={() => setSensorOpen((open) => !open)}>
                <Plus />
                Thêm Sensor
              </Button>
            ) : null
          }
        >
          {sensorOpen ? (
            <SensorForm
              models={sensorModels.data ?? []}
              onSubmit={async (payload) => {
                await createSensor(systemId, deviceId, payload);
                setSensorOpen(false);
                refresh();
              }}
            />
          ) : null}
          {value.sensors.length ? (
            value.sensors.map((sensor) => (
              <Link
                key={sensor.id}
                className="flex items-center justify-between rounded-xl border p-4 transition-colors hover:border-primary"
                to={`/aquaponics-systems/${systemId}/devices/${deviceId}/sensors/${sensor.id}`}
              >
                <div>
                  <p className="font-medium">{sensor.name}</p>
                  <p className="text-xs text-muted-foreground">
                    {sensor.code} · Model #{sensor.sensor_model_id}
                  </p>
                </div>
                <StatusBadge value={sensor.status} />
              </Link>
            ))
          ) : (
            <EmptyState
              icon={Activity}
              title="Chưa có Sensor"
              description="Tạo Sensor từ một SensorModel đã có."
            />
          )}
        </ResourceCard>
        <ResourceCard
          title="Cơ cấu chấp hành"
          icon={Radio}
          action={
            can("actuators.create") ? (
              <Button
                size="sm"
                onClick={() => setActuatorOpen((open) => !open)}
              >
                <Plus />
                Thêm Actuator
              </Button>
            ) : null
          }
        >
          {actuatorOpen ? (
            <ActuatorForm
              models={actuatorModels.data ?? []}
              onSubmit={async (payload) => {
                await createActuator(systemId, deviceId, payload);
                setActuatorOpen(false);
                refresh();
              }}
            />
          ) : null}
          {value.actuators.length ? (
            value.actuators.map((actuator) => (
                <Link
                  key={actuator.id}
                  className="block rounded-xl border p-4 transition-colors hover:border-primary"
                  to={`/aquaponics-systems/${systemId}/devices/${deviceId}/actuators/${actuator.id}`}
                >
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <p className="font-medium">{actuator.name}</p>
                    <p className="text-xs text-muted-foreground">
                      {actuator.code} ·{" "}
                      {actuator.actuator_model_id
                        ? `Model #${actuator.actuator_model_id}`
                        : "Chưa có model"}
                    </p>
                  </div>
                  <StatusBadge value={value.status} />
                </div>
                <dl className="mt-3 grid grid-cols-3 gap-2 text-sm">
                  <div>
                    <dt className="text-xs text-muted-foreground">
                      Trạng thái
                    </dt>
                    <dd>{actuatorStateLabel(actuator.reported_state)}</dd>
                  </div>
                  <div>
                    <dt className="text-xs text-muted-foreground">Điện áp</dt>
                    <dd className="tabular-nums">
                      {actuator.voltage_v == null
                        ? "—"
                        : `${actuator.voltage_v} V`}
                    </dd>
                  </div>
                  <div>
                    <dt className="text-xs text-muted-foreground">Dòng điện</dt>
                    <dd className="tabular-nums">
                      {actuator.current_a == null
                        ? "—"
                        : `${actuator.current_a} A`}
                    </dd>
                  </div>
                </dl>
              </Link>
            ))
          ) : (
            <EmptyState
              icon={Radio}
              title="Chưa có Actuator"
              description="Tạo Actuator từ một ActuatorModel đã có."
            />
          )}
        </ResourceCard>
      </div>
    </div>
  );
}

function Info({ label, value }: { label: string; value: string }) {
  return (
    <Card>
      <CardContent className="p-4">
        <p className="text-xs text-muted-foreground">{label}</p>
        <p className="mt-1 font-semibold">{value}</p>
      </CardContent>
    </Card>
  );
}
function ResourceCard({
  title,
  icon: Icon,
  action,
  children,
}: {
  title: string;
  icon: typeof Activity;
  action: React.ReactNode;
  children: React.ReactNode;
}) {
  return (
    <Card>
      <CardHeader className="flex-row items-center justify-between">
        <CardTitle className="flex items-center gap-2">
          <Icon className="size-5 text-primary" />
          {title}
        </CardTitle>
        {action}
      </CardHeader>
      <CardContent className="space-y-3">{children}</CardContent>
    </Card>
  );
}
function SensorForm({
  models,
  onSubmit,
}: {
  models: SensorModel[];
  onSubmit: (payload: {
    sensor_model_id: number;
    code: string;
    name: string;
  }) => Promise<void>;
}) {
  const [code, setCode] = useState("");
  const [name, setName] = useState("");
  const [model, setModel] = useState("");
  const submit = (event: FormEvent) => {
    event.preventDefault();
    void onSubmit({
      sensor_model_id: Number(model),
      code: code.trim().toUpperCase(),
      name: name.trim(),
    });
  };
  return (
    <form
      className="grid gap-2 rounded-xl bg-muted p-4 sm:grid-cols-3"
      onSubmit={submit}
    >
      <Label className="sr-only" htmlFor="sensor-code">
        Mã Sensor
      </Label>
      <Input
        id="sensor-code"
        placeholder="Mã Sensor"
        value={code}
        onChange={(event) => setCode(event.target.value)}
        required
      />
      <Label className="sr-only" htmlFor="sensor-name">
        Tên Sensor
      </Label>
      <Input
        id="sensor-name"
        placeholder="Tên Sensor"
        value={name}
        onChange={(event) => setName(event.target.value)}
        required
      />
      <select
        className="h-9 rounded-md border bg-background px-3 text-sm"
        value={model}
        onChange={(event) => setModel(event.target.value)}
        required
      >
        <option value="">Chọn model</option>
        {models.map((item) => (
          <option value={item.id} key={item.id}>
            {item.name}
          </option>
        ))}
      </select>
      <Button className="sm:col-span-3" type="submit">
        Tạo Sensor
      </Button>
    </form>
  );
}
function ActuatorForm({
  models,
  onSubmit,
}: {
  models: ActuatorModel[];
  onSubmit: (payload: {
    actuator_model_id: number;
    code: string;
    name: string;
  }) => Promise<void>;
}) {
  const [code, setCode] = useState("");
  const [name, setName] = useState("");
  const [model, setModel] = useState("");
  const submit = (event: FormEvent) => {
    event.preventDefault();
    void onSubmit({
      actuator_model_id: Number(model),
      code: code.trim().toUpperCase(),
      name: name.trim(),
    });
  };
  return (
    <form
      className="grid gap-2 rounded-xl bg-muted p-4 sm:grid-cols-3"
      onSubmit={submit}
    >
      <Label className="sr-only" htmlFor="actuator-code">
        Mã Actuator
      </Label>
      <Input
        id="actuator-code"
        placeholder="Mã Actuator"
        value={code}
        onChange={(event) => setCode(event.target.value)}
        required
      />
      <Label className="sr-only" htmlFor="actuator-name">
        Tên Actuator
      </Label>
      <Input
        id="actuator-name"
        placeholder="Tên Actuator"
        value={name}
        onChange={(event) => setName(event.target.value)}
        required
      />
      <select
        className="h-9 rounded-md border bg-background px-3 text-sm"
        value={model}
        onChange={(event) => setModel(event.target.value)}
        required
      >
        <option value="">Chọn model</option>
        {models.map((item) => (
          <option value={item.id} key={item.id}>
            {item.name}
          </option>
        ))}
      </select>
      <Button className="sm:col-span-3" type="submit">
        Tạo Actuator
      </Button>
    </form>
  );
}
