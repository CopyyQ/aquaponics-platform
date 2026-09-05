const valueFormatter = new Intl.NumberFormat("vi-VN", {
  maximumFractionDigits: 2,
})

export function formatSensorValue(value: number | null, unit: string) {
  if (value === null || !Number.isFinite(value)) return "—"
  return `${valueFormatter.format(value)} ${unit}`.trim()
}
