import { AlertTriangle, CheckCircle2, RefreshCw } from "lucide-react"
import { Link } from "react-router-dom"
import type { CoreId, MonitoringDevice, ProjectMonitoringSummary } from "@/entities/telemetry/model/project-monitoring"
import type { MonitoringDialogTab } from "@/features/view-device-monitoring-history/model/monitoring-dialog.types"
import { formatDateTime, formatRelative } from "@/shared/lib/date"
import { Alert, AlertDescription, AlertTitle } from "@/shared/ui/alert"
import { Badge } from "@/shared/ui/badge"
import { Button } from "@/shared/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/shared/ui/card"
import { EmptyState } from "@/shared/ui/empty-state"
import { PageHeader } from "@/shared/ui/page-header"
import { ProjectDeviceMonitoringCard } from "@/widgets/project-device-monitoring/ProjectDeviceMonitoringCard"

const statusLabel: Record<string, string> = { HEALTHY: "Ổn định", WARNING: "Cần chú ý", CRITICAL: "Nghiêm trọng", NO_DATA: "Chưa có dữ liệu" }

interface ProjectMonitoringViewProps {
  project: { code: string; name?: string; location: string | null }
  summary: ProjectMonitoringSummary
  devices: MonitoringDevice[]
  mode: "admin" | "public-readonly"
  isRefetching: boolean
  onRefresh: () => void
  onOpenMonitoring?: (deviceId: CoreId, tab: MonitoringDialogTab, resourceId?: CoreId) => void
}

export function ProjectMonitoringView({ project, summary, devices, mode, isRefetching, onRefresh, onOpenMonitoring }: ProjectMonitoringViewProps) {
  const publicMode = mode === "public-readonly"
  const { health, inventory } = summary
  return <div className="flex min-w-0 flex-col gap-6">
    <PageHeader
      title={publicMode ? project.name ?? "Giám sát dự án" : "Giám sát dự án"}
      description={`${project.code} · ${project.location || "Chưa có địa điểm"}`}
      actions={<div className="flex flex-wrap gap-2">
        <Button variant="outline" onClick={onRefresh} aria-label="Làm mới dữ liệu"><RefreshCw data-icon="inline-start" />Làm mới</Button>
        {!publicMode ? <><Link to="../overview" className="inline-flex items-center rounded-md border px-3 py-2 text-sm font-medium hover:bg-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring">Xem tổng quan</Link><Link to="../devices" className="inline-flex items-center rounded-md border px-3 py-2 text-sm font-medium hover:bg-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring">Quản lý thiết bị</Link></> : <Badge variant="secondary">Chỉ đọc</Badge>}
      </div>}
    />
    {isRefetching ? <Alert aria-live="polite"><AlertTitle>Đang làm mới dữ liệu</AlertTitle><AlertDescription>Dữ liệu hiện tại vẫn được giữ lại.</AlertDescription></Alert> : null}
    <Card className={health.status === "CRITICAL" ? "border-destructive/50" : health.status === "WARNING" ? "border-amber-500/40" : "border-primary/30"}><CardContent className="grid gap-5 p-5 lg:grid-cols-[1.3fr_1fr]"><div><div className="flex items-center gap-3"><div className="grid size-11 place-items-center rounded-xl bg-primary/10 text-primary">{health.status === "HEALTHY" ? <CheckCircle2 aria-hidden="true" /> : <AlertTriangle aria-hidden="true" />}</div><div><p className="text-sm text-muted-foreground">Tình trạng vận hành</p><h2 className="text-2xl font-semibold">{statusLabel[health.status]}</h2></div></div><ul className="mt-4 flex flex-col gap-2 text-sm text-muted-foreground">{health.reasons.length ? health.reasons.map((reason) => <li key={reason.code}>• {reason.message}</li>) : <li>Không có vấn đề cần xử lý.</li>}</ul></div><div className="grid grid-cols-2 gap-3 sm:grid-cols-4 lg:grid-cols-2"><Metric label="Thiết bị" value={`${inventory.devices_online}/${inventory.devices_enabled}`} detail="đang trực tuyến" /><Metric label="Cảm biến" value={`${inventory.sensors_reporting}/${inventory.sensors_enabled}`} detail="đang gửi dữ liệu" /><Metric label="Cảnh báo mở" value={summary.alerts.open_total} detail={`${summary.alerts.critical_open} nghiêm trọng`} /><Metric label="Telemetry cuối" value={formatRelative(summary.freshness.last_received_at)} detail={formatDateTime(summary.freshness.last_received_at)} /></div></CardContent></Card>
    <section className="grid gap-5 xl:grid-cols-[minmax(0,1.1fr)_minmax(320px,0.9fr)]"><Card><CardHeader><CardTitle>Cần chú ý</CardTitle><CardDescription>Các mục được ưu tiên theo mức độ xử lý.</CardDescription></CardHeader><CardContent className="flex flex-col gap-3">{summary.attention.length ? summary.attention.map((item) => <div key={item.id} className="rounded-lg border p-4"><div className="flex flex-wrap items-center gap-2"><Badge variant={item.severity === "CRITICAL" ? "destructive" : "warning"}>{item.severity === "CRITICAL" ? "Nghiêm trọng" : "Cảnh báo"}</Badge><span className="font-medium">{item.title}</span></div><p className="mt-2 text-sm text-muted-foreground">{item.description}</p><p className="mt-2 text-xs text-muted-foreground">{formatDateTime(item.last_seen_at)}</p></div>) : <p className="rounded-lg border border-dashed p-6 text-center text-sm text-muted-foreground">Không có vấn đề cần xử lý.</p>}</CardContent></Card><Card><CardHeader><CardTitle>Độ phủ dữ liệu cảm biến</CardTitle><CardDescription>Chỉ tính Sensor đang bật và có reading hợp lệ.</CardDescription></CardHeader><CardContent className="flex flex-col gap-4"><div className="text-3xl font-semibold">{inventory.sensors_reporting}/{inventory.sensors_enabled}</div><div className="text-sm text-muted-foreground">{inventory.sensors_offline} ngoại tuyến · {inventory.sensors_stale} dữ liệu cũ</div><div className="h-2 overflow-hidden rounded-full bg-muted" role="progressbar" aria-label="Độ phủ dữ liệu cảm biến" aria-valuemin={0} aria-valuemax={100} aria-valuenow={Math.round(summary.freshness.coverage_ratio * 100)}><div className="h-full rounded-full bg-primary" style={{ width: `${Math.round(summary.freshness.coverage_ratio * 100)}%` }} /></div><p className="text-sm text-muted-foreground">Dữ liệu mới nhất: {formatDateTime(summary.freshness.last_received_at)}</p></CardContent></Card></section>
    <Card><CardHeader><CardTitle>Giá trị cảm biến mới nhất</CardTitle><CardDescription>Dựa trên inventory thực tế của Project; counter không bị cộng hoặc lấy trung bình.</CardDescription></CardHeader><CardContent><div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">{summary.measurement_groups.map((group) => <div key={group.model_code} className="rounded-lg border p-4"><div className="flex items-start justify-between gap-2"><div><p className="font-medium">{group.name}</p><p className="text-xs text-muted-foreground">{group.model_code}</p></div><Badge variant={group.stale ? "warning" : "success"}>{group.stale ? "Dữ liệu cũ" : "Đang báo"}</Badge></div><p className="mt-4 text-2xl font-semibold">{group.latest_value === null ? "—" : `${group.latest_value} ${group.unit}`}</p><p className="mt-1 text-xs text-muted-foreground">{group.reporting_sensors}/{group.expected_sensors} Sensor · {formatDateTime(group.latest_at)}</p></div>)}</div>{!summary.measurement_groups.length ? <p className="p-6 text-center text-sm text-muted-foreground">Project chưa có cảm biến.</p> : null}</CardContent></Card>
    <section><div className="mb-3"><h2 className="text-xl font-semibold">Tình trạng thiết bị</h2><p className="text-sm text-muted-foreground">Trạng thái thiết bị và dữ liệu Sensor mới nhất.</p></div>{devices.length ? <div className="flex flex-col gap-4">{devices.map((item) => <ProjectDeviceMonitoringCard key={item.id} device={item} readOnly={publicMode} onOpenMonitoring={onOpenMonitoring ? (tab, resource) => onOpenMonitoring(item.id, tab, resource) : undefined} />)}</div> : <EmptyState icon={AlertTriangle} title="Project chưa có thiết bị" description="Chưa có thiết bị để theo dõi vận hành." />}</section>
    <Card><CardHeader><CardTitle>Cảnh báo gần đây</CardTitle><CardDescription>Open alerts được ưu tiên hiển thị trước.</CardDescription></CardHeader><CardContent className="flex flex-col gap-3">{summary.recent_alerts.length ? summary.recent_alerts.map((alert) => <div key={alert.id} className="flex flex-wrap items-center justify-between gap-3 rounded-lg border p-4"><div><div className="flex flex-wrap items-center gap-2"><Badge variant={alert.severity === "CRITICAL" ? "destructive" : "warning"}>{alert.severity === "CRITICAL" ? "Nghiêm trọng" : "Cảnh báo"}</Badge><span className="font-medium">{alert.sensor_name} · {alert.device_name}</span></div><p className="mt-1 text-sm text-muted-foreground">{alert.message}</p></div><time className="text-xs text-muted-foreground" dateTime={alert.started_at}>{formatDateTime(alert.started_at)}</time></div>) : <p className="rounded-lg border border-dashed p-6 text-center text-sm text-muted-foreground">Không có cảnh báo đang mở.</p>}</CardContent></Card>
  </div>
}

function Metric({ label, value, detail }: { label: string; value: string | number; detail: string }) { return <div className="rounded-lg border bg-muted/20 p-3"><p className="text-xs text-muted-foreground">{label}</p><p className="mt-1 truncate text-lg font-semibold">{value}</p><p className="text-xs text-muted-foreground">{detail}</p></div> }
