import axios from "axios"

const configuredBase = import.meta.env.VITE_API_BASE_URL?.trim() || "/api/v1"
export const apiBaseUrl = configuredBase.endsWith("/api/v1") ? configuredBase : `${configuredBase.replace(/\/$/, "")}/api/v1`

export const api = axios.create({ baseURL: apiBaseUrl, timeout: 20_000 })

api.interceptors.request.use((config) => {
  const token = localStorage.getItem("aquaponics_access_token")
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem("aquaponics_access_token")
      window.dispatchEvent(new Event("aquaponics-auth-expired"))
    }
    return Promise.reject(error)
  },
)

export function errorMessage(error: unknown): string {
  if (axios.isAxiosError(error)) {
    const status = error.response?.status
    const detail = error.response?.data?.detail
    if (typeof detail === "string") return detail
    if (detail && typeof detail.detail === "string") return detail.detail
    if (Array.isArray(detail)) {
      const fields = detail.map((item) => item?.loc?.at?.(-1)).filter((item): item is string => Boolean(item))
      if (fields.length) return `Dữ liệu không hợp lệ: ${fields.join(", ")}`
    }
    if (status === 403) return "Bạn không có quyền thực hiện thao tác này."
    if (status === 404) return "Không tìm thấy tài nguyên yêu cầu."
    if (status === 409) return "Thao tác xung đột với dữ liệu hiện tại."
    if (status === 422) return "Dữ liệu gửi lên không hợp lệ."
    if (status && status >= 500) return "Dịch vụ đang gặp sự cố. Vui lòng thử lại sau."
    if (error.code === "ECONNABORTED") return "Yêu cầu quá thời gian chờ."
  }
  return "Không thể hoàn tất yêu cầu."
}
