export function getSensorValueStatus(value: number | null, lowerThreshold: number | null, upperThreshold: number | null) {
  if (value === null) return { label: "Chưa xác định", tone: "neutral" as const }
  if (lowerThreshold !== null && value < lowerThreshold) {
    return { label: "Thấp hơn ngưỡng", tone: "danger" as const }
  }
  if (upperThreshold !== null && value > upperThreshold) {
    return { label: "Cao hơn ngưỡng", tone: "danger" as const }
  }
  return { label: "Trong ngưỡng", tone: "success" as const }
}
