import { Navigate, Outlet, createBrowserRouter, RouterProvider } from "react-router-dom"
import { useAuth } from "./auth"
import { Shell } from "./shell"
import { LoginPage } from "@/pages/login"
import { SystemsPage } from "@/pages/systems"
import { SystemPage } from "@/pages/system"
import { DevicePage } from "@/pages/device"
import { CatalogsPage } from "@/pages/catalogs"
import { UsersPage } from "@/pages/users"
import { ProfilePage } from "@/pages/profile"

function Guard() {
  const { session, loading } = useAuth()
  if (loading) return <p className="p-8">Đang tải phiên đăng nhập…</p>
  return session ? <Outlet /> : <Navigate to="/login" replace />
}

function LoginRoute() {
  const { session } = useAuth()
  return session ? <Navigate to="/aquaponics-systems" replace /> : <LoginPage />
}

const router = createBrowserRouter([
  { path: "/login", element: <LoginRoute /> },
  { element: <Guard />, children: [{ element: <Shell />, children: [
    { index: true, element: <Navigate to="/aquaponics-systems" replace /> },
    { path: "/aquaponics-systems", element: <SystemsPage /> },
    { path: "/aquaponics-systems/:systemId", element: <SystemPage /> },
    { path: "/aquaponics-systems/:systemId/devices/:deviceId", element: <DevicePage /> },
    { path: "/catalogs", element: <CatalogsPage /> },
    { path: "/users", element: <UsersPage /> },
    { path: "/profile", element: <ProfilePage /> },
  ] }] },
  { path: "*", element: <Navigate to="/aquaponics-systems" replace /> },
])

export function AppRouter() { return <RouterProvider router={router} /> }
