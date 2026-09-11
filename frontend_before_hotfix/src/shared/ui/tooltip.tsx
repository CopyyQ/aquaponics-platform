import type { ReactNode } from "react"

export function TooltipProvider({ children }: { children: ReactNode; delayDuration?: number }) { return <>{children}</> }
export function Tooltip({ children }: { children: ReactNode }) { return <>{children}</> }
export function TooltipTrigger({ children }: { children: ReactNode; asChild?: boolean }) { return <>{children}</> }
export function TooltipContent({ children }: { children: ReactNode }) { return <span className="sr-only">{children}</span> }
