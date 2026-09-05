import { Badge } from "@/shared/ui/badge"

const labels: Record<string, string> = {
  ONLINE: "Trực tuyến", OFFLINE: "Ngoại tuyến", WAITING_CONNECTION: "Chờ kết nối", DISABLED: "Đã vô hiệu hóa",
  ACTIVE: "Đang hoạt động", PENDING: "Đang chờ", OPEN: "Đang mở", ACKNOWLEDGED: "Đã xác nhận", RESOLVED: "Đã khắc phục",
  ADMIN: "Quản trị viên", OWNER: "Chủ hệ thống", VIEWER: "Người xem", WARNING: "Cảnh báo", CRITICAL: "Nghiêm trọng", LOCKED: "Đã khóa", SOFT_DELETED: "Đã xóa mềm",
}

export function StatusBadge({ value }: { value: string }) {
  const variant = value === "ONLINE" || value === "ACTIVE" || value === "RESOLVED" ? "success" : value === "OFFLINE" || value === "CRITICAL" ? "destructive" : value === "WAITING_CONNECTION" || value === "PENDING" || value === "OPEN" ? "warning" : "secondary"
  return <Badge variant={variant}>{labels[value] ?? value}</Badge>
}
