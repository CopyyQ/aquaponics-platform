import axios from "axios"

type ErrorPayload = {
  code?: unknown
  current_role?: unknown
  detail?: unknown
  message?: unknown
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null
}

function asPayload(value: unknown): ErrorPayload | undefined {
  return isRecord(value) ? value : undefined
}

export function formatBackendErrorPayload(
  data: unknown,
  fallback: string,
): string {
  const response = asPayload(data)
  const nested = asPayload(response?.detail)
  const code = nested?.code ?? response?.code
  const currentRole = nested?.current_role ?? response?.current_role
  const backendDetail = nested?.detail ?? response?.detail
  const backendMessage = nested?.message ?? response?.message
  const message = typeof backendDetail === "string" ? backendDetail : typeof backendMessage === "string" ? backendMessage : undefined

  const parts = [
    typeof code === "string" ? `code: ${code}` : undefined,
    typeof currentRole === "string"
      ? `current_role: ${currentRole}`
      : undefined,
    message,
  ].filter((part): part is string => Boolean(part))

  return parts.length > 0 ? parts.join(" • ") : fallback
}

export function formatBackendError(
  error: unknown,
  fallback: string,
): string {
  if (!axios.isAxiosError(error)) return fallback
  return formatBackendErrorPayload(error.response?.data, fallback)
}

export function formatResourceLoadError(
  error: unknown,
  resourceName: string,
): string {
  if (!axios.isAxiosError(error) || !error.response) {
    return "Không thể kết nối Backend."
  }
  const status = error.response.status
  if (status === 401) return "Phiên đăng nhập đã hết hạn."
  if (status === 403) return `Bạn không có quyền truy cập ${resourceName}.`
  if (status === 404) return "Endpoint không tồn tại hoặc route API đang cấu hình sai."
  if (status >= 500) return `Backend gặp lỗi khi tải ${resourceName}.`
  return formatBackendError(error, `Không thể tải ${resourceName}.`)
}
