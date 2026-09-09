import { Boxes, Gauge, UserRound, Users } from "lucide-react"
import type { LucideIcon } from "lucide-react"

export interface NavigationItem { label: string; path: string; icon: LucideIcon; permission?: string }

export function getNavigationItems(can: (permission: string) => boolean): NavigationItem[] {
  const items: NavigationItem[] = [
    { label: "Hệ thống Aquaponics", path: "/aquaponics-systems", icon: Gauge, permission: "aquaponics_systems.read" },
    { label: "Danh mục thiết bị", path: "/catalogs", icon: Boxes, permission: "device_templates.read" },
    { label: "Người dùng", path: "/users", icon: Users, permission: "users.read" },
    { label: "Hồ sơ", path: "/profile", icon: UserRound },
  ]
  return items.filter((item) => !item.permission || can(item.permission))
}
