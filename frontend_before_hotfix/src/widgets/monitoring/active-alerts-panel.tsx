import { AlertTriangle, BellOff } from "lucide-react"
import type { Alert } from "@/entities/alert/model/types"
import type { Sensor } from "@/entities/sensor/model/types"
import { formatDateTime } from "@/shared/lib/date"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/shared/ui/card"
import { StatusBadge } from "@/shared/ui/status-badge"

interface ActiveAlertsPanelProps {
  alerts: Alert[]
  sensors: Sensor[]
}

export function ActiveAlertsPanel({ alerts, sensors }: ActiveAlertsPanelProps) {
  const activeAlerts = alerts.filter((alert) => alert.status !== "RESOLVED")
  const sensorById = new Map(sensors.map((sensor) => [sensor.id, sensor]))

  return <Card className="h-full shadow-none">
    <CardHeader>
      <CardTitle className="flex items-center gap-2"><AlertTriangle /> Cảnh báo đang hoạt động</CardTitle>
      <CardDescription>Ưu tiên cảnh báo nghiêm trọng và cảm biến mất kết nối.</CardDescription>
    </CardHeader>
    <CardContent className="flex flex-col gap-3">
      {activeAlerts.length ? activeAlerts.slice(0, 6).map((alert) => {
        const sensor = sensorById.get(alert.sensor_id)
        return <div key={alert.id} className="rounded-xl border bg-background p-4">
          <div className="flex flex-wrap items-center gap-2">
            <StatusBadge value={alert.severity} />
            <StatusBadge value={alert.status} />
          </div>
          <div className="mt-3 font-medium">{sensor?.name ?? `Cảm biến #${alert.sensor_id}`}</div>
          <p className="mt-1 text-sm leading-6 text-muted-foreground">{alert.message}</p>
          <div className="mt-3 grid gap-2 text-xs text-muted-foreground sm:grid-cols-2">
            <span>Giá trị: {alert.trigger_value ?? "Không có"}</span>
            <span>Vị trí: {sensor?.description || "Chưa có mô tả"}</span>
            <span className="sm:col-span-2">Thời gian: {formatDateTime(alert.started_at)}</span>
          </div>
        </div>
      }) : <div className="grid min-h-56 place-items-center rounded-xl border border-dashed bg-muted/20 p-6 text-center">
        <div>
          <div className="mx-auto grid size-11 place-items-center rounded-full bg-primary/10 text-primary"><BellOff /></div>
          <div className="mt-3 font-semibold">Không có cảnh báo cần xử lý</div>
          <p className="mt-1 text-sm text-muted-foreground">Các cảnh báo mới sẽ xuất hiện tại đây khi vượt ngưỡng hoặc mất kết nối.</p>
        </div>
      </div>}
    </CardContent>
  </Card>
}
