import { Navigate, Outlet } from "react-router-dom"
import { useAuthStore } from "@/features/auth/model/auth-store"
import type { UserRole } from "@/entities/user/model/types"

interface RoleRouteProps {
  roles: UserRole[]
}

export function RoleRoute({ roles }: RoleRouteProps) {
  const role = useAuthStore((state) => state.user?.system_role)
  if (!role || !roles.includes(role)) return <Navigate to={role === "ADMIN" ? "/admin/overview" : "/overview"} replace />
  return <Outlet />
}
