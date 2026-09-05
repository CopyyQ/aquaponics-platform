import type { LucideIcon } from "lucide-react"
import { Card, CardContent } from "@/shared/ui/card"
import { cn } from "@/shared/lib/utils"

interface MonitoringMetricCardProps {
  title: string
  value: string | number
  description: string
  icon: LucideIcon
  tone?: "default" | "success" | "warning" | "danger"
}

const toneClass: Record<NonNullable<MonitoringMetricCardProps["tone"]>, string> = {
  default: "bg-primary/10 text-primary",
  success: "bg-emerald-500/10 text-emerald-700 dark:text-emerald-300",
  warning: "bg-amber-500/10 text-amber-700 dark:text-amber-300",
  danger: "bg-destructive/10 text-destructive",
}

export function MonitoringMetricCard({ title, value, description, icon: Icon, tone = "default" }: MonitoringMetricCardProps) {
  return <Card className="overflow-hidden border-border/80 shadow-none">
    <CardContent className="flex min-h-32 items-start justify-between gap-4 p-5">
      <div className="min-w-0">
        <div className="text-sm font-medium text-muted-foreground">{title}</div>
        <div className="mt-2 text-3xl font-semibold tracking-tight">{value}</div>
        <div className="mt-1 text-xs leading-5 text-muted-foreground">{description}</div>
      </div>
      <div className={cn("grid size-11 shrink-0 place-items-center rounded-xl", toneClass[tone])}>
        <Icon />
      </div>
    </CardContent>
  </Card>
}
