import type { ComponentType, ComponentProps } from "react"
import { SensorTelemetryChart } from "@/features/sensor-monitoring/components/SensorTelemetryChart"
import { DeviceStateTimeline, DissolvedOxygenChart, ElectricalConductivityChart, GenericSensorChart, PhSensorChart, TurbidityChart, WaterFlowChart, WaterLevelChart, WaterTemperatureChart } from "@/features/sensor-monitoring/components/charts/SensorCharts"

type SensorChart = ComponentType<Omit<ComponentProps<typeof SensorTelemetryChart>, "title" | "variant">>

export const sensorChartRegistry: Record<string, SensorChart> = {
  PH: PhSensorChart,
  WATER_TEMPERATURE: WaterTemperatureChart,
  TEMPERATURE: WaterTemperatureChart,
  DO: DissolvedOxygenChart,
  DISSOLVED_OXYGEN: DissolvedOxygenChart,
  EC: ElectricalConductivityChart,
  WATER_LEVEL: WaterLevelChart,
  FLOW: WaterFlowChart,
  WATER_FLOW: WaterFlowChart,
  TURBIDITY: TurbidityChart,
  AIR_HUMIDITY: GenericSensorChart,
  AIR_TEMPERATURE: GenericSensorChart,
  AIR_PRESSURE: GenericSensorChart,
  ILLUMINANCE: GenericSensorChart,
  PUMP: DeviceStateTimeline,
  RELAY: DeviceStateTimeline,
}

export function getSensorChart(modelCode?: string): SensorChart {
  return modelCode ? sensorChartRegistry[modelCode.toUpperCase()] ?? GenericSensorChart : GenericSensorChart
}
