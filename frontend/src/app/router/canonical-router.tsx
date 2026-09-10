import { lazy, Suspense, type ComponentType, type ReactNode } from "react"
import { Navigate, Outlet, createBrowserRouter, RouterProvider, useLocation } from "react-router-dom"
import { AppShell } from "@/app/layouts/app-shell"
import { AquaponicsSystemLayout } from "@/app/layouts/aquaponics-system-layout"
import { useAuth } from "@/app/auth"
import { Skeleton } from "@/shared/ui/skeleton"
import { EmptyState } from "@/shared/ui/empty-state"
import { ShieldAlert } from "lucide-react"

function lazyNamed<T extends Record<K, ComponentType>, K extends keyof T>(loader: () => Promise<T>, name: K) {
  return lazy(async () => ({ default: (await loader())[name] }))
}

const LoginPage = lazyNamed(() => import("@/pages/login"), "LoginPage")
const SystemsPage = lazyNamed(() => import("@/pages/systems-canonical"), "SystemsPage")
const OverviewPage = lazyNamed(() => import("@/pages/overview"), "OverviewPage")
const ScadaPage = lazyNamed(() => import("@/pages/scada"), "ScadaPage")
const MonitoringPage = lazyNamed(() => import("@/pages/monitoring"), "MonitoringPage")
const DevicesPage = lazyNamed(() => import("@/pages/devices-canonical"), "DevicesPage")
const DeviceDetailPage = lazyNamed(() => import("@/pages/device-detail-activation"), "DeviceDetailCanonicalPage")
const SensorDetailPage = lazyNamed(() => import("@/pages/sensor-detail-canonical"), "SensorDetailPage")
const ActuatorDetailPage = lazyNamed(() => import("@/pages/actuator-detail-canonical"), "ActuatorDetailPage")
const AlertsPage = lazyNamed(() => import("@/pages/alerts-activation"), "AlertsPage")
const AlertDetailPage = lazyNamed(() => import("@/pages/alert-detail-canonical"), "AlertDetailPage")
const MembersPage = lazyNamed(() => import("@/pages/members"), "MembersPage")
const ActivitiesPage = lazyNamed(() => import("@/pages/activities"), "ActivitiesPage")
const SettingsPage = lazyNamed(() => import("@/pages/settings-canonical"), "SettingsPage")
const AlertDeliveryPage = lazyNamed(() => import("@/pages/alert-delivery"), "AlertDeliveryPage")
const CatalogsPage = lazyNamed(() => import("@/pages/catalogs-activation"), "CatalogsCanonicalPage")
const UsersPage = lazyNamed(() => import("@/pages/users-canonical"), "UsersPage")
const UserDetailPage = lazyNamed(() => import("@/pages/user-detail-canonical"), "UserDetailPage")
const ProfilePage = lazyNamed(() => import("@/pages/profile-canonical"), "ProfilePage")
const NotFoundPage = lazyNamed(() => import("@/pages/not-found-canonical"), "NotFoundCanonicalPage")
const PublicMonitoringPage = lazyNamed(() => import("@/pages/public-monitoring-canonical"), "PublicMonitoringPage")

function PageSuspense({ children }: { children: ReactNode }) {
  return <Suspense fallback={<div className="space-y-4"><Skeleton className="h-20" /><Skeleton className="h-72" /></div>}>{children}</Suspense>
}

function Guard() {
  const { session, loading } = useAuth()
  const location = useLocation()
  if (loading) return <div className="p-8"><Skeleton className="h-10 w-48" /></div>
  if (!session) return <Navigate to="/login" replace state={{ from: location.pathname }} />
  if (session.user.must_change_password && location.pathname !== "/profile") return <Navigate to="/profile?change-password=required" replace />
  return <Outlet />
}

function LoginRoute() {
  const { session } = useAuth()
  return session ? <Navigate to="/aquaponics-systems" replace /> : <LoginPage />
}

function PermissionGuard({ permission, children }: { permission: string; children: ReactNode }) {
  const { can } = useAuth()
  return can(permission) ? children : <EmptyState icon={ShieldAlert} title="Không có quyền truy cập" description={`Phiên hiện tại không có quyền ${permission}. Backend vẫn là lớp thực thi bảo mật cuối cùng.`} />
}

const child = (element: ReactNode) => ({ element: <PageSuspense>{element}</PageSuspense> })
const permitted = (permission: string, element: ReactNode) => child(<PermissionGuard permission={permission}>{element}</PermissionGuard>)

const router = createBrowserRouter([
  { path: "/public/:slug", ...child(<PublicMonitoringPage />) },
  { path: "/login", element: <LoginRoute /> },
  { element: <Guard />, children: [{ element: <AppShell />, children: [
    { index: true, element: <Navigate to="/aquaponics-systems" replace /> },
    { path: "/aquaponics-systems", ...permitted("aquaponics_systems.read", <SystemsPage />) },
    { path: "/aquaponics-systems/:systemId", element: <PermissionGuard permission="aquaponics_systems.read"><AquaponicsSystemLayout /></PermissionGuard>, children: [
      { index: true, element: <Navigate to="overview" replace /> },
      { path: "overview", ...permitted("aquaponics_systems.read", <OverviewPage />) },
      { path: "scada", ...permitted("scada.read", <ScadaPage />) },
      { path: "monitoring", ...permitted("monitoring.read", <MonitoringPage />) },
      { path: "devices", ...permitted("devices.read", <DevicesPage />) },
      { path: "devices/:deviceId", ...permitted("devices.read", <DeviceDetailPage />) },
      { path: "devices/:deviceId/sensors/:sensorId", ...permitted("sensors.read", <SensorDetailPage />) },
      { path: "devices/:deviceId/actuators/:actuatorId", ...permitted("actuators.read", <ActuatorDetailPage />) },
      { path: "alerts", ...permitted("incidents.read", <AlertsPage />) },
      { path: "alerts/:alertId", ...permitted("incidents.read", <AlertDetailPage />) },
      { path: "members", ...permitted("aquaponics_systems.read", <MembersPage />) },
      { path: "activities", ...permitted("activities.read", <ActivitiesPage />) },
      { path: "notifications", ...permitted("notifications.settings.read", <AlertDeliveryPage />) },
      { path: "settings", ...permitted("aquaponics_systems.read", <SettingsPage />) },
    ] },
    { path: "/catalogs", ...permitted("device_templates.read", <CatalogsPage />) },
    { path: "/users", ...permitted("users.read", <UsersPage />) },
    { path: "/users/:userId", ...permitted("users.read", <UserDetailPage />) },
    { path: "/profile", ...child(<ProfilePage />) },
  ] }] },
  { path: "*", ...child(<NotFoundPage />) },
])

export function AppRouter() { return <RouterProvider router={router} /> }
