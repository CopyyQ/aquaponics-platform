import type { ConnectionStatus } from "@/entities/device/model/types"

export interface Sensor {
  id: number
  device_id: number
  sensor_model_id: number
  code: string
  name: string
  installation_location: string | null
  description: string | null
  status: ConnectionStatus
  last_seen_at: string | null
  warning_enabled: boolean
  lower_threshold: number | null
  upper_threshold: number | null
  below_threshold_message: string | null
  above_threshold_message: string | null
  alert_risk_level: BusinessRiskLevel | null
  alert_delay_seconds: number
  is_enabled: boolean
  disabled_at: string | null
  disabled_by_user_id: number | null
  disabled_reason: string | null
  created_at: string
  updated_at: string
}

export interface SensorCreateInput {
  sensor_model_id: number
  code: string
  name: string
  description?: string
}

export interface ThresholdInput {
  warning_enabled: boolean
  lower_threshold: number | null
  upper_threshold: number | null
  alert_delay_seconds: number
  below_threshold_message: string | null
  above_threshold_message: string | null
  alert_risk_level: BusinessRiskLevel | null
}

export type BusinessRiskLevel = "EXTREME" | "VERY_HIGH" | "HIGH" | "MEDIUM" | "LOW_MEDIUM" | "LOW"
