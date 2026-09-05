import { createContext, useContext } from "react"
import type { ProjectOverview } from "@/entities/project/model/types"

export const ProjectContext = createContext<ProjectOverview | null>(null)

export function useProjectContext() {
  const value = useContext(ProjectContext)
  if (!value) throw new Error("useProjectContext phải được dùng trong ProjectLayout")
  return value
}
