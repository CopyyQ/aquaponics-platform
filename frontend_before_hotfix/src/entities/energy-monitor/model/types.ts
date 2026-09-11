import type { MonitoringRange } from "@/entities/telemetry/model/project-monitoring";

export interface EnergyMeasurement {
  sensor_id: number | null;
  sensor_code: string | null;
  model_code: string;
  name: string;
  unit: string;
  semantics: "GAUGE" | "COUNTER";
  raw_value: number | null;
  display_value: number | null;
  freshness: "FRESH" | "STALE" | "NO_DATA";
  quality: "VALID" | "OUT_OF_RANGE" | "INVALID" | "UNVALIDATED" | "NO_DATA";
  quality_reason: string | null;
  engineering_min: number | null;
  engineering_max: number | null;
  recorded_at: string | null;
  received_at: string | null;
}

export interface EnergyOverview {
  device: {
    id: number; code: string; name: string; device_kind: "ENERGY_MONITOR";
    enabled: boolean; connectivity: string; last_seen_at: string | null;
    last_received_at: string | null; last_valid_recorded_at: string | null;
    template: { code: string; name: string; nominal_output_voltage_v: number | null };
  };
  measurements: Record<string, EnergyMeasurement>;
  data_health: { expected_measurements: number; fresh_measurements: number; valid_measurements: number; invalid_measurements: number; missing_measurements: number };
  energy_consumption: { last_1h_wh: number | null; last_6h_wh: number | null; last_12h_wh: number | null; last_24h_wh: number | null; month_to_date_wh: number | null };
  issues: Array<{ code: string; severity: string; message: string; sensor_id: number | null }>;
}

export interface EnergyPowerSeries {
  device_id: number;
  sensor: { id: number; code: string; model_code: "POWER_W"; unit: string };
  range: MonitoringRange;
  resolution: string;
  timezone: string;
  points: Array<{ bucket_time: string; avg_value: number; min_value: number; max_value: number; sample_count: number; partial: boolean }>;
}
