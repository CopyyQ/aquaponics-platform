import { useQuery } from "@tanstack/react-query"
import { listActuatorModels, listDeviceTemplates, listSensorModels } from "@/api/resources"

export function CatalogsPage() {
  const templates = useQuery({ queryKey: ["device-templates"], queryFn: listDeviceTemplates })
  const sensorModels = useQuery({ queryKey: ["sensor-models"], queryFn: listSensorModels })
  const actuatorModels = useQuery({ queryKey: ["actuator-models"], queryFn: listActuatorModels })
  return <section className="space-y-5"><h1 className="text-3xl font-bold">Danh mục vận hành</h1><p className="text-muted-foreground">DeviceTemplate, SensorModel và ActuatorModel dùng để tạo các tài nguyên runtime.</p><div className="grid gap-5 lg:grid-cols-3"><Catalog title="DeviceTemplate" loading={templates.isLoading}>{templates.data?.map((item) => <div className="rounded border p-3" key={item.id}><strong>{item.name}</strong><p className="text-sm text-muted-foreground">{item.code} · {item.sensors.length} Sensor slot · {item.actuators.length} Actuator slot</p></div>)}</Catalog><Catalog title="SensorModel" loading={sensorModels.isLoading}>{sensorModels.data?.map((item) => <div className="rounded border p-3" key={item.id}><strong>{item.name}</strong><p className="text-sm text-muted-foreground">{item.code} · {item.unit}</p></div>)}</Catalog><Catalog title="ActuatorModel" loading={actuatorModels.isLoading}>{actuatorModels.data?.map((item) => <div className="rounded border p-3" key={item.id}><strong>{item.name}</strong><p className="text-sm text-muted-foreground">{item.code} · {item.data_type}</p></div>)}</Catalog></div></section>
}

function Catalog({ title, loading, children }: { title: string; loading: boolean; children: React.ReactNode }) {
  return <section className="space-y-2 rounded-xl border bg-card p-4"><h2 className="text-xl font-semibold">{title}</h2>{loading && <p>Đang tải…</p>}{children}</section>
}
