import type { ScadaConnectivity, ScadaFreshness, ScadaQuality } from "./types"

export interface ScadaStateInput { lifecycle?: "ENABLED" | "DISABLED"; connectivity?: ScadaConnectivity; freshness?: ScadaFreshness; quality?: ScadaQuality; desiredState?: boolean | null; reportedState?: boolean | null; commandStatus?: string | null; alertSeverity?: "CRITICAL" | "HIGH" | "WARNING" | "INFO" | null }
export interface ScadaVisualState { primaryState: string; severity: "NONE" | "INFO" | "WARNING" | "HIGH" | "CRITICAL"; label: string; animated: boolean; reasons: string[] }

export function resolveScadaVisualState(input: ScadaStateInput): ScadaVisualState {
  const reasons: string[] = []
  if (input.lifecycle === "DISABLED") return { primaryState: "DISABLED", severity: "INFO", label: "Đã vô hiệu hóa", animated: false, reasons: ["Thiết bị không tham gia vận hành."] }
  if (input.alertSeverity === "CRITICAL") return { primaryState: "CRITICAL", severity: "CRITICAL", label: "Nghiêm trọng", animated: true, reasons: ["Có cảnh báo nghiêm trọng."] }
  if (input.connectivity === "OFFLINE") return { primaryState: "DISCONNECTED", severity: "HIGH", label: "Mất kết nối", animated: false, reasons: ["Không nhận được kết nối thiết bị."] }
  if (input.commandStatus === "TIMEOUT" || input.commandStatus === "FAILED") return { primaryState: input.commandStatus, severity: "HIGH", label: input.commandStatus === "TIMEOUT" ? "Lệnh quá thời gian" : "Lệnh thất bại", animated: false, reasons: ["Thiết bị chưa xác nhận lệnh."] }
  if (input.desiredState !== null && input.desiredState !== undefined && input.reportedState !== null && input.reportedState !== undefined && input.desiredState !== input.reportedState) return { primaryState: "OUT_OF_SYNC", severity: "WARNING", label: "Chưa đồng bộ", animated: false, reasons: ["Trạng thái mong muốn khác trạng thái báo cáo."] }
  if (input.quality === "OUT_OF_RANGE" || input.quality === "INVALID") return { primaryState: "INVALID", severity: "WARNING", label: "Dữ liệu không hợp lệ", animated: false, reasons: ["Giá trị cần được kiểm tra."] }
  if (input.freshness === "STALE") return { primaryState: "STALE", severity: "WARNING", label: "Dữ liệu cũ", animated: false, reasons: ["Dữ liệu mới nhất đã quá ngưỡng tươi."] }
  if (input.freshness === "NO_DATA") return { primaryState: "NO_DATA", severity: "INFO", label: "Chưa có dữ liệu", animated: false, reasons: ["Cảm biến chưa gửi dữ liệu."] }
  if (input.connectivity === "WAITING_CONNECTION") return { primaryState: "WAITING_CONNECTION", severity: "INFO", label: "Đang chờ kết nối", animated: false, reasons: ["Thiết bị chưa kết nối."] }
  return { primaryState: "NORMAL", severity: "NONE", label: "Bình thường", animated: false, reasons }
}
