import { Activity, CheckCircle2, Clock3 } from "lucide-react"
import type { LatestTelemetry } from "@/entities/telemetry/model/types"
import { formatRelative } from "@/shared/lib/date"
import { cn } from "@/shared/lib/utils"
import { Card, CardContent } from "@/shared/ui/card"

export function TelemetryValueCard({ item, selected = false }: { item: LatestTelemetry; selected?: boolean }) {
  return <Card className={cn("h-full overflow-hidden shadow-none transition-colors", selected && "border-primary bg-primary/5")}>
    <div className={cn("h-1 bg-primary", selected && "bg-primary")} />
    <CardContent className="p-5">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="truncate text-sm font-medium text-muted-foreground">{item.sensor_name}</div>
          <div className="mt-2 flex items-end gap-2">
            <span className="text-3xl font-semibold tracking-tight">{item.value ?? "—"}</span>
            <span className="pb-1 text-sm text-muted-foreground">{item.unit}</span>
          </div>
        </div>
        <div className="grid size-10 shrink-0 place-items-center rounded-xl bg-primary/10 text-primary">
          {selected ? <CheckCircle2 /> : <Activity />}
        </div>
      </div>
      <div className="mt-4 flex items-center justify-between gap-3 border-t pt-3 text-xs text-muted-foreground">
        <span className="truncate">{item.device_name}</span>
        <span className="flex shrink-0 items-center gap-1"><Clock3 />{formatRelative(item.recorded_at)}</span>
      </div>
    </CardContent>
  </Card>
}
