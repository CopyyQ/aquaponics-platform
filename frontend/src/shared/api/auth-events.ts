export type AuthenticationFailureCode =
  | "ACCOUNT_DISABLED"
  | "ACCOUNT_LOCKED"
  | "TOKEN_REVOKED"
  | "UNAUTHORIZED"

const eventName = "aquaponics:authentication-failure"

export function emitAuthenticationFailure(code: AuthenticationFailureCode) {
  if (typeof window !== "undefined") {
    window.dispatchEvent(new CustomEvent<AuthenticationFailureCode>(eventName, { detail: code }))
  }
}

export function onAuthenticationFailure(handler: (code: AuthenticationFailureCode) => void) {
  if (typeof window === "undefined") return () => undefined
  const listener = (event: Event) => handler((event as CustomEvent<AuthenticationFailureCode>).detail)
  window.addEventListener(eventName, listener)
  return () => window.removeEventListener(eventName, listener)
}
