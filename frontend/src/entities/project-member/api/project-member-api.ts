import { httpClient } from "@/shared/api/http-client"
import type { ProjectMemberList } from "@/entities/project-member/model/types"

export const projectMemberApi = {
  list: async (projectId: number, q: string, page = 1) =>
    (
      await httpClient.get<ProjectMemberList>(`/projects/${projectId}/members`, {
        params: { q, page, page_size: 20 },
      })
    ).data,
  add: async (projectId: number, userId: number) =>
    (await httpClient.post(`/projects/${projectId}/members`, { user_id: userId })).data,
  remove: async (projectId: number, userId: number): Promise<void> => {
    await httpClient.delete(`/projects/${projectId}/members/${userId}`)
  },
}
