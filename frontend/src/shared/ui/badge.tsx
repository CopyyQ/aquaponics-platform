import * as React from "react"
import { cva, type VariantProps } from "class-variance-authority"
import { cn } from "@/shared/lib/utils"

const badgeVariants = cva("inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-semibold transition-colors", {
  variants: {
    variant: {
      default: "border-transparent bg-primary text-primary-foreground",
      secondary: "border-transparent bg-secondary text-secondary-foreground",
      destructive: "border-transparent bg-destructive text-white",
      outline: "text-foreground",
      success: "border-emerald-500/20 bg-emerald-500/10 text-emerald-700 dark:text-emerald-400",
      warning: "border-amber-500/20 bg-amber-500/10 text-amber-700 dark:text-amber-400",
    },
  },
  defaultVariants: { variant: "default" },
})

export function Badge({ className, variant, ...props }: React.ComponentProps<"div"> & VariantProps<typeof badgeVariants>) {
  return <div className={cn(badgeVariants({ variant }), className)} {...props} />
}
