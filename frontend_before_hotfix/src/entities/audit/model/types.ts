export interface AuditLog {
  id: number
  user_id: number
  action: string
  entity_type: string
  entity_id: number | null
  description: string | null
  old_data: Record<string, unknown> | null
  new_data: Record<string, unknown> | null
  created_at: string
  actor: { id: number; full_name: string; username: string }
  target: { id: number | null; type: string; display_name: string }
}
