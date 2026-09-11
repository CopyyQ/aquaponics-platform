import type { ConnectionStatus } from "@/entities/device/model/types";
import type { ElectricalFeedbackMetric } from "@/entities/project/model/types";

export interface Actuator {
  id: number;
  device_id: number;
  actuator_model_id: number | null;
  actuator_model: { code: string; name: string } | null;
  sequence_number: number;
  code: string;
  name: string;
  location: string | null;
  notes: string | null;
  is_enabled: boolean;
  desired_state: boolean | null;
  reported_state: boolean | null;
  last_command_at: string | null;
  last_reported_at: string | null;
  disabled_at: string | null;
  disabled_by_user_id: number | null;
  disabled_reason: string | null;
  removed_at: string | null;
  removed_by_user_id: number | null;
  removed_reason: string | null;
  created_at: string;
  updated_at: string;
  electrical_feedbacks: {
    voltage: ElectricalFeedbackMetric;
    current: ElectricalFeedbackMetric;
  } | null;
}

export type ActuatorConnectionStatus = ConnectionStatus;

export interface ActuatorFeedbackBinding {
  id: number;
  actuator_id: number;
  sensor_id: number;
  feedback_role: "SUPPLY_VOLTAGE" | "RUNNING_CURRENT";
  value_key: string;
  unit: string;
  data_type: "FLOAT";
  lower_threshold: number | null;
  upper_threshold: number | null;
  effective_lower_threshold: number | null;
  effective_upper_threshold: number | null;
  default_lower_threshold: number | null;
  default_upper_threshold: number | null;
  threshold_source: "ACTUATOR_OVERRIDE" | "MODEL_DEFAULT" | "NONE";
  is_enabled: boolean;
  created_at: string;
  updated_at: string;
}

export interface FeedbackSensorOption {
  id: number;
  code: string;
  name: string;
  device_id: number;
  device_code: string;
  device_name: string;
  sensor_model_id: number;
  sensor_model_code: string;
  sensor_model_name: string;
  unit: string;
  data_type: "FLOAT";
}

export type ActuatorFeedbackRole = ActuatorFeedbackBinding["feedback_role"];
