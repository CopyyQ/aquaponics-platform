import { describe, expect, it } from "vitest"
import { GenericSensorChart } from "@/features/sensor-monitoring/components/charts/SensorCharts"
import { getSensorChart } from "@/features/sensor-monitoring/model/sensorChartRegistry"

describe("environmental sensor chart registry", () => {
  it.each(["AIR_HUMIDITY", "AIR_TEMPERATURE", "AIR_PRESSURE", "ILLUMINANCE"])(
    "uses the generic time-series chart for %s",
    (modelCode) => {
      expect(getSensorChart(modelCode)).toBe(GenericSensorChart)
    },
  )
})
