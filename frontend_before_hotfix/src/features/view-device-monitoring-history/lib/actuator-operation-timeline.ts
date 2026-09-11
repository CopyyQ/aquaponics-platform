import type {
  MonitoringActuatorElectricalPoint,
  MonitoringActuatorHistoryPoint,
} from "@/api/contracts";

export const ACTUATOR_CHART_MIN = 0;
export const ACTUATOR_CHART_MAX = 12;

export interface ActuatorOperationPoint {
  timestamp: string;
  time: number;
  reportedState: boolean | null;
  hasElectricalReading: boolean;
  voltageRaw: number | null;
  voltageVisual: number | null;
  currentRaw: number | null;
  currentVisual: number | null;
}

export function clampActuatorValue(value: number) {
  return Math.min(ACTUATOR_CHART_MAX, Math.max(ACTUATOR_CHART_MIN, value));
}

function time(value: string) {
  const parsed = Date.parse(value);
  return Number.isFinite(parsed) ? parsed : null;
}

export function buildActuatorOperationTimeline(
  states: MonitoringActuatorHistoryPoint[],
  readings: MonitoringActuatorElectricalPoint[],
): ActuatorOperationPoint[] {
  const stateByTime = new Map<number, boolean | null>();
  states.forEach((point) => {
    const at = time(point.recorded_at);
    if (at !== null) stateByTime.set(at, point.state);
  });
  const electricalByTime = new Map<number, MonitoringActuatorElectricalPoint>();
  readings.forEach((point) => {
    const at = time(point.recorded_at);
    if (at !== null) electricalByTime.set(at, point);
  });
  const timestamps = [
    ...new Set([...stateByTime.keys(), ...electricalByTime.keys()]),
  ].sort((a, b) => a - b);
  let reportedState: boolean | null = null;
  return timestamps.map((at) => {
    if (stateByTime.has(at)) reportedState = stateByTime.get(at) ?? null;
    const reading = electricalByTime.get(at);
    return {
      timestamp: new Date(at).toISOString(),
      time: at,
      reportedState,
      hasElectricalReading: reading !== undefined,
      voltageRaw: reading?.voltage_v ?? null,
      voltageVisual:
        reading?.voltage_v == null
          ? null
          : clampActuatorValue(reading.voltage_v),
      currentRaw: reading?.current_a ?? null,
      currentVisual:
        reading?.current_a == null
          ? null
          : clampActuatorValue(reading.current_a),
    };
  });
}

export function collapseStateTransitions(points: ActuatorOperationPoint[]) {
  return points.filter(
    (point, index) =>
      index === 0 || point.reportedState !== points[index - 1].reportedState,
  );
}
