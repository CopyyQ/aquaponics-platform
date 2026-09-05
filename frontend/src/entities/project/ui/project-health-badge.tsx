import type { ProjectHealthStatus } from "@/entities/project/model/project-health"
import { Badge } from "@/shared/ui/badge"

const labels: Record<ProjectHealthStatus, string> = {
  CRITICAL: "Nguy hiểm",
  WARNING: "Cảnh báo",
  ATTENTION: "Cần chú ý",
  HEALTHY: "Bình thường",
}

export function ProjectHealthBadge({ status }: { status: ProjectHealthStatus }) {
  const variant = status === "CRITICAL"
    ? "destructive"
    : status === "WARNING"
      ? "warning"
      : status === "HEALTHY"
        ? "success"
        : "secondary"
  return <Badge variant={variant}>{labels[status]}</Badge>
}
