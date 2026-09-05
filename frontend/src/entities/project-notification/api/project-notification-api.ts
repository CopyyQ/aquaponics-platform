import type { NotificationDelivery, NotificationRecipient, NotificationSettings, PublicSettings } from "@/entities/project-notification/model/types"
import { httpClient } from "@/shared/api/http-client"

export const projectNotificationApi = {
  deliveryHistory: async () => (await httpClient.get<NotificationDelivery[]>("/admin/notification-deliveries/history")).data,
  get: async (projectId: number) => (await httpClient.get<NotificationSettings>(`/projects/${projectId}/notification-settings`)).data,
  update: async (projectId: number, payload: Omit<NotificationSettings, "telegram_bot_configured" | "recipients">) => (await httpClient.put<NotificationSettings>(`/projects/${projectId}/notification-settings`, payload)).data,
  createRecipient: async (projectId: number, payload: { name: string; telegram_chat_id: string; enabled?: boolean }) => (await httpClient.post<NotificationRecipient>(`/projects/${projectId}/notification-recipients`, payload)).data,
  updateRecipient: async (projectId: number, recipientId: number, payload: Partial<Pick<NotificationRecipient, "name" | "telegram_chat_id" | "enabled">>) => (await httpClient.patch<NotificationRecipient>(`/projects/${projectId}/notification-recipients/${recipientId}`, payload)).data,
  removeRecipient: async (projectId: number, recipientId: number) => { await httpClient.delete(`/projects/${projectId}/notification-recipients/${recipientId}`) },
  testRecipient: async (projectId: number, recipientId: number) => (await httpClient.post<{ sent: boolean; detail: string }>(`/projects/${projectId}/notification-recipients/${recipientId}/test`)).data,
  getPublicSettings: async (projectId: number) => (await httpClient.get<PublicSettings>(`/projects/${projectId}/public-settings`)).data,
  updatePublicSettings: async (projectId: number, payload: { enabled: boolean }) => (await httpClient.put<PublicSettings>(`/projects/${projectId}/public-settings`, payload)).data,
}
