import { createContext, useContext, useEffect, useMemo, useState, type ReactNode } from "react"
import { loadSession, logout as logoutRequest } from "@/api/resources"
import type { Session } from "@/api/contracts"

interface AuthState {
  session: Session | null
  loading: boolean
  can: (permission: string) => boolean
  has: (permission: string) => boolean
  reload: () => Promise<void>
  logout: () => Promise<void>
}

const AuthContext = createContext<AuthState | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [session, setSession] = useState<Session | null>(null)
  const [loading, setLoading] = useState(true)
  const reload = async () => {
    if (!localStorage.getItem("aquaponics_access_token")) {
      setSession(null)
      setLoading(false)
      return
    }
    try { setSession(await loadSession()) } catch { setSession(null) } finally { setLoading(false) }
  }
  const logout = async () => {
    try { await logoutRequest() } finally { localStorage.removeItem("aquaponics_access_token"); setSession(null) }
  }
  useEffect(() => {
    void reload()
    const expired = () => setSession(null)
    window.addEventListener("aquaponics-auth-expired", expired)
    window.addEventListener("aquaponics:authentication-failure", expired)
    return () => {
      window.removeEventListener("aquaponics-auth-expired", expired)
      window.removeEventListener("aquaponics:authentication-failure", expired)
    }
  }, [])
  const value = useMemo(() => {
    const can = (permission: string) => Boolean(session?.permissions.includes(permission))
    return { session, loading, can, has: can, reload, logout }
  }, [session, loading])
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth() {
  const value = useContext(AuthContext)
  if (!value) throw new Error("AuthProvider is required")
  return value
}
