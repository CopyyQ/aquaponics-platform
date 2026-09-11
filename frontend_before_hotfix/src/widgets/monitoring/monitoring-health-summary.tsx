import { AlertTriangle, CheckCircle2, Router, WifiOff } from "lucide-react"
import type { Alert } from "@/entities/alert/model/types"
import type { Device } from "@/entities/device/model/types"
import type { Sensor } from "@/entities/sensor/model/types"
import { formatDateTime } from "@/shared/lib/date"
import { Card, CardContent } from "@/shared/ui/card"
import { StatusBadge } from "@/shared/ui/status-badge"

interface MonitoringHealthSummaryProps {
  devices: Device[]
  sensors: Sensor[]
  alerts: Alert[]
  latestReceivedAt: string | null
}

export function MonitoringHealthSummary({ devices, sensors, alerts, latestReceivedAt }: MonitoringHealthSummaryProps) {
  const activeAlerts = alerts.filter((alert) => alert.status !== "RESOLVED")
  const criticalAlerts = activeAlerts.filter((alert) => alert.severity === "CRITICAL")
  const offlineDevices = devices.filter((device) => device.status === "OFFLINE")
  const offlineSensors = sensors.filter((sensor) => sensor.status === "OFFLINE")
  const hasCriticalState = criticalAlerts.length > 0 || offlineDevices.length > 0

  return <Card className="overflow-hidden border-none bg-primary text-primary-foreground shadow-none">
    <CardContent className="grid gap-5 p-5 lg:grid-cols-[1.1fr_0.9fr]">
      <div className="flex gap-4">
        <div className="grid size-12 shrink-0 place-items-center rounded-xl bg-white/12">
          {hasCriticalState ? <AlertTriangle /> : <CheckCircle2 />}
        </div>
        <div>
          <div className="text-sm text-primary-foreground/75">Trạng thái trạm quan trắc</div>
          <h2 className="mt-1 text-2xl font-semibold">{hasCriticalState ? "Cần kiểm tra vận hành" : "Hệ thống đang ổn định"}</h2>
          <p className="mt-2 max-w-2xl text-sm leading-6 text-primary-foreground/75">
            {criticalAlerts.length} cảnh báo nghiêm trọng, {offlineDevices.length} gateway ngoại tuyến và {offlineSensors.length} cảm biến mất kết nối.
          </p>
        </div>
      </div>
      <div className="grid gap-3 sm:grid-cols-3 lg:grid-cols-1 xl:grid-cols-3">
        <div className="rounded-xl bg-white/10 p-4">
          <div className="flex items-center gap-2 text-xs text-primary-foreground/70"><Router /> Gateway</div>
          <div className="mt-2 font-semibold">{devices.filter((device) => device.status === "ONLINE").length}/{devices.length} trực tuyến</div>
        </div>
        <div className="rounded-xl bg-white/10 p-4">
          <div className="flex items-center gap-2 text-xs text-primary-foreground/70"><WifiOff /> MQTT</div>
          <div className="mt-2"><StatusBadge value={offlineDevices.length ? "OFFLINE" : "ONLINE"} /></div>
        </div>
        <div className="rounded-xl bg-white/10 p-4">
          <div className="text-xs text-primary-foreground/70">Telemetry mới nhất</div>
          <div className="mt-2 text-sm font-semibold">{formatDateTime(latestReceivedAt)}</div>
        </div>
      </div>
    </CardContent>
  </Card>
}
