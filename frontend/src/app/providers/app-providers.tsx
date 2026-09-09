import { useEffect, type ReactNode } from "react"
import { QueryClientProvider } from "@tanstack/react-query"
import { TooltipProvider } from "@/shared/ui/tooltip"
import { Toaster } from "@/shared/ui/sonner"
import { ThemeProvider } from "@/app/providers/theme-provider"
import { AuthProvider } from "@/app/auth"
import { queryClient } from "@/shared/api/query-client"
import { toast } from "sonner"

export { queryClient }

export function AppProviders({ children }: { children: ReactNode }) {
  useEffect(() => {
    const expired = () => { queryClient.clear(); localStorage.removeItem("aquaponics_access_token"); toast.error("Phiên đăng nhập không còn hoạt động."); if (!window.location.pathname.startsWith("/login")) window.location.replace("/login") }
    window.addEventListener("aquaponics-auth-expired", expired)
    return () => window.removeEventListener("aquaponics-auth-expired", expired)
  }, [])
  return <ThemeProvider><QueryClientProvider client={queryClient}><TooltipProvider delayDuration={250}><AuthProvider>{children}</AuthProvider><Toaster /></TooltipProvider></QueryClientProvider></ThemeProvider>
}
