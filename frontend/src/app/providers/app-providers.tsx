import { QueryClientProvider } from "@tanstack/react-query"
import { useEffect, type ReactNode } from "react"
import { TooltipProvider } from "@/shared/ui/tooltip"
import { Toaster } from "@/shared/ui/sonner"
import { ThemeProvider } from "@/app/providers/theme-provider"
import { queryClient } from "@/shared/api/query-client"
import { onAuthenticationFailure } from "@/shared/api/auth-events"
import { useAuthStore } from "@/features/auth/model/auth-store"
import { toast } from "sonner"

export { queryClient }

export function AppProviders({ children }: { children: ReactNode }) {
  useEffect(() => onAuthenticationFailure((code) => {
    void queryClient.cancelQueries()
    queryClient.clear()
    useAuthStore.getState().clear()
    localStorage.removeItem("aquaponics_access_token")
    localStorage.removeItem("access_token")
    localStorage.removeItem("refresh_token")
    sessionStorage.clear()
    const messages = { ACCOUNT_DISABLED: "Tài khoản đã bị vô hiệu hóa.", ACCOUNT_LOCKED: "Tài khoản đang bị khóa.", TOKEN_REVOKED: "Phiên đăng nhập đã bị thu hồi.", UNAUTHORIZED: "Phiên đăng nhập không còn hoạt động." }
    toast.error(messages[code])
    if (!window.location.pathname.startsWith("/login")) window.location.replace("/login")
  }), [])
  return <ThemeProvider><QueryClientProvider client={queryClient}><TooltipProvider delayDuration={250}>{children}<Toaster /></TooltipProvider></QueryClientProvider></ThemeProvider>
}
