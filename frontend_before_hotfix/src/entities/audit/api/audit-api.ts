import { httpClient } from "@/shared/api/http-client"
import type { AuditLog } from "@/entities/audit/model/types"

export const auditApi = {
  list: async () => (await httpClient.get<AuditLog[]>("/audit-logs")).data,
}
