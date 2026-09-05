export type UserRole = "ADMIN" | "OWNER" | "VIEWER"
export type UserStatus = "ACTIVE" | "DISABLED" | "LOCKED" | "SOFT_DELETED"

export interface User {
  id: number
  username: string
  full_name: string
  email: string
  phone_number: string
  address: string
  system_role: UserRole
  status: UserStatus
  must_change_password: boolean
  last_login_at: string | null
  created_at: string
  updated_at: string
  token_version: number
  is_deleted: boolean
  deleted_at: string | null
  disabled_at: string | null
  disabled_by_user_id: number | null
  disabled_reason: string | null
  locked_at: string | null
  locked_by_user_id: number | null
  locked_reason: string | null
}

export interface UserCreateInput {
  username: string
  temporary_password: string
  full_name: string
  email: string
  phone_number: string
  address: string
  system_role: UserRole
}

export interface AdminUserCreateInput {
  username: string
  full_name: string
  email: string
  phone_number: string
  address: string
  system_role: UserRole
  status: Exclude<UserStatus, "SOFT_DELETED">
  password: string
  confirm_password: string
  must_change_password: boolean
}

export interface AdminSetPasswordInput {
  new_password: string
  confirm_password: string
  invalidate_sessions: boolean
  must_change_password: boolean
}

export interface AdminSetPasswordResponse {
  success: boolean
  message: string
  sessions_invalidated: boolean
  must_change_password: boolean
}

export interface AdminUserDetail extends User {
  project_count: number
  device_count: number
  sensor_count: number
  open_alert_count: number
  online_device_count: number
  offline_device_count: number
  last_telemetry_at: string | null
}

export interface AdminUserList {
  items: AdminUserDetail[]
  total: number
  page: number
  page_size: number
}

export interface UserActivity {
  id: number
  action: string
  description: string | null
  entity_type: string
  entity_id: number | null
  created_at: string
  old_data: Record<string, unknown> | null
  new_data: Record<string, unknown> | null
  actor_name: string
  target_name: string
}
