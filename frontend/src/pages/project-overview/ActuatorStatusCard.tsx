import type { ProjectOverviewActuator } from "@/entities/project/model/types"
import {
  actuatorCommandLabel,
  actuatorCurrentLabel,
  electricalFreshnessLabel,
  electricalQualityLabel,
} from "@/entities/actuator/lib/actuator-electrical"
import { formatDateTime } from "@/shared/lib/date"
import { Badge } from "@/shared/ui/badge"

const riskLabel = (risk?: string) =>
  risk === "EXTREME" ? "Cực cao" : risk === "VERY_HIGH" ? "Rất cao" : risk === "HIGH" ? "Cao" : risk === "MEDIUM" ? "Trung bình" : risk === "LOW_MEDIUM" ? "Thấp–trung bình" : risk === "LOW" ? "Thấp" : "Chưa xác định"

const technicalLabel = (severity?: string) => severity === "CRITICAL" ? "Nghiêm trọng" : severity === "WARNING" ? "Cảnh báo" : "Chưa xác định"

const stateLabel = (state: unknown, missing: string) => state === true ? "Bật" : state === false ? "Tắt" : missing

const numberLabel = (value: unknown, unit: string) => typeof value === "number" ? `${value.toLocaleString("vi-VN", { maximumFractionDigits: 3 })} ${unit}` : "Chưa có dữ liệu"

export function incidentDurationLabel(totalSeconds: number): string {
  const safeSeconds = Math.max(0, Math.floor(totalSeconds))
  const days = Math.floor(safeSeconds / 86400)
  const hours = Math.floor((safeSeconds % 86400) / 3600)
  const minutes = Math.floor((safeSeconds % 3600) / 60)
  const seconds = safeSeconds % 60
  return [days ? `${days} ngày` : "", hours ? `${hours} giờ` : "", minutes ? `${minutes} phút` : "", seconds || (!days && !hours && !minutes) ? `${seconds} giây` : ""].filter(Boolean).join(" ")
}

function Info({ label, value }: { label: string; value: string }) {
  return <div><dt className="text-xs text-muted-foreground">{label}</dt><dd className="mt-1 font-medium">{value}</dd></div>
}

export function ActuatorStatusCard({ actuator }: { actuator: ProjectOverviewActuator }) {
  const incident = actuator.active_incident
  const evidence = incident?.evidence ?? {}
  const current = evidence.current_a ?? actuator.electrical.current_a
  const threshold = evidence.threshold ?? evidence.minimum_running_current_a ?? actuator.electrical.minimum_running_current_a
  const desired = evidence.desired_state ?? actuator.desired_state
  const reported = evidence.reported_state ?? actuator.reported_state
  const command = typeof evidence.command_status === "string" ? evidence.command_status : actuator.command_status
  const quality = typeof evidence.quality === "string" ? evidence.quality : actuator.electrical.quality
  const freshness = typeof evidence.freshness === "string" ? evidence.freshness : actuator.electrical.freshness

  return (
    <article className="rounded-lg border p-4" aria-label={`Cơ cấu chấp hành ${actuator.name}`}>
      <div className="flex items-start justify-between gap-3">
        <div><h3 className="font-medium">{actuator.name}</h3><p className="text-xs text-muted-foreground">Thiết bị: {actuator.device_name}</p></div>
        <Badge variant={incident ? "destructive" : actuator.connection_status === "CONNECTED" ? "success" : actuator.connection_status === "DISCONNECTED" ? "destructive" : "warning"}>
          {incident ? riskLabel(incident.business_risk_level) : actuator.connection_status === "CONNECTED" ? "Trực tuyến" : actuator.connection_status === "DISCONNECTED" ? "Mất kết nối" : "Chưa xác định"}
        </Badge>
      </div>
      <dl className="mt-4 grid grid-cols-2 gap-x-4 gap-y-3 text-sm sm:grid-cols-3">
        <Info label="Kết nối" value={actuator.connection_status === "CONNECTED" ? "Trực tuyến" : actuator.connection_status === "DISCONNECTED" ? "Ngoại tuyến" : "Chưa xác định"} />
        <Info label="Trạng thái yêu cầu" value={stateLabel(actuator.desired_state, "Chưa có yêu cầu")} />
        <Info label="Trạng thái báo về" value={stateLabel(actuator.reported_state, "Chưa xác định")} />
        <Info label="Lệnh gần nhất" value={actuatorCommandLabel(actuator.command_status)} />
        <Info label="Đồng bộ" value={actuator.synchronization_status === "IN_SYNC" ? "Đã đồng bộ" : actuator.synchronization_status === "PENDING" ? "Đang chờ phản hồi" : actuator.synchronization_status === "FAILED" ? "Thất bại" : actuator.synchronization_status === "TIMEOUT" ? "Hết thời gian chờ" : "Cần kiểm tra"} />
        <Info label="Dòng điện" value={actuatorCurrentLabel(actuator.electrical)} />
        <Info label="Chất lượng dữ liệu" value={electricalQualityLabel(actuator.electrical.quality)} />
        <Info label="Độ mới dữ liệu" value={electricalFreshnessLabel(actuator.electrical.freshness)} />
        <Info label="Thời gian đo" value={formatDateTime(actuator.electrical.recorded_at)} />
        <Info label="Backend nhận lúc" value={formatDateTime(actuator.electrical.received_at)} />
      </dl>
      <div className={`mt-4 rounded-md p-3 ${incident ? "bg-destructive/10" : "bg-muted/50"}`}>
        <p className="text-xs font-medium uppercase tracking-wide">Kết luận vận hành</p>
        <p className="mt-1 font-medium">{actuator.operational_conclusion.label}</p>
        <p className="mt-1 text-sm text-muted-foreground">{actuator.operational_conclusion.explanation}</p>
      </div>
      {incident ? (
        <section className="mt-4 rounded-md border border-destructive/30 p-3" aria-labelledby={`incident-${incident.id}`}>
          <h4 id={`incident-${incident.id}`} className="font-medium">Điều kiện cảnh báo</h4>
          <p className="mt-1 text-sm text-muted-foreground">{incident.condition_summary}</p>
          <dl className="mt-3 grid grid-cols-2 gap-x-4 gap-y-3 text-sm sm:grid-cols-3">
            <Info label="Dòng điện hiện tại" value={numberLabel(current, "A")} />
            <Info label="Ngưỡng dòng điện" value={numberLabel(threshold, "A")} />
            <Info label="Trạng thái yêu cầu" value={stateLabel(desired, "Chưa xác định")} />
            <Info label="Trạng thái báo về" value={stateLabel(reported, "Chưa xác định")} />
            <Info label="Trạng thái lệnh" value={actuatorCommandLabel(typeof command === "string" ? command : null)} />
            <Info label="Chất lượng dữ liệu" value={electricalQualityLabel(quality)} />
            <Info label="Độ mới dữ liệu" value={electricalFreshnessLabel(freshness)} />
            <Info label="Bắt đầu lúc" value={formatDateTime(incident.started_at)} />
            <Info label="Đã kéo dài" value={incidentDurationLabel(incident.duration_seconds)} />
            <Info label="Mức độ nghiệp vụ" value={riskLabel(incident.business_risk_level)} />
            <Info label="Mức kỹ thuật" value={technicalLabel(incident.technical_severity)} />
            <Info label="Mã sự cố" value={String(incident.id)} />
          </dl>
        </section>
      ) : null}
    </article>
  )
}
