import { formatDistanceToNow } from "date-fns"
import { vi } from "date-fns/locale"

export const VIETNAM_TIME_ZONE = "Asia/Ho_Chi_Minh"

const vietnamDateTimeFormatter = new Intl.DateTimeFormat("vi-VN", {
  timeZone: VIETNAM_TIME_ZONE,
  day: "2-digit",
  month: "2-digit",
  year: "numeric",
  hour: "2-digit",
  minute: "2-digit",
  second: "2-digit",
  hour12: false,
})

const vietnamTimeFormatter = new Intl.DateTimeFormat("vi-VN", {
  timeZone: VIETNAM_TIME_ZONE,
  hour: "2-digit",
  minute: "2-digit",
  hour12: false,
})

export function formatDateTime(value?: string | null) {
  if (!value) return "Chưa có dữ liệu"
  const parts = Object.fromEntries(vietnamDateTimeFormatter.formatToParts(new Date(value)).filter((part) => part.type !== "literal").map((part) => [part.type, part.value]))
  return `${parts.day}/${parts.month}/${parts.year} ${parts.hour}:${parts.minute}:${parts.second}`
}

export function formatVietnamTime(value?: string | null) {
  if (!value) return "—"
  return vietnamTimeFormatter.format(new Date(value))
}

export function formatRelative(value?: string | null) {
  if (!value) return "Chưa kết nối"
  return formatDistanceToNow(new Date(value), { addSuffix: true, locale: vi })
}
