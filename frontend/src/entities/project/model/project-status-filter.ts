import type { AdminUserProject } from "@/entities/project/model/types"

export type ProjectStatusFilter = "active" | "disabled" | "all"

export const PROJECT_STATUS_FILTER_OPTIONS: ReadonlyArray<{
  value: ProjectStatusFilter
  label: string
}> = [
  { value: "active", label: "Đang hoạt động" },
  { value: "disabled", label: "Đã vô hiệu hóa" },
  { value: "all", label: "Tất cả" },
]

export function filterProjectsByStatus(
  projects: AdminUserProject[],
  filter: ProjectStatusFilter,
): AdminUserProject[] {
  if (filter === "active") return projects.filter((project) => project.status === "ACTIVE")
  if (filter === "disabled") return projects.filter((project) => project.status === "DISABLED")
  return projects.filter((project) => project.status === "ACTIVE" || project.status === "DISABLED")
}

export function projectStatusCounts(projects: AdminUserProject[]) {
  return {
    active: projects.filter((project) => project.status === "ACTIVE").length,
    disabled: projects.filter((project) => project.status === "DISABLED").length,
  }
}
