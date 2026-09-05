import axios from "axios"
import { getAccountAuthCode, isAccountAuthError } from "@/shared/api/auth-errors"
import { emitAuthenticationFailure, type AuthenticationFailureCode } from "@/shared/api/auth-events"

export function resolveApiBaseUrl(value: string | undefined) {
  const baseUrl = (value?.trim() || "/api/v1").replace(/\/$/, "")
  return baseUrl.endsWith("/api/v1") ? baseUrl : `${baseUrl}/api/v1`
}

const API_BASE_URL = resolveApiBaseUrl(import.meta.env.VITE_API_BASE_URL)

interface HttpClientOptions {
  getAccessToken?: () => string | null
  onAuthenticationFailure?: (code: AuthenticationFailureCode) => void
}

export function createHttpClient(options: HttpClientOptions = {}) {
  const client = axios.create({ baseURL: API_BASE_URL, timeout: 20000 })
  client.interceptors.request.use((config) => {
    const token = options.getAccessToken?.() ?? (typeof localStorage === "undefined" ? null : localStorage.getItem("aquaponics_access_token"))
    if (token) config.headers.Authorization = `Bearer ${token}`
    return config
  })
  client.interceptors.response.use((response) => response, (error) => {
    const code = getAccountAuthCode(error)
    if (isAccountAuthError(error)) {
      const authCode = (code || "UNAUTHORIZED") as AuthenticationFailureCode
      options.onAuthenticationFailure?.(authCode)
      if (!options.onAuthenticationFailure) emitAuthenticationFailure(authCode)
    }
    return Promise.reject(error)
  })
  return client
}

export const httpClient = createHttpClient()


export const apiBaseUrl = API_BASE_URL
