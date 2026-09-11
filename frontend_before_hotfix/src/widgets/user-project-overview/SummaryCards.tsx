import { BellRing, Cpu, RadioTower, WifiOff } from "lucide-react"
import { Card, CardContent } from "@/shared/ui/card"

type Summary = { total_devices: number; online_devices: number; offline_devices: number; total_sensors: number; open_alerts: number; offline_sensors?: number }

export function SummaryCards({ summary }: { summary: Summary }) {
  const items = [["Thiết bị", summary.total_devices, `${summary.online_devices} trực tuyến`, Cpu], ["Thiết bị ngoại tuyến", summary.offline_devices, "Cần kiểm tra kết nối", WifiOff], ["Cảm biến", summary.total_sensors, summary.offline_sensors === undefined ? "Theo các Project hoạt động" : `${summary.offline_sensors} ngoại tuyến`, RadioTower], ["Cảnh báo đang mở", summary.open_alerts, "Cần được xử lý", BellRing]] as const
  return <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">{items.map(([label, value, helper, Icon]) => <Card key={label}><CardContent className="flex items-start justify-between p-5"><div className="flex flex-col gap-1"><span className="text-sm text-muted-foreground">{label}</span><strong className="text-3xl">{value}</strong><span className="text-xs text-muted-foreground">{helper}</span></div><div className="rounded-xl bg-primary/10 p-3 text-primary"><Icon /></div></CardContent></Card>)}</div>
}
