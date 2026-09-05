import * as React from "react"
import { cn } from "@/shared/lib/utils"

interface TabsContextValue {
  value: string
  setValue: (value: string) => void
}

const TabsContext = React.createContext<TabsContextValue | null>(null)

export function Tabs({ className, defaultValue = "", value, onValueChange, ...props }:
  React.ComponentProps<"div"> & {
    defaultValue?: string
    value?: string
    onValueChange?: (value: string) => void
  }) {
  const [internalValue, setInternalValue] = React.useState(defaultValue)
  const activeValue = value ?? internalValue
  const setValue = React.useCallback((nextValue: string) => {
    if (value === undefined) setInternalValue(nextValue)
    onValueChange?.(nextValue)
  }, [onValueChange, value])
  return (
    <TabsContext.Provider value={{ value: activeValue, setValue }}>
      <div className={className} {...props} />
    </TabsContext.Provider>
  )
}

export function TabsList({ className, ...props }: React.ComponentProps<"div">) {
  return <div role="tablist" className={cn("inline-flex min-h-9 flex-wrap items-center rounded-lg bg-muted p-1", className)} {...props} />
}

export function TabsTrigger({ className, value = "", ...props }:
  Omit<React.ComponentProps<"button">, "value"> & { value?: string }) {
  const context = React.useContext(TabsContext)
  const selected = context?.value === value
  return (
    <button
      type="button"
      role="tab"
      aria-selected={selected}
      data-state={selected ? "active" : "inactive"}
      className={cn(
        "rounded-md px-3 py-1 text-sm font-medium focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring data-[state=active]:bg-background data-[state=active]:shadow-xs",
        className,
      )}
      {...props}
      onClick={(event) => {
        context?.setValue(value)
        props.onClick?.(event)
      }}
    />
  )
}

export function TabsContent({ className, value = "", ...props }:
  Omit<React.ComponentProps<"div">, "value"> & { value?: string }) {
  const context = React.useContext(TabsContext)
  if (context?.value !== value) return null
  return <div role="tabpanel" className={cn("mt-4", className)} {...props} />
}
