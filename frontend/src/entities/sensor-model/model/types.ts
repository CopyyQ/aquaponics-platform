export interface SensorModel {
  id: number
  code: string
  name: string
  unit: string
  description: string | null
  default_lower_threshold: number | null
  default_upper_threshold: number | null
  is_visible: boolean
  is_active: boolean
  value_type: string
  chart_type: string
  measurement_semantics: "GAUGE" | "COUNTER"
  created_at: string
  updated_at: string
}
