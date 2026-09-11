import { lazy, Suspense, type ComponentType, type ReactNode } from "react"
import { Navigate, createBrowserRouter, RouterProvider } from "react-router-dom"
import { AppShell } from "@/app/layouts/app-shell"
import { ProjectLayout } from "@/app/layouts/project-layout"
import { ProtectedRoute } from "@/app/router/protected-route"
import { RoleRoute } from "@/app/router/role-route"
import { useAuthStore } from "@/features/auth/model/auth-store"
import { Skeleton } from "@/shared/ui/skeleton"

function lazyNamed<T extends Record<K, ComponentType>, K extends keyof T>(loader: () => Promise<T>, name: K) {
  return lazy(async () => ({ default: (await loader())[name] }))
}

const LoginPage = lazyNamed(() => import("@/pages/login/LoginPage"), "LoginPage")
const NotFoundPage = lazyNamed(() => import("@/pages/not-found/NotFoundPage"), "NotFoundPage")
const UserOverviewPage = lazyNamed(() => import("@/pages/user-overview/UserOverviewPage"), "UserOverviewPage")
const UserMonitoringPage = lazyNamed(() => import("@/pages/user-monitoring/UserMonitoringPage"), "UserMonitoringPage")
const AlertsPage = lazyNamed(() => import("@/pages/alerts/AlertsPage"), "AlertsPage")
const ProfilePage = lazyNamed(() => import("@/pages/profile/ProfilePage"), "ProfilePage")
const ProjectOverviewPage = lazyNamed(() => import("@/pages/project-overview/ProjectOverviewPage"), "ProjectOverviewPage")
const ProjectDevicesPage = lazyNamed(() => import("@/pages/project-devices/ProjectDevicesPage"), "ProjectDevicesPage")
const ProjectMonitoringPage = lazyNamed(() => import("@/pages/project-monitoring/ProjectMonitoringPage"), "ProjectMonitoringPage")
const ProjectScadaPage = lazyNamed(() => import("@/pages/project-scada/ProjectScadaPage"), "ProjectScadaPage")
const ProjectMembersPage = lazyNamed(() => import("@/pages/project-members/ProjectMembersPage"), "ProjectMembersPage")
const ProjectAlertsPage = lazyNamed(() => import("@/pages/project-alerts/ProjectAlertsPage"), "ProjectAlertsPage")
const ProjectNotificationsPage = lazyNamed(() => import("@/pages/project-notifications/ProjectNotificationsPage"), "ProjectNotificationsPage")
const ProjectSettingsPage = lazyNamed(() => import("@/pages/project-settings/ProjectSettingsPage"), "ProjectSettingsPage")
const PublicMonitoringPage = lazyNamed(() => import("@/pages/public-monitoring/PublicMonitoringPage"), "PublicMonitoringPage")
const DeviceDetailPage = lazyNamed(() => import("@/pages/device-detail/DeviceDetailPage"), "DeviceDetailPage")
const SensorDetailPage = lazyNamed(() => import("@/pages/sensor-detail/SensorDetailPage"), "SensorDetailPage")
const AdminOverviewPage = lazyNamed(() => import("@/pages/admin-overview/AdminOverviewPage"), "AdminOverviewPage")
const AdminUsersPage = lazyNamed(() => import("@/pages/admin-users/AdminUsersPage"), "AdminUsersPage")
const AuditLogsPage = lazyNamed(() => import("@/pages/audit-logs/AuditLogsPage"), "AuditLogsPage")
const CustomerDirectoryPage = lazyNamed(() => import("@/pages/customer-directory/CustomerDirectoryPage"), "CustomerDirectoryPage")
const AccountsPage = lazyNamed(() => import("@/pages/admin-accounts/AccountsPage"), "AccountsPage")
const AdminUserDetailPage = lazyNamed(() => import("@/pages/admin-user-detail/AdminUserDetailPage"), "AdminUserDetailPage")
const DeviceTemplatesPage = lazyNamed(() => import("@/pages/device-templates/DeviceTemplatesPage"), "DeviceTemplatesPage")
const AdminAlertsPage = lazyNamed(() => import("@/pages/admin-alerts/AdminAlertsPage"), "AdminAlertsPage")

function PageSuspense({ children }: { children: ReactNode }) {
  return <Suspense fallback={<div className="flex flex-col gap-4"><Skeleton className="h-20" /><Skeleton className="h-72" /></div>}>{children}</Suspense>
}

function HomeRedirect() {
  const role = useAuthStore((state) => state.user?.system_role)
  return <Navigate to={role === "ADMIN" ? "/admin/overview" : "/overview"} replace />
}

function ProjectMembersAccess() {
  const role = useAuthStore((state) => state.user?.system_role)
  return role === "VIEWER" ? <Navigate to="../overview" replace /> : <ProjectMembersPage />
}

function ProjectManageAccess({ page }: { page: "notifications" | "settings" }) {
  const role = useAuthStore((state) => state.user?.system_role)
  if (role === "VIEWER") return <Navigate to="../overview" replace />
  return page === "notifications" ? <ProjectNotificationsPage /> : <ProjectSettingsPage />
}

const projectChildren = [
  { index: true, element: <Navigate to="overview" replace /> },
  { path: "overview", element: <ProjectOverviewPage /> },
  { path: "scada", element: <ProjectScadaPage /> },
  { path: "devices", element: <ProjectDevicesPage /> },
  { path: "devices/:deviceId", element: <DeviceDetailPage /> },
  { path: "devices/:deviceId/sensors/:sensorId", element: <SensorDetailPage /> },
  { path: "monitoring", element: <ProjectMonitoringPage /> },
  { path: "alerts", element: <ProjectAlertsPage /> },
  { path: "notifications", element: <ProjectManageAccess page="notifications" /> },
  { path: "members", element: <ProjectMembersAccess /> },
  { path: "settings", element: <ProjectManageAccess page="settings" /> },
]

const adminRoutes = [
  { path: "/login", element: <PageSuspense><LoginPage /></PageSuspense> },
  {
    element: <ProtectedRoute />,
    children: [{
      element: <AppShell />,
      children: [
        { index: true, element: <HomeRedirect /> },
        { path: "/overview", element: <UserOverviewPage /> },
        { path: "/projects", element: <UserOverviewPage /> },
        { path: "/projects/:projectId", element: <ProjectLayout />, children: projectChildren },
        { path: "/monitoring", element: <UserMonitoringPage /> },
        { path: "/alerts", element: <AlertsPage /> },
        { path: "/profile", element: <ProfilePage /> },
        { path: "/settings", element: <Navigate to="/overview" replace /> },
        {
          element: <RoleRoute roles={["ADMIN"]} />,
          children: [
            { path: "/members", element: <AdminUsersPage /> },
            { path: "/audit-logs", element: <AuditLogsPage /> },
            { path: "/admin/overview", element: <AdminOverviewPage /> },
            { path: "/admin/users", element: <CustomerDirectoryPage /> },
            { path: "/admin/accounts", element: <AccountsPage /> },
            { path: "/admin/users/:userId", element: <AdminUserDetailPage /> },
            { path: "/admin/projects/:projectId", element: <ProjectLayout />, children: projectChildren.map((route) => route.path === "members" ? { ...route, element: <ProjectMembersPage /> } : route) },
            { path: "/admin/device-templates", element: <DeviceTemplatesPage /> },
            { path: "/admin/alerts", element: <AdminAlertsPage /> },
          ],
        },
        { path: "*", element: <NotFoundPage /> },
      ].map((route) => ({ ...route, element: route.element ? <PageSuspense>{route.element}</PageSuspense> : route.element })),
    }],
  },
]

const publicGatewayRoutes = [
  { path: "/", element: <PageSuspense><PublicMonitoringPage /></PageSuspense> },
  { path: "*", element: <PageSuspense><NotFoundPage /></PageSuspense> },
]

const router = createBrowserRouter(
  import.meta.env.VITE_PUBLIC_MONITORING_GATEWAY === "true"
    ? publicGatewayRoutes
    : adminRoutes,
)

export function AppRouter() {
  return <RouterProvider router={router} />
}
