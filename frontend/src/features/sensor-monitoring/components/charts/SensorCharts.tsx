import type { ComponentProps } from "react"
import { SensorTelemetryChart } from "@/features/sensor-monitoring/components/SensorTelemetryChart"

type Props = Omit<ComponentProps<typeof SensorTelemetryChart>, "title" | "variant">

export function PhSensorChart(props: Props) { return <SensorTelemetryChart {...props} title="Biểu đồ pH" variant="line" /> }
export function WaterTemperatureChart(props: Props) { return <SensorTelemetryChart {...props} title="Nhiệt độ nước" variant="smooth" /> }
export function DissolvedOxygenChart(props: Props) { return <SensorTelemetryChart {...props} title="Oxy hòa tan" variant="line" /> }
export function ElectricalConductivityChart(props: Props) { return <SensorTelemetryChart {...props} title="Độ dẫn điện EC" variant="smooth" /> }
export function WaterLevelChart(props: Props) { return <SensorTelemetryChart {...props} title="Mực nước" variant="step" /> }
export function WaterFlowChart(props: Props) { return <SensorTelemetryChart {...props} title="Lưu lượng nước" variant="area" /> }
export function TurbidityChart(props: Props) { return <SensorTelemetryChart {...props} title="Độ đục" variant="line" /> }
export function DeviceStateTimeline(props: Props) { return <SensorTelemetryChart {...props} title="Trạng thái thiết bị" variant="state" /> }
export function GenericSensorChart(props: Props) { return <SensorTelemetryChart {...props} title="Dữ liệu cảm biến" variant="line" /> }
