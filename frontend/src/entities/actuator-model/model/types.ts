export interface ActuatorModel {
  id: number
  code: string
  name: string
  description: string | null
  data_type: "BOOLEAN"
  default_state: boolean
  is_active: boolean
  sort_order: number
  is_deleted: boolean
  created_at: string
  updated_at: string
  feedbacks: ActuatorModelFeedback[]
}

export interface ActuatorModelFeedbackInput {
  feedback_role: "SUPPLY_VOLTAGE" | "RUNNING_CURRENT"
  sensor_model_id: number
  value_key: string
  unit: string
  data_type: "FLOAT"
  default_lower_threshold: number | null
  default_upper_threshold: number | null
  is_required: boolean
  is_enabled: boolean
  display_order: number
}

export interface ActuatorModelFeedback extends ActuatorModelFeedbackInput {
  id: number
  sensor_model_code: string
  sensor_model_name: string
}

export interface ActuatorModelInput {
  code: string
  name: string
  description?: string
  data_type?: "BOOLEAN"
  default_state?: boolean
  is_active?: boolean
  feedbacks?: ActuatorModelFeedbackInput[]
}
