import * as React from "react"
import { cn } from "@/shared/lib/utils"

export function Switch({ className, checked, onCheckedChange, disabled, ...props }: Omit<React.ComponentProps<"button">, "onChange"> & { checked?: boolean; onCheckedChange?: (checked: boolean) => void }) {
  return <button type="button" role="switch" aria-checked={checked} disabled={disabled} onClick={() => onCheckedChange?.(!checked)} className={cn("inline-flex h-5 w-9 shrink-0 items-center rounded-full border-2 border-transparent transition-colors", checked ? "bg-primary" : "bg-input", className)} {...props}><span className={cn("block size-4 rounded-full bg-background shadow transition-transform", checked ? "translate-x-4" : "translate-x-0")} /></button>
}
