import { formatDistanceToNow } from "date-fns"
import { vi } from "date-fns/locale"

export const VIETNAM_TIME_ZONE = "Asia/Ho_Chi_Minh"

const hasExplicitZone = (value: string) => /(?:Z|[+-]\d{2}:?\d{2})$/i.test(value)

export function parseApiDate(value: string) {
  const normalized = hasExplicitZone(value) ? value : `${value}Z`
  return new Date(normalized)
}

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
  const parts = Object.fromEntries(vietnamDateTimeFormatter.formatToParts(parseApiDate(value)).filter((part) => part.type !== "literal").map((part) => [part.type, part.value]))
  return `${parts.day}/${parts.month}/${parts.year} ${parts.hour}:${parts.minute}:${parts.second}`
}

export function formatVietnamTime(value?: string | null) {
  if (!value) return "—"
  return vietnamTimeFormatter.format(parseApiDate(value))
}

export function formatRelative(value?: string | null) {
  if (!value) return "Chưa kết nối"
  return formatDistanceToNow(parseApiDate(value), { addSuffix: true, locale: vi })
}
