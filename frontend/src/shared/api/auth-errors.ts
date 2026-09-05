import axios from "axios"

export const ACCOUNT_AUTH_CODES = [
  "ACCOUNT_DISABLED",
  "ACCOUNT_INACTIVE",
  "ACCOUNT_LOCKED",
  "ACCOUNT_DELETED",
  "TOKEN_REVOKED",
] as const

export function getAccountAuthCode(error: unknown): string | undefined {
  if (!axios.isAxiosError(error)) return undefined
  const data = error.response?.data as {
    code?: string
    detail?: { code?: string }
  } | undefined
  return data?.code ?? data?.detail?.code
}

export function isAccountAuthError(error: unknown): boolean {
  const code = getAccountAuthCode(error)
  return ACCOUNT_AUTH_CODES.some((candidate) => candidate === code)
}
