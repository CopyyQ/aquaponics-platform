import type { ProjectOverviewActuator } from "@/entities/project/model/types"

export function actuatorCurrentLabel(electrical: ProjectOverviewActuator["electrical"]): string {
  if (!electrical.configured) return "Chưa cấu hình đo dòng điện"
  if (electrical.quality === "INVALID") return "Không hợp lệ"
  if (electrical.current_a === null) return "Không có dữ liệu"
  return `${electrical.current_a.toLocaleString("vi-VN", { maximumFractionDigits: 3 })} A`
}

export function electricalQualityLabel(quality?: string): string {
  if (quality === "VALID") return "Hợp lệ"
  if (quality === "OUT_OF_RANGE") return "Ngoài phạm vi"
  if (quality === "INVALID") return "Không hợp lệ"
  if (quality === "UNVALIDATED") return "Chưa được xác thực"
  return "Không có dữ liệu"
}

export function electricalFreshnessLabel(freshness: string): string {
  return freshness === "FRESH" ? "Mới" : freshness === "STALE" ? "Dữ liệu cũ" : "Không có dữ liệu"
}

export function actuatorCommandLabel(status: string | null): string {
  if (status === "ACKNOWLEDGED") return "Đã xác nhận"
  if (status === "FAILED") return "Thất bại"
  if (status === "TIMEOUT") return "Hết thời gian chờ"
  if (status === "PUBLISHED") return "Đã gửi lệnh"
  if (status === "PENDING") return "Đang chờ gửi"
  return "Chưa có lệnh"
}
