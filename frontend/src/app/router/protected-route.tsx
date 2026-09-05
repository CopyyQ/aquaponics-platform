import { useEffect } from "react"
import { Navigate, Outlet, useLocation } from "react-router-dom"
import { LoaderCircle } from "lucide-react"
import { useAuthStore } from "@/features/auth/model/auth-store"

export function ProtectedRoute() {
  const { token, user, loading, hydrate } = useAuthStore()
  const location = useLocation()
  useEffect(() => { void hydrate() }, [hydrate])
  if (loading) return <div className="grid min-h-screen place-items-center"><LoaderCircle className="size-7 animate-spin text-primary" /></div>
  const active = user?.status === "ACTIVE" && user.is_deleted === false && user.deleted_at === null
  if (!token || !user || !active) return <Navigate to="/login" replace />
  if (user.must_change_password && location.pathname !== "/profile") return <Navigate to="/profile" replace />
  return <Outlet />
}
