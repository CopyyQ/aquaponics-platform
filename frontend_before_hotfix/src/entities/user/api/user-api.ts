import { httpClient } from "@/shared/api/http-client"
import type { AdminSetPasswordInput, AdminSetPasswordResponse, AdminUserCreateInput, AdminUserDetail, AdminUserList, User, UserActivity, UserCreateInput, UserRole, UserStatus } from "@/entities/user/model/types"

export const userApi = {
  adminList: async (q: string, page = 1, customerOnly = false, role?: UserRole, status?: UserStatus) => (await httpClient.get<AdminUserList>("/admin/users", { params: { q, page, page_size: 20, customer_only: customerOnly, role, status } })).data,
  adminCreate: async (payload: AdminUserCreateInput) => (
    await httpClient.post<AdminUserDetail>("/admin/users", payload)
  ).data,
  list: async () => (await httpClient.get<User[]>("/members")).data,
  create: async (payload: UserCreateInput) => (await httpClient.post<User>("/members", payload)).data,
  update: async (id: number, payload: Partial<User>) => (await httpClient.patch<User>(`/members/${id}`, payload)).data,
  disable: async (id: number) => (await httpClient.post(`/members/${id}/disable`)).data,
  enable: async (id: number) => (await httpClient.post(`/members/${id}/enable`)).data,
  remove: async (id: number) => httpClient.delete(`/members/${id}`),
  adminGet: async (id: number) => (await httpClient.get<AdminUserDetail>(`/admin/users/${id}`)).data,
  adminUpdate: async (id: number, payload: Partial<User>) => (
    await httpClient.patch<AdminUserDetail>(`/admin/users/${id}`, payload)
  ).data,
  activity: async (id: number) => (
    await httpClient.get<UserActivity[]>(`/admin/users/${id}/activity`)
  ).data,
  resetPassword: async (id: number, temporary_password: string, confirm_password: string) => (
    await httpClient.post(`/admin/users/${id}/reset-password`, {
      temporary_password, confirm_password, invalidate_sessions: true,
    })
  ).data,
  adminSetPassword: async (id: number, payload: AdminSetPasswordInput) => (
    await httpClient.post<AdminSetPasswordResponse>(`/admin/users/${id}/set-password`, payload)
  ).data,
  forceLogout: async (id: number, reason?: string) => (await httpClient.post(`/admin/users/${id}/force-logout`, { reason })).data,
  activate: async (id: number, reason?: string) => (await httpClient.post(`/admin/users/${id}/activate`, { reason })).data,
  disableAccount: async (id: number, reason?: string) => (await httpClient.post(`/admin/users/${id}/disable`, { reason })).data,
  lock: async (id: number, reason?: string) => (await httpClient.post(`/admin/users/${id}/lock`, { reason })).data,
  unlock: async (id: number, reason?: string) => (await httpClient.post(`/admin/users/${id}/unlock`, { reason })).data,
  softDelete: async (id: number, reason?: string) => (await httpClient.delete(`/admin/users/${id}`, { data: { reason } })).data,
  restore: async (id: number, reason?: string) => (await httpClient.post(`/admin/users/${id}/restore`, { reason })).data,
  assignOwner: async (user_id: number) => httpClient.post("/members/assign-owner", { user_id }),
}
