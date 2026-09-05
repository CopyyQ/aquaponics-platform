import type { LucideIcon } from "lucide-react"
import type { ReactNode } from "react"

export function EmptyState({ icon: Icon, title, description, action }: { icon: LucideIcon; title: string; description: string; action?: ReactNode }) {
  return <div className="flex min-h-56 flex-col items-center justify-center rounded-xl border border-dashed bg-muted/20 p-8 text-center"><div className="mb-4 rounded-full bg-primary/10 p-3"><Icon className="size-6 text-primary" /></div><h3 className="font-semibold">{title}</h3><p className="mt-1 max-w-md text-sm text-muted-foreground">{description}</p>{action && <div className="mt-4">{action}</div>}</div>
}
