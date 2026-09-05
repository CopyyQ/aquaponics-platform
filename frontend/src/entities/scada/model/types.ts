export type ScadaConnectivity = "ONLINE" | "WAITING_CONNECTION" | "OFFLINE" | "UNKNOWN" | "DISABLED"
export type ScadaFreshness = "FRESH" | "STALE" | "NO_DATA"
export type ScadaQuality = "VALID" | "OUT_OF_RANGE" | "INVALID" | "UNVALIDATED"
export type ScadaEntityType = "DEVICE" | "SENSOR" | "ACTUATOR"
export type ScadaSymbolType =
  | "FISH_TANK" | "BIO_FILTER" | "GROW_BED" | "SUMP_TANK"
  | "CONTROLLER_DEVICE" | "ENERGY_MONITOR" | "WATER_PUMP" | "AIR_PUMP"
  | "VALVE" | "FAN" | "GROW_LIGHT" | "HEATER" | "GENERIC_ACTUATOR"
  | "PH_SENSOR" | "WATER_TEMPERATURE_SENSOR" | "ENVIRONMENT_TEMPERATURE_SENSOR"
  | "HUMIDITY_SENSOR" | "DISSOLVED_OXYGEN_SENSOR" | "EC_SENSOR" | "TDS_SENSOR"
  | "WATER_LEVEL_SENSOR" | "LIGHT_SENSOR" | "AIR_PRESSURE_SENSOR" | "GENERIC_SENSOR"

export interface ScadaBinding { entity_type: ScadaEntityType; entity_id: number }
export interface ScadaSymbol { id: string; type: ScadaSymbolType | string; label: string; position: [number, number, number]; binding?: ScadaBinding | null }
export interface ScadaConnection { id: string; type: "WATER_PIPE" | "AIR_PIPE"; source_symbol_id: string; target_symbol_id: string; flow_direction: "SOURCE_TO_TARGET"; active: boolean }
export interface ScadaLayout { schema_version: number; camera: Record<string, unknown>; symbols: ScadaSymbol[]; connections: ScadaConnection[] }

export interface ScadaInventoryDevice { id: number; code: string; name: string; device_template_id: number | null; template_code: string | null; device_kind: string; enabled: boolean; connectivity: ScadaConnectivity; last_seen_at: string | null }
export interface ScadaInventorySensor { id: number; code: string; name: string; sensor_model_code: string; unit: string; device_id: number; enabled: boolean }
export interface ScadaInventoryActuator { id: number; code: string; name: string; actuator_model_code: string | null; device_id: number; enabled: boolean }
export interface ScadaRuntimeSensor { id: number; value: number | null; recorded_at: string | null; received_at: string | null; freshness: ScadaFreshness; quality: ScadaQuality; quality_reason: string | null }
export interface ScadaRuntimeActuator { id: number; desired_state: boolean | null; reported_state: boolean | null; synchronization: "IN_SYNC" | "OUT_OF_SYNC" | "UNKNOWN"; command_status: string | null; command_time: string | null; last_ack_at: string | null; failure_reason: string | null }

export interface ScadaIssue {
  id: string; severity: "CRITICAL" | "HIGH" | "WARNING" | "INFO"; title: string
  root_cause: string; affected_entities: string[]; current_state: string; timestamp: string | null
  suggested_action: string; device_id: number | null; sensor_id: number | null; actuator_id: number | null
}

export interface ScadaUnplacedEntity { entity_type: ScadaEntityType; entity_id: number; name: string; code: string; parent_device_id: number | null; suggested_symbol_type: ScadaSymbolType | string; reason: string }

export interface ScadaRuntime {
  project: { id: number; name: string; code: string }
  dashboard: { id: number | null; status: "GENERATED" | "DRAFT" | "PUBLISHED"; version: number; schema_version: number }
  layout: ScadaLayout
  inventory: { devices: ScadaInventoryDevice[]; sensors: ScadaInventorySensor[]; actuators: ScadaInventoryActuator[]; energy_monitors: ScadaInventoryDevice[] }
  runtime: {
    devices: Array<{ id: number; connectivity: ScadaConnectivity; last_seen_at: string | null }>
    sensors: ScadaRuntimeSensor[]
    actuators: ScadaRuntimeActuator[]
    alerts: Array<{ id: number; sensor_id: number; device_id: number; severity: string; status: string; title: string; value: number | null; timestamp: string }>
  }
  energy_monitor_runtime: Array<{ device_id: number; current_power: number | null; output_voltage: number | null; input_voltage: number | null; load_current: number | null; input_current: number | null; energy_total: number | null; valid_measurements: number; expected_measurements: number; latest_received_at: string | null; issue_severity: string | null }>
  issues: ScadaIssue[]
  unplaced_entities: ScadaUnplacedEntity[]
  summary: {
    active_devices_total: number; connected_devices: number; waiting_devices: number; disconnected_devices: number; unknown_connectivity_devices: number; disabled_devices: number
    active_sensors_total: number; fresh_sensors: number; fresh_valid_sensors: number; fresh_invalid_sensors: number; stale_sensors: number; no_data_sensors: number; disabled_sensors: number
    active_actuators_total: number; actuators_on: number; actuators_off: number; actuators_out_of_sync: number; commands_pending: number; commands_failed: number; commands_timeout: number; disabled_actuators: number
    active_energy_monitors: number; connected_energy_monitors: number; open_alerts: number; critical_alerts: number; warning_alerts: number; unplaced_entities: number
  }
  updated_at: string
}

export interface ScadaLayoutMutationResponse { dashboard: ScadaRuntime["dashboard"]; layout: ScadaLayout; warnings: string[] }
