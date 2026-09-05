import type { UserRole } from "@/entities/user/model/types"

export const canManageInfrastructure = (role?: UserRole) => role === "ADMIN"
export const canManageThresholds = (role?: UserRole) => role === "ADMIN" || role === "OWNER"
export const canResolveAlerts = canManageThresholds
export const canManageMembers = (role?: UserRole) => role === "ADMIN" || role === "OWNER"
export const canViewAuditLogs = canManageThresholds
