import type { AuditLog } from "@/entities/audit/model/types"

export const auditActionLabels: Record<string, string> = {
  DISABLE_USER: "Vô hiệu hóa tài khoản", ACTIVATE_USER: "Kích hoạt tài khoản",
  LOCK_USER: "Khóa tài khoản", UNLOCK_USER: "Mở khóa tài khoản",
  SOFT_DELETE_USER: "Xóa mềm tài khoản", RESTORE_USER: "Khôi phục tài khoản",
  FORCE_LOGOUT_USER: "Thu hồi phiên đăng nhập",
  SET_USER_DISABLED: "Vô hiệu hóa tài khoản", SET_USER_ACTIVE: "Kích hoạt tài khoản",
  SET_USER_LOCKED: "Khóa tài khoản", SET_USER_UNLOCKED: "Mở khóa tài khoản",
  CREATE_PROJECT: "Tạo dự án", UPDATE_PROJECT: "Cập nhật dự án",
  DISABLE_PROJECT: "Vô hiệu hóa dự án", ACTIVATE_PROJECT: "Kích hoạt dự án",
  CREATE_DEVICE_FROM_TEMPLATE: "Thêm thiết bị vào dự án",
  CREATE_SENSOR_FROM_MODEL: "Thêm cảm biến vào thiết bị",
  RESET_USER_PASSWORD: "Đặt lại mật khẩu", UPDATE_USER_ROLE: "Thay đổi vai trò",
  ADMIN_SET_USER_PASSWORD: "Quản trị viên đặt lại mật khẩu",
  CREATE_USER: "Tạo tài khoản", UPDATE_USER: "Cập nhật tài khoản",
  CREATE_DEVICE: "Tạo thiết bị", CREATE_SENSOR: "Thêm cảm biến",
  UPDATE_SENSOR_THRESHOLDS: "Sửa ngưỡng cảm biến", CHANGE_PASSWORD: "Đổi mật khẩu",
  PROJECT_CREATED: "Tạo dự án", PROJECT_UPDATED: "Cập nhật dự án",
  PROJECT_DISABLED: "Vô hiệu hóa dự án", PROJECT_ENABLED: "Kích hoạt lại dự án",
  DEVICE_ADDED: "Thêm thiết bị", DEVICE_UPDATED: "Cập nhật thiết bị",
  DEVICE_DISABLED: "Vô hiệu hóa thiết bị", DEVICE_ENABLED: "Kích hoạt thiết bị",
  SENSOR_ADDED: "Thêm cảm biến", SENSOR_UPDATED: "Cập nhật cảm biến",
  SENSOR_DISABLED: "Vô hiệu hóa cảm biến", SENSOR_ENABLED: "Kích hoạt cảm biến",
  ACTUATOR_COMMAND_REQUESTED: "Yêu cầu lệnh điều khiển",
  SCADA_LAYOUT_UPDATED: "Lưu sơ đồ vận hành", SCADA_LAYOUT_PUBLISHED: "Xuất bản sơ đồ vận hành",
  MEMBER_ADDED: "Thêm thành viên", MEMBER_UPDATED: "Cập nhật thành viên", MEMBER_REMOVED: "Xóa thành viên",
  NOTIFICATION_SETTINGS_UPDATED: "Cập nhật cấu hình thông báo",
  NOTIFICATION_RECIPIENT_ADDED: "Thêm người nhận thông báo",
  NOTIFICATION_RECIPIENT_UPDATED: "Cập nhật người nhận thông báo",
  NOTIFICATION_RECIPIENT_ENABLED: "Bật người nhận thông báo",
  NOTIFICATION_RECIPIENT_DISABLED: "Tắt người nhận thông báo",
  NOTIFICATION_RECIPIENT_REMOVED: "Xóa người nhận thông báo",
  REMOTE_MONITORING_ENABLED: "Bật theo dõi từ xa", REMOTE_MONITORING_DISABLED: "Tắt theo dõi từ xa",
  ALERT_RESOLVED: "Xác nhận đã khắc phục cảnh báo",
}

export const auditEntityLabels: Record<string, string> = {
  USER: "Người dùng", PROJECT: "Dự án", DEVICE: "Thiết bị", SENSOR: "Cảm biến",
  ALERT: "Cảnh báo", DEVICE_TEMPLATE: "Mẫu thiết bị", SENSOR_MODEL: "Mẫu cảm biến",
  ACTUATOR: "Cơ cấu chấp hành", SCADA: "Sơ đồ vận hành", MEMBER: "Thành viên",
  NOTIFICATION: "Thông báo", REMOTE_MONITORING: "Theo dõi từ xa",
}

const statusLabels: Record<string, string> = { ACTIVE: "Đang hoạt động", DISABLED: "Vô hiệu hóa", LOCKED: "Đang bị khóa", ARCHIVED: "Đã lưu trữ" }

export function formatAuditDetail(log: Pick<AuditLog, "old_data" | "new_data" | "description">): string {
  const oldStatus = typeof log.old_data?.old_status === "string" ? log.old_data.old_status : typeof log.old_data?.status === "string" ? log.old_data.status : undefined
  const newStatus = typeof log.new_data?.new_status === "string" ? log.new_data.new_status : typeof log.new_data?.status === "string" ? log.new_data.status : undefined
  const reason = typeof log.new_data?.reason === "string" ? log.new_data.reason : undefined
  if (oldStatus && newStatus) return `Từ: ${statusLabels[oldStatus] ?? oldStatus} · Sang: ${statusLabels[newStatus] ?? newStatus}${reason ? ` · Lý do: ${reason}` : ""}`
  if (newStatus) return `Trạng thái mới: ${statusLabels[newStatus] ?? newStatus}${reason ? ` · Lý do: ${reason}` : ""}`
  return log.description || "Đã cập nhật thông tin"
}
