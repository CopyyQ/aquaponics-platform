export interface ProjectMember {
  id: number
  user_id: number
  full_name: string
  username: string
  email: string
  phone_number: string
  role: "VIEWER"
  status: "ACTIVE" | "DISABLED"
  created_at: string
  created_by: number | null
  created_by_name: string | null
}

export interface ProjectMemberList {
  items: ProjectMember[]
  total: number
  page: number
  page_size: number
}
