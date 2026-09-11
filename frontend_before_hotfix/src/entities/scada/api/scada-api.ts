import { httpClient } from "@/shared/api/http-client"
import type { ScadaLayout, ScadaLayoutMutationResponse, ScadaRuntime } from "@/entities/scada/model/types"

export const scadaApi = {
  runtime: async (projectId: number) => (await httpClient.get<ScadaRuntime>(`/projects/${projectId}/scada/runtime`)).data,
  saveDraft: async (projectId: number, layout: ScadaLayout) => (await httpClient.put<ScadaLayoutMutationResponse>(`/projects/${projectId}/scada/layout/draft`, layout)).data,
  publish: async (projectId: number) => (await httpClient.post<ScadaLayoutMutationResponse>(`/projects/${projectId}/scada/layout/publish`)).data,
}
