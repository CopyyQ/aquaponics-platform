import { Bell, BookOpenCheck, Boxes, ChartNoAxesCombined, FolderKanban, Gauge, UserCog, Users } from "lucide-react"
import type { UserRole } from "@/entities/user/model/types"

export interface NavigationItem { label: string; path: string; icon: typeof Gauge; roles?: UserRole[] }

export function getAdminNavigationItems(): NavigationItem[] {
  return [
    { label: "Tổng quan hệ thống", path: "/admin/overview", icon: Gauge, roles: ["ADMIN"] },
    { label: "Thiết bị và cảm biến", path: "/admin/device-templates", icon: Boxes, roles: ["ADMIN"] },
    { label: "Cảnh báo", path: "/admin/alerts", icon: Bell, roles: ["ADMIN"] },
    { label: "Danh mục khách hàng", path: "/admin/users", icon: Users, roles: ["ADMIN"] },
    { label: "Quản lý tài khoản", path: "/admin/accounts", icon: UserCog, roles: ["ADMIN"] },
    { label: "Thông báo & Nhật ký", path: "/audit-logs", icon: BookOpenCheck, roles: ["ADMIN"] },
  ]
}

export function getOwnerNavigationItems(): NavigationItem[] {
  return [
    { label: "Tổng quan", path: "/overview", icon: Gauge, roles: ["OWNER", "VIEWER"] },
    { label: "Quan trắc", path: "/monitoring", icon: ChartNoAxesCombined, roles: ["OWNER", "VIEWER"] },
    { label: "Dự án", path: "/projects", icon: FolderKanban, roles: ["OWNER", "VIEWER"] },
    { label: "Cảnh báo", path: "/alerts", icon: Bell, roles: ["OWNER", "VIEWER"] },
  ]
}

export function getViewerNavigationItems(): NavigationItem[] {
  return getOwnerNavigationItems()
}

export function getNavigationItems(role: UserRole | undefined): NavigationItem[] {
  if (role === "ADMIN") return getAdminNavigationItems()
  if (role === "OWNER") return getOwnerNavigationItems()
  if (role === "VIEWER") return getViewerNavigationItems()
  return []
}
