export type ConnectionStatus =
  | "WAITING_CONNECTION"
  | "ONLINE"
  | "OFFLINE"
  | "DISABLED";

export interface Device {
  id: number;
  project_id: number;
  device_template_id: number | null;
  device_kind: "GENERIC" | "ENERGY_MONITOR";
  template_code: string | null;
  template_name: string | null;
  nominal_output_voltage_v: number | null;
  code: string;
  name: string;
  description: string | null;
  location: string | null;
  status: ConnectionStatus;
  last_seen_at: string | null;
  is_enabled: boolean;
  disabled_at: string | null;
  disabled_by_user_id: number | null;
  disabled_reason: string | null;
  created_at: string;
  updated_at: string;
  sensor_count?: number;
  actuator_count?: number;
}

export interface DeviceCreateInput {
  device_template_id?: number;
  code: string;
  name: string;
  description?: string;
  location?: string;
  installation_location?: string;
  notes?: string;
  create_default_sensors?: boolean;
}

export interface MqttDeviceConfig {
  schema_version: "2.0";
  generated_at: string;
  config_version: string;
  configuration_hash: string;
  project: { code: string; name: string };
  device: {
    id: number;
    code: string;
    name: string;
    kind: "GENERIC" | "ENERGY_MONITOR";
    enabled: boolean;
    status: ConnectionStatus;
    template: { id: number; code: string; name: string; nominal_output_voltage_v: number | null } | null;
  };
  mqtt: {
    host: string;
    port: number;
    client_id: string;
    qos: number;
    topics: {
      telemetry: string;
      status: string;
      commands: string;
      command_ack: string;
    };
  };
  sensors: ConnectionSensor[];
  actuators: ConnectionActuator[];
  payload_contracts: Record<string, unknown>;
}

export interface ConnectionSensor {
  sensor_code: string;
  sensor_model_code: string;
  name: string;
  data_type: string;
  unit: string;
  location: string | null;
  is_enabled: true;
  measurement_semantics: "GAUGE" | "COUNTER";
  required: boolean;
}

export interface ConnectionActuator {
  id: number;
  actuator_code: string;
  actuator_model_code: string;
  name: string;
  data_type: "BOOLEAN";
  state_encoding: { off: false; on: true };
  default_state: boolean;
  location: string | null;
  is_enabled: true;
  feedbacks: ConnectionActuatorFeedback[];
}

export interface ConnectionActuatorFeedback {
  role: "SUPPLY_VOLTAGE" | "RUNNING_CURRENT";
  sensor_id: number;
  sensor_code: string;
  sensor_model_code: string;
  value_key: string;
  unit: string;
  data_type: "FLOAT";
  mqtt: { topic: string; payload: Record<string, unknown> };
}

export interface DeviceOverview {
  device: Device;
  owner: { id: number; full_name: string } | null;
  project: { id: number; name: string } | null;
  sensors: Array<{
    id: number;
    code: string;
    name: string;
    status: ConnectionStatus;
    last_seen_at: string | null;
    lower_threshold: number | null;
    upper_threshold: number | null;
  }>;
  last_received_at: string | null;
}
