export interface TemplateSensor {
  id: number;
  sensor_model_id: number;
  display_name: string | null;
  default_location: string | null;
  default_lower_threshold: number | null;
  default_upper_threshold: number | null;
  default_warning_enabled: boolean | null;
  default_below_threshold_message: string | null;
  default_above_threshold_message: string | null;
  default_alert_risk_level: "EXTREME" | "VERY_HIGH" | "HIGH" | "MEDIUM" | "LOW_MEDIUM" | "LOW" | null;
  sort_order: number;
  is_required: boolean;
  model_code: string;
  model_name: string;
  unit: string;
  value_type: string;
  chart_type: string;
  measurement_semantics: "GAUGE" | "COUNTER";
}

export interface TemplateActuator {
  id: number;
  actuator_model_id: number;
  code: string;
  default_name: string | null;
  default_location: string | null;
  default_notes: string | null;
  actuator_type: "SWITCH" | "PUMP" | "VALVE" | "LIGHT" | "ALARM" | "OTHER";
  default_state: boolean | null;
  command_capability: "ON_OFF";
  monitor_current: boolean;
  electrical_profile_id: number | null;
  electrical_profile_code: string | null;
  electrical_profile_name: string | null;
  sort_order: number;
  is_required: boolean;
  is_enabled: boolean;
  model_code: string;
  model_name: string;
}

export interface TemplateActuatorInput {
  actuator_model_id: number;
  code: string;
  default_name?: string;
  default_location?: string;
  default_notes?: string;
  actuator_type: TemplateActuator["actuator_type"];
  default_state: boolean | null;
  command_capability: "ON_OFF";
  monitor_current: boolean;
  electrical_profile_id: number | null;
  sort_order: number;
  is_required: boolean;
  is_enabled: boolean;
}

export type TemplateActuatorUpdate = Partial<
  Omit<TemplateActuatorInput, "actuator_model_id">
>;

export interface ActuatorCurrentProfile {
  id: number;
  code: string;
  name: string;
  actuator_model_ids: number[];
}

export interface DeviceTemplate {
  id: number;
  code: string;
  name: string;
  description: string | null;
  notes: string | null;
  device_kind: "GENERIC" | "ENERGY_MONITOR";
  nominal_output_voltage_v: number | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
  sensors: TemplateSensor[];
  actuators: TemplateActuator[];
}

export interface DeviceTemplateList {
  items: DeviceTemplate[];
  total: number;
  page: number;
  page_size: number;
}

export interface DeviceTemplateInput {
  code: string;
  name: string;
  description?: string;
  notes?: string;
  device_kind?: "GENERIC" | "ENERGY_MONITOR";
  nominal_output_voltage_v?: number;
  is_active?: boolean;
}

export interface TemplateSensorInput {
  sensor_model_id: number;
  display_name?: string;
  default_location?: string;
  default_lower_threshold?: number | null;
  default_upper_threshold?: number | null;
  default_warning_enabled?: boolean | null;
  default_below_threshold_message?: string | null;
  default_above_threshold_message?: string | null;
  default_alert_risk_level?: "EXTREME" | "VERY_HIGH" | "HIGH" | "MEDIUM" | "LOW_MEDIUM" | "LOW" | null;
  sort_order: number;
  is_required: boolean;
}

export type TemplateSensorUpdate = Partial<
  Omit<TemplateSensorInput, "sensor_model_id">
>;
