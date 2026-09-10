import type {
  Alert,
  MonitoringActuator as CanonicalMonitoringActuator,
  MonitoringDevice as CanonicalMonitoringDevice,
  MonitoringLatest,
} from "@/api/contracts"
import type {
  CoreId,
  MonitoringActuator,
  MonitoringDevice,
  MonitoringSensor,
  ProjectMonitoringSummary,
} from "@/entities/telemetry/model/project-monitoring"
import type {
  ProjectAttention,
  ProjectDeviceHealth,
  ProjectMeasurementGroup,
  ProjectRecentAlert,
} from "@/entities/project/model/types"

const ACTIVE_ALERT_STATUSES = new Set(["OPEN", "ACKNOWLEDGED"])
const VALID_QUALITIES = new Set(["VALID", "OUT_OF_RANGE", "INVALID", "UNVALIDATED", "NO_DATA"])
const CONNECTION_STATUSES = new Set(["WAITING_CONNECTION", "ONLINE", "OFFLINE", "DISABLED"])
const THRESHOLD_STATES = new Set(["BELOW", "NORMAL", "ABOVE", "UNCONFIGURED"])

function connectionStatus(value: string): MonitoringDevice["connection_status"] {
  return CONNECTION_STATUSES.has(value) ? value as MonitoringDevice["connection_status"] : "WAITING_CONNECTION"
}

function quality(value: string | null | undefined): NonNullable<MonitoringSensor["latest"]>["quality"] {
  return value && VALID_QUALITIES.has(value)
    ? value as NonNullable<MonitoringSensor["latest"]>["quality"]
    : "UNVALIDATED"
}

function freshness(value: string | null | undefined): NonNullable<MonitoringSensor["latest"]>["freshness"] {
  return value === "FRESH" || value === "STALE" || value === "NO_DATA" ? value : "NO_DATA"
}

function thresholdState(value: string | null | undefined): MonitoringSensor["threshold_state"] {
  return value && THRESHOLD_STATES.has(value)
    ? value as MonitoringSensor["threshold_state"]
    : "UNCONFIGURED"
}

function technicalSeverity(value: string): "WARNING" | "CRITICAL" {
  return value === "CRITICAL" ? "CRITICAL" : "WARNING"
}

function mapActuator(item: CanonicalMonitoringActuator): MonitoringActuator {
  return {
    id: item.id,
    code: item.code,
    name: item.name,
    actuator_model: item.actuator_model,
    connection_status: connectionStatus(item.connection_status),
    desired_state: item.desired_state,
    reported_state: item.reported_state,
    synchronization_status: item.synchronization_status,
    latest_command: item.latest_command,
    last_reported_at: item.last_reported_at,
    electrical: item.electrical,
    active_incident: item.active_alert
      ? {
          id: item.active_alert.id,
          technical_severity: technicalSeverity(item.active_alert.technical_severity),
          business_risk_level: item.active_alert.business_risk_level,
          status: item.active_alert.status,
          rule_name: item.active_alert.rule_name,
          evaluator_type: item.active_alert.evaluator_type,
          condition_summary: item.active_alert.condition_summary,
          started_at: item.active_alert.started_at,
          duration_seconds: item.active_alert.duration_seconds,
          evidence: item.active_alert.evidence,
        }
      : null,
  }
}

function mapDevice(item: CanonicalMonitoringDevice): MonitoringDevice {
  return {
    id: item.id,
    code: item.code,
    name: item.name,
    is_enabled: item.is_enabled,
    connection_status: connectionStatus(item.connection_status),
    location: item.location,
    last_seen_at: item.last_seen_at,
    sensors: item.sensors.map((sensor) => ({
      id: sensor.id,
      code: sensor.code,
      name: sensor.name,
      unit: sensor.unit,
      is_enabled: sensor.is_enabled,
      connection_status: connectionStatus(sensor.connection_status),
      data_status: connectionStatus(sensor.data_status),
      latest: sensor.latest && sensor.latest.value !== null
        ? {
            value: sensor.latest.value,
            recorded_at: sensor.latest.recorded_at ?? "",
            quality: quality(sensor.latest.quality),
            quality_reason: sensor.latest.quality_reason,
            engineering_min: sensor.latest.engineering_min,
            engineering_max: sensor.latest.engineering_max,
            freshness: freshness(sensor.latest.freshness),
          }
        : null,
      lower_threshold: sensor.lower_threshold,
      upper_threshold: sensor.upper_threshold,
      threshold_state: thresholdState(sensor.threshold_state),
      alerts_enabled: sensor.alerts_enabled ?? false,
    })),
    actuators: item.actuators.map(mapActuator),
  }
}

function latestTimestamp(devices: MonitoringDevice[]): string | null {
  const values = devices.flatMap((device) => [
    device.last_seen_at,
    ...device.sensors.map((sensor) => sensor.latest?.recorded_at ?? null),
    ...device.actuators.map((actuator) => actuator.last_reported_at),
  ]).filter((value): value is string => Boolean(value))
  if (!values.length) return null
  return values.sort((left, right) => Date.parse(right) - Date.parse(left))[0] ?? null
}

function buildMeasurementGroups(devices: MonitoringDevice[]): ProjectMeasurementGroup[] {
  const groups = new Map<string, Array<{ deviceId: CoreId; sensor: MonitoringSensor }>>()
  for (const device of devices) {
    for (const sensor of device.sensors.filter((candidate) => candidate.is_enabled)) {
      const key = `${sensor.name.trim().toLocaleLowerCase("vi-VN")}::${sensor.unit}`
      const items = groups.get(key) ?? []
      items.push({ deviceId: device.id, sensor })
      groups.set(key, items)
    }
  }

  return [...groups.entries()].map(([key, items]) => {
    const readings = items
      .filter((item) => item.sensor.latest?.value != null)
      .sort((left, right) => Date.parse(right.sensor.latest?.recorded_at ?? "") - Date.parse(left.sensor.latest?.recorded_at ?? ""))
    const latest = readings[0] ?? items[0]
    const values = readings.map((item) => item.sensor.latest?.value).filter((value): value is number => value != null)
    const reporting = items.filter(({ sensor }) => sensor.latest?.freshness === "FRESH" && sensor.latest?.value != null).length
    return {
      model_code: latest?.sensor.code ?? key,
      name: latest?.sensor.name ?? "Cảm biến",
      unit: latest?.sensor.unit ?? "",
      reporting_sensors: reporting,
      expected_sensors: items.length,
      latest_value: latest?.sensor.latest?.value ?? null,
      minimum_value: values.length ? Math.min(...values) : null,
      maximum_value: values.length ? Math.max(...values) : null,
      latest_at: latest?.sensor.latest?.recorded_at ?? null,
      stale: Boolean(latest?.sensor.latest && latest.sensor.latest.freshness !== "FRESH"),
      counter: /(^|[-_])ENERGY([-_]|$)|\bWH\b/i.test(latest?.sensor.code ?? "") || latest?.sensor.unit === "Wh",
      sensor_id: latest?.sensor.id ?? null,
      device_id: latest?.deviceId ?? null,
      quality: latest?.sensor.latest?.quality,
      quality_reason: latest?.sensor.latest?.quality_reason,
      engineering_min: latest?.sensor.latest?.engineering_min,
      engineering_max: latest?.sensor.latest?.engineering_max,
    }
  }).sort((left, right) => left.name.localeCompare(right.name, "vi"))
}

function buildAttention(devices: MonitoringDevice[], alerts: Alert[]): ProjectAttention[] {
  const result: ProjectAttention[] = []
  const deviceById = new Map(devices.map((device) => [device.id, device]))

  for (const alert of alerts.filter((item) => ACTIVE_ALERT_STATUSES.has(item.status))) {
    const device = alert.device_id ? deviceById.get(alert.device_id) : undefined
    const sensor = device?.sensors.find((item) => item.id === alert.sensor_id)
    const actuator = device?.actuators.find((item) => item.id === alert.actuator_id)
    result.push({
      id: `alert-${alert.id}`,
      severity: alert.severity,
      title: `${sensor?.name ?? actuator?.name ?? alert.resource_type} · ${device?.name ?? "Hệ thống"}`,
      description: alert.message,
      device_id: alert.device_id,
      sensor_id: alert.sensor_id,
      last_seen_at: alert.last_triggered_at || alert.started_at,
    })
  }

  for (const device of devices.filter((item) => item.is_enabled && item.connection_status === "OFFLINE")) {
    result.push({
      id: `device-offline-${device.id}`,
      severity: "WARNING",
      title: `${device.name} mất kết nối`,
      description: "Thiết bị đang ngoại tuyến; dữ liệu cuối vẫn được giữ để đối chiếu.",
      device_id: device.id,
      sensor_id: null,
      last_seen_at: device.last_seen_at,
    })
  }

  for (const device of devices) {
    for (const sensor of device.sensors.filter((item) => item.is_enabled && (item.latest?.freshness === "STALE" || !item.latest))) {
      if (result.length >= 14) break
      result.push({
        id: `sensor-freshness-${sensor.id}`,
        severity: "WARNING",
        title: `${sensor.name} · ${device.name}`,
        description: sensor.latest ? "Dữ liệu cảm biến đã cũ." : "Cảm biến chưa có dữ liệu mới.",
        device_id: device.id,
        sensor_id: sensor.id,
        last_seen_at: sensor.latest?.recorded_at ?? device.last_seen_at,
      })
    }
    if (result.length >= 14) break
  }

  return result.slice(0, 14)
}

function buildRecentAlerts(devices: MonitoringDevice[], alerts: Alert[]): ProjectRecentAlert[] {
  const deviceById = new Map(devices.map((device) => [device.id, device]))
  return alerts
    .filter((alert) => alert.sensor_id !== null && alert.device_id !== null)
    .sort((left, right) => Date.parse(right.started_at) - Date.parse(left.started_at))
    .slice(0, 8)
    .map((alert) => {
      const device = deviceById.get(alert.device_id!)
      const sensor = device?.sensors.find((item) => item.id === alert.sensor_id)
      return {
        id: alert.id,
        sensor_id: alert.sensor_id!,
        sensor_name: sensor?.name ?? `Sensor #${alert.sensor_id}`,
        device_id: alert.device_id!,
        device_name: device?.name ?? `Device #${alert.device_id}`,
        severity: alert.severity,
        status: alert.status,
        message: alert.message,
        trigger_value: alert.actual_value,
        condition_active: alert.condition_active,
        normalized_at: alert.normalized_at,
        resolved_by_user_id: alert.resolved_by_user_id,
        started_at: alert.started_at,
      }
    })
}

export function adaptCanonicalMonitoring(latest: MonitoringLatest, alerts: Alert[]) {
  const devices = latest.devices.map(mapDevice)
  const enabledDevices = devices.filter((item) => item.is_enabled)
  const sensors = devices.flatMap((device) => device.sensors)
  const enabledSensors = sensors.filter((item) => item.is_enabled)
  const reportingSensors = enabledSensors.filter((item) => item.latest?.freshness === "FRESH" && item.latest?.value != null)
  const staleSensors = enabledSensors.filter((item) => item.latest?.freshness === "STALE")
  const noDataSensors = enabledSensors.filter((item) => !item.latest || item.latest.freshness === "NO_DATA")
  const activeAlerts = alerts.filter((item) => ACTIVE_ALERT_STATUSES.has(item.status))
  const criticalAlerts = activeAlerts.filter((item) => item.severity === "CRITICAL")
  const warningAlerts = activeAlerts.filter((item) => item.severity === "WARNING")
  const receivedAt = latestTimestamp(devices)

  const reasons: ProjectMonitoringSummary["health"]["reasons"] = []
  if (criticalAlerts.length) reasons.push({ code: "CRITICAL_ALERT", severity: "CRITICAL", message: `${criticalAlerts.length} cảnh báo nghiêm trọng đang hoạt động.` })
  const offlineDevices = enabledDevices.filter((item) => item.connection_status === "OFFLINE")
  if (offlineDevices.length) reasons.push({ code: "DEVICE_OFFLINE", severity: "WARNING", message: `${offlineDevices.length} thiết bị đang mất kết nối.` })
  if (staleSensors.length) reasons.push({ code: "SENSOR_STALE", severity: "WARNING", message: `${staleSensors.length} cảm biến có dữ liệu cũ.` })
  if (noDataSensors.length) reasons.push({ code: "SENSOR_NO_DATA", severity: "WARNING", message: `${noDataSensors.length} cảm biến chưa có dữ liệu.` })
  if (warningAlerts.length) reasons.push({ code: "WARNING_ALERT", severity: "WARNING", message: `${warningAlerts.length} cảnh báo cần theo dõi.` })

  const healthStatus: ProjectMonitoringSummary["health"]["status"] = criticalAlerts.length
    ? "CRITICAL"
    : enabledSensors.length > 0 && reportingSensors.length === 0
      ? "NO_DATA"
      : reasons.length
        ? "WARNING"
        : "HEALTHY"

  const deviceHealth: ProjectDeviceHealth[] = devices.map((device) => ({
    id: device.id,
    code: device.code,
    name: device.name,
    status: device.connection_status,
    is_enabled: device.is_enabled,
    last_seen_at: device.last_seen_at,
    sensor_count: device.sensors.length,
    reporting_sensor_count: device.sensors.filter((sensor) => sensor.latest?.freshness === "FRESH").length,
    stale_sensor_count: device.sensors.filter((sensor) => sensor.latest?.freshness === "STALE").length,
    offline_sensor_count: device.sensors.filter((sensor) => !sensor.latest || sensor.latest?.freshness === "NO_DATA").length,
    open_alert_count: activeAlerts.filter((alert) => alert.device_id === device.id).length,
  }))

  const summary: ProjectMonitoringSummary = {
    project_id: latest.aquaponics_system_id,
    health: { status: healthStatus, label: healthStatus, reasons },
    inventory: {
      devices_total: devices.length,
      devices_enabled: enabledDevices.length,
      devices_online: enabledDevices.filter((item) => item.connection_status === "ONLINE").length,
      devices_offline: offlineDevices.length,
      devices_waiting: enabledDevices.filter((item) => item.connection_status === "WAITING_CONNECTION").length,
      sensors_total: sensors.length,
      sensors_enabled: enabledSensors.length,
      sensors_reporting: reportingSensors.length,
      sensors_stale: staleSensors.length,
      sensors_offline: noDataSensors.length,
      members_total: 0,
    },
    alerts: {
      open_total: activeAlerts.length,
      critical_open: criticalAlerts.length,
      warning_open: warningAlerts.length,
    },
    freshness: {
      last_received_at: receivedAt,
      reporting_sensors: reportingSensors.length,
      expected_sensors: enabledSensors.length,
      coverage_ratio: enabledSensors.length ? reportingSensors.length / enabledSensors.length : 0,
    },
    attention: buildAttention(devices, alerts),
    measurement_groups: buildMeasurementGroups(devices),
    device_health: deviceHealth,
    recent_alerts: buildRecentAlerts(devices, alerts),
    actuators: [],
    actuator_inventory: {
      total: devices.reduce((total, device) => total + device.actuators.length, 0),
      online: devices.flatMap((device) => device.actuators).filter((item) => item.connection_status === "ONLINE").length,
    },
  }

  return { devices, summary }
}
