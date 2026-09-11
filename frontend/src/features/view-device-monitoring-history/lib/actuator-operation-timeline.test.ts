import { describe, expect, it } from "vitest";
import {
  buildActuatorOperationTimeline,
  clampActuatorValue,
  collapseStateTransitions,
} from "./actuator-operation-timeline";

const state = (recorded_at: string, value: boolean) => ({
  recorded_at,
  state: value,
});
const reading = (
  recorded_at: string,
  voltage_v: number | null,
  current_a: number | null,
) => ({ recorded_at, voltage_v, current_a, quality: "VALID" });

describe("actuator operation timeline", () => {
  it("sorts state changes and preserves step durations", () => {
    const result = buildActuatorOperationTimeline(
      [
        state("2026-09-07T10:15:00Z", false),
        state("2026-09-07T10:00:00Z", false),
        state("2026-09-07T10:05:00Z", true),
      ],
      [],
    );
    expect(result.map((point) => point.reportedState)).toEqual([
      false,
      true,
      false,
    ]);
  });
  it("collapses repeated states without fake transitions", () => {
    const result = collapseStateTransitions(
      buildActuatorOperationTimeline(
        [
          state("2026-09-07T10:00:00Z", true),
          state("2026-09-07T10:01:00Z", true),
          state("2026-09-07T10:02:00Z", true),
        ],
        [],
      ),
    );
    expect(result).toHaveLength(1);
  });
  it("clamps geometry but retains raw electrical values", () => {
    const [point] = buildActuatorOperationTimeline(
      [],
      [reading("2026-09-07T10:00:00Z", 12.41, 1.45)],
    );
    expect(point).toMatchObject({
      voltageRaw: 12.41,
      voltageVisual: 12,
      currentRaw: 1.45,
      currentVisual: 1.45,
    });
    expect(clampActuatorValue(-2)).toBe(0);
    expect(clampActuatorValue(15)).toBe(12);
  });
  it("keeps zero at the chart bottom and null state unknown", () => {
    const [point] = buildActuatorOperationTimeline(
      [],
      [reading("2026-09-07T10:00:00Z", null, 0)],
    );
    expect(point).toMatchObject({ reportedState: null, currentVisual: 0 });
  });
  it("resolves duplicate timestamps deterministically with the last input", () => {
    const [point] = buildActuatorOperationTimeline(
      [
        state("2026-09-07T10:00:00Z", false),
        state("2026-09-07T10:00:00Z", true),
      ],
      [
        reading("2026-09-07T10:00:00Z", 5, 1),
        reading("2026-09-07T10:00:00Z", 6, 2),
      ],
    );
    expect(point).toMatchObject({
      reportedState: true,
      voltageRaw: 6,
      currentRaw: 2,
    });
  });
});
