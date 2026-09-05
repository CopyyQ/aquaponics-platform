import { useMutation, useQuery } from "@tanstack/react-query";
import { AlertTriangle, BatteryCharging, Download, RefreshCw } from "lucide-react";
import { Link, useSearchParams } from "react-router-dom";
import { energyMonitorApi } from "@/entities/energy-monitor/api/energy-monitor-api";
import { deviceApi } from "@/entities/device/api/device-api";
import type { EnergyMeasurement } from "@/entities/energy-monitor/model/types";
import { monitoringExpectedInterval, monitoringRangeLabel, monitoringRanges, parseMonitoringRange } from "@/entities/telemetry/lib/monitoring-range";
import { useProtectedQueryScope } from "@/features/auth/model/use-protected-query-scope";
import { queryKeys } from "@/shared/api/query-keys";
import { formatDateTime, formatRelative } from "@/shared/lib/date";
import { downloadBlob } from "@/shared/lib/download";
import { TimeSeriesChart } from "@/shared/charts/time-series";
import { Alert, AlertDescription, AlertTitle } from "@/shared/ui/alert";
import { Badge } from "@/shared/ui/badge";
import { Button } from "@/shared/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/shared/ui/card";
import { EmptyState } from "@/shared/ui/empty-state";
import { Skeleton } from "@/shared/ui/skeleton";
import { ToggleGroup, ToggleGroupItem } from "@/shared/ui/toggle-group";

const measurementOrder = ["output_voltage", "input_voltage", "load_current", "input_current", "power", "energy_total"] as const;

function value(value: number | null, unit: string) {
  return value === null ? "—" : `${new Intl.NumberFormat("vi-VN", { maximumFractionDigits: 2 }).format(value)} ${unit}`;
}

function energyValue(valueWh: number | null) {
  if (valueWh === null) return "—";
  return valueWh >= 1_000
    ? `${new Intl.NumberFormat("vi-VN", { maximumFractionDigits: 3 }).format(valueWh / 1_000)} kWh`
    : `${new Intl.NumberFormat("vi-VN", { maximumFractionDigits: 2 }).format(valueWh)} Wh`;
}

function MeasurementCard({ measurement, projectId, deviceId }: { measurement: EnergyMeasurement; projectId: number; deviceId: number }) {
  const invalid = measurement.quality === "OUT_OF_RANGE" || measurement.quality === "INVALID";
  const display = invalid ? measurement.raw_value : measurement.display_value;
  return <Card className={invalid ? "border-destructive/50" : undefined}><CardHeader className="pb-2"><div className="flex items-start justify-between gap-2"><CardTitle className="text-base">{measurement.name}</CardTitle><Badge variant={invalid ? "destructive" : measurement.freshness === "FRESH" ? "success" : "warning"}>{invalid ? "Ngoài miền hợp lệ" : measurement.freshness === "FRESH" ? "Dữ liệu mới" : measurement.freshness === "STALE" ? "Dữ liệu cũ" : "Chưa có dữ liệu"}</Badge></div><CardDescription>{measurement.model_code} · {measurement.sensor_code ?? "Chưa materialize Sensor"}</CardDescription></CardHeader><CardContent className="flex flex-col gap-2"><p className={invalid ? "text-2xl font-semibold text-destructive" : "text-2xl font-semibold"}>{measurement.model_code === "ENERGY_TOTAL_WH" ? energyValue(display) : value(display, measurement.unit)}</p><p className="text-xs text-muted-foreground">Ghi nhận: {formatDateTime(measurement.recorded_at)}<br />Nhận tại server: {formatDateTime(measurement.received_at)}</p>{measurement.quality_reason ? <p className="text-xs text-destructive">{measurement.quality_reason}</p> : null}{measurement.sensor_id ? <Link className="text-sm font-medium text-primary hover:underline" to={`/admin/projects/${projectId}/devices/${deviceId}/sensors/${measurement.sensor_id}`}>Xem chi tiết cảm biến</Link> : null}</CardContent></Card>;
}

export function EnergyMonitorDashboard({ projectId, deviceId, projectName }: { projectId: number; deviceId: number; projectName?: string }) {
  const { active, queryScope } = useProtectedQueryScope();
  const [params, setParams] = useSearchParams();
  const range = parseMonitoringRange(params.get("range"));
  const overview = useQuery({ queryKey: queryKeys.energyMonitor.overview(queryScope, projectId, deviceId), queryFn: () => energyMonitorApi.overview(projectId, deviceId), enabled: active, staleTime: 30_000, refetchInterval: 30_000 });
  const series = useQuery({ queryKey: queryKeys.energyMonitor.powerSeries(queryScope, projectId, deviceId, range), queryFn: () => energyMonitorApi.powerSeries(projectId, deviceId, range), enabled: active, staleTime: range === "1h" ? 60_000 : 180_000 });
  const configDownload = useMutation({ mutationFn: () => deviceApi.downloadMqttConfig(projectId, deviceId), onSuccess: ({ blob, filename }) => downloadBlob(blob, filename) });
  if (overview.isLoading) return <div className="grid gap-4"><Skeleton className="h-40" /><Skeleton className="h-64" /></div>;
  if (overview.isError || !overview.data) return <EmptyState icon={BatteryCharging} title="Không thể tải giám sát năng lượng" description="Thiết bị không thuộc loại giám sát năng lượng hoặc dữ liệu chưa sẵn sàng." action={<Button variant="outline" onClick={() => { void overview.refetch(); }}><RefreshCw data-icon="inline-start" />Thử lại</Button>} />;
  const data = overview.data;
  const setRange = (nextRange: string) => { const next = new URLSearchParams(params); next.set("range", nextRange); setParams(next, { replace: true }); };
  return <section className="flex flex-col gap-5" aria-label="Dashboard thiết bị giám sát năng lượng">
    {!data.device.enabled ? <Alert><AlertTitle>Thiết bị đã vô hiệu hóa</AlertTitle><AlertDescription>Telemetry cũ vẫn được giữ, nhưng trạng thái này không phải lỗi mất kết nối.</AlertDescription></Alert> : null}
    <Card><CardHeader><div className="flex flex-wrap items-start justify-between gap-3"><div><CardTitle className="text-xl">Thiết bị giám sát năng lượng</CardTitle><CardDescription>{data.device.code} · {data.device.template.name}</CardDescription></div><div className="flex gap-2"><Badge variant={data.device.enabled ? "success" : "secondary"}>{data.device.enabled ? "Đang sử dụng" : "Đã vô hiệu hóa"}</Badge><Badge variant={data.device.connectivity === "ONLINE" ? "success" : "warning"}>{data.device.connectivity === "ONLINE" ? "Đang kết nối" : data.device.connectivity === "OFFLINE" ? "Mất kết nối" : "Chờ kết nối"}</Badge></div></div></CardHeader><CardContent className="grid gap-3 text-sm sm:grid-cols-2 xl:grid-cols-4"><p>Dự án: <strong>{projectName ?? `#${projectId}`}</strong></p><p><strong>{data.data_health.expected_measurements} cảm biến · 0 cơ cấu chấp hành</strong></p><p>Điện áp danh định: <strong>{data.device.template.nominal_output_voltage_v ?? "—"} V</strong></p><p>Dữ liệu nhận cuối: <strong>{formatRelative(data.device.last_received_at)}</strong></p><p>Dữ liệu hợp lệ cuối: <strong>{formatRelative(data.device.last_valid_recorded_at)}</strong></p><p>Last seen: <strong>{formatDateTime(data.device.last_seen_at)}</strong></p></CardContent></Card>
    {data.issues.length ? <Card><CardHeader><CardTitle>Vấn đề cần chú ý</CardTitle></CardHeader><CardContent className="flex flex-col gap-2">{data.issues.map((issue) => <Alert key={`${issue.code}-${issue.sensor_id ?? "device"}`} variant={issue.severity === "CRITICAL" ? "destructive" : "default"}><AlertTriangle /><AlertTitle>{issue.severity === "CRITICAL" ? "Nghiêm trọng" : "Cần chú ý"}</AlertTitle><AlertDescription>{issue.message}</AlertDescription></Alert>)}</CardContent></Card> : null}
    <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3" data-testid="energy-monitor-measurements">{measurementOrder.map((key) => <MeasurementCard key={key} measurement={data.measurements[key]} projectId={projectId} deviceId={deviceId} />)}</div>
    <Card><CardHeader><CardTitle>Điện năng tiêu thụ</CardTitle><CardDescription>Server tính từ các đoạn counter ENERGY_TOTAL_WH; counter reset không tạo điện năng âm.</CardDescription></CardHeader><CardContent className="grid gap-3 sm:grid-cols-2 xl:grid-cols-5">{[["1 giờ", data.energy_consumption.last_1h_wh], ["6 giờ", data.energy_consumption.last_6h_wh], ["12 giờ", data.energy_consumption.last_12h_wh], ["24 giờ", data.energy_consumption.last_24h_wh], ["Tháng này", data.energy_consumption.month_to_date_wh]].map(([label, amount]) => <div key={String(label)} className="rounded-lg bg-muted/50 p-3"><p className="text-xs text-muted-foreground">{label}</p><p className="text-xl font-semibold tabular-nums">{energyValue(amount as number | null)}</p></div>)}</CardContent></Card>
    <div className="grid gap-5 xl:grid-cols-12"><Card className="xl:col-span-8"><CardHeader><div className="flex flex-wrap items-center justify-between gap-3"><div><CardTitle>Công suất tiêu thụ</CardTitle><CardDescription>Trung bình các reading POWER_W hợp lệ theo bucket; khoảng trống không được thay bằng 0.</CardDescription></div><ToggleGroup type="single" value={range} onValueChange={(next) => { if (next) setRange(next); }} aria-label="Khoảng thời gian biểu đồ công suất">{monitoringRanges.map((option) => <ToggleGroupItem key={option.value} value={option.value} aria-label={option.longLabel}>{option.label}</ToggleGroupItem>)}</ToggleGroup></div></CardHeader><CardContent>{series.isLoading ? <Skeleton className="h-72" /> : series.isError ? <EmptyState icon={BatteryCharging} title="Không thể tải biểu đồ công suất" description="Vui lòng thử lại." action={<Button variant="outline" onClick={() => { void series.refetch(); }}>Thử lại</Button>} /> : <TimeSeriesChart title="Công suất tiêu thụ" unit="W" currentValue={data.measurements.power.display_value} rangeLabel={monitoringRangeLabel(range)} lastUpdatedAt={data.measurements.power.received_at} expectedIntervalMs={monitoringExpectedInterval(range)} status={data.device.connectivity === "OFFLINE" ? "offline" : data.measurements.power.freshness === "STALE" ? "stale" : "normal"} data={(series.data?.points ?? []).map((point) => ({ timestamp: point.bucket_time, value: point.avg_value }))} />}</CardContent></Card><Card className="xl:col-span-4"><CardHeader><CardTitle>Tình trạng dữ liệu</CardTitle><CardDescription>Reading mới và hợp lệ được theo dõi độc lập.</CardDescription></CardHeader><CardContent className="grid grid-cols-2 gap-3">{[["Phép đo dự kiến", data.data_health.expected_measurements], ["Có dữ liệu mới", data.data_health.fresh_measurements], ["Có dữ liệu hợp lệ", data.data_health.valid_measurements], ["Không hợp lệ", data.data_health.invalid_measurements], ["Chưa có dữ liệu", data.data_health.missing_measurements]].map(([label, count]) => <div key={String(label)} className="rounded-lg bg-muted/50 p-3"><p className="text-xs text-muted-foreground">{label}</p><p className="text-2xl font-semibold">{count}</p></div>)}</CardContent></Card></div>
    <Card><CardHeader><CardTitle>Thông tin cấu hình</CardTitle><CardDescription>{data.device.template.code} · ENERGY_MONITOR · không chứa secret.</CardDescription></CardHeader><CardContent className="flex flex-wrap items-center justify-between gap-3 text-sm"><p>Sensor instance: {measurementOrder.map((key) => data.measurements[key].sensor_code ?? "—").join(", ")}</p><Button variant="outline" disabled={configDownload.isPending} onClick={() => configDownload.mutate()}><Download data-icon="inline-start" />{configDownload.isPending ? "Đang tải…" : "Tải cấu hình JSON"}</Button></CardContent></Card>
  </section>;
}
