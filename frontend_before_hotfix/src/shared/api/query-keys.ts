export type QueryPrimitive = string | number | boolean | null | undefined;
export type QueryFilter = Readonly<Record<string, QueryPrimitive>>;
export type QueryKeyPart = QueryPrimitive | object | readonly QueryPrimitive[];
export type QueryScope = readonly QueryPrimitive[];

const scoped = (
  root: string,
  scope: QueryScope,
  ...parts: readonly QueryKeyPart[]
) => [root, ...scope, ...parts] as const;

export const queryKeys = {
  user: {
    overview: (scope: QueryScope) => scoped("user-overview", scope),
    monitoring: (scope: QueryScope, filters?: object) =>
      scoped("user-monitoring", scope, filters),
  },
  adminOverview: {
    all: ["admin-overview"] as const,
    detail: (scope: QueryScope) => scoped("admin-overview", scope),
  },
  adminMonitoringProjects: {
    all: ["admin-monitoring-projects"] as const,
    list: (scope: QueryScope, filters?: object) =>
      scoped("admin-monitoring-projects", scope, filters),
  },
  users: {
    all: ["admin-users"] as const,
    list: (scope: QueryScope, ...filters: readonly QueryKeyPart[]) =>
      scoped("admin-users", scope, ...filters),
    detailRoot: ["admin-user"] as const,
    detail: (scope: QueryScope, userId: number) =>
      scoped("admin-user", scope, userId),
    projectsRoot: ["admin-user-projects"] as const,
    projects: (scope: QueryScope, userId: number) =>
      scoped("admin-user-projects", scope, userId),
    activityRoot: ["admin-user-activity"] as const,
    activity: (scope: QueryScope, userId: number) =>
      scoped("admin-user-activity", scope, userId),
    members: ["members"] as const,
    availableMembers: (projectId: number) =>
      ["members", "available", projectId] as const,
  },
  projects: {
    all: ["projects"] as const,
    list: (scope: QueryScope, ...filters: readonly QueryKeyPart[]) =>
      scoped("projects", scope, ...filters),
    detailRoot: ["project"] as const,
    detail: (scope: QueryScope, projectId: number) =>
      scoped("project", scope, projectId),
    devicesRoot: ["project-devices"] as const,
    devices: (scope: QueryScope, projectId: number, options?: QueryFilter) =>
      scoped("project-devices", scope, projectId, options),
    membersRoot: ["project-members"] as const,
    members: (scope: QueryScope, projectId: number, filters?: QueryFilter) =>
      scoped("project-members", scope, projectId, filters),
    monitoringRoot: ["project-monitoring"] as const,
    monitoringLatest: (scope: QueryScope, projectId: number) =>
      scoped("project-monitoring", scope, projectId, "inventory"),
    monitoringSeries: (scope: QueryScope, projectId: number, range: string) =>
      scoped("project-monitoring", scope, projectId, "series", range),
    summary: (scope: QueryScope, projectId: number) =>
      scoped("project-monitoring-summary", scope, projectId),
    deviceSensorSeries: (
      scope: QueryScope,
      projectId: number,
      deviceId: number,
      range: string,
    ) => scoped("project-monitoring", scope, projectId, deviceId, "sensor-series", range),
    deviceActuatorHistory: (
      scope: QueryScope,
      projectId: number,
      deviceId: number,
      range: string,
    ) => scoped("project-monitoring", scope, projectId, deviceId, "actuator-history", range),
    monitoring: (scope: QueryScope, projectId: number) =>
      scoped("project-monitoring", scope, projectId),
    telemetryRoot: ["project-telemetry"] as const,
    telemetry: (
      scope: QueryScope,
      projectId: number,
      ...filters: readonly QueryKeyPart[]
    ) => scoped("project-telemetry", scope, projectId, ...filters),
    alertsRoot: ["project-alerts"] as const,
    alerts: (
      scope: QueryScope,
      projectId: number,
      ...filters: readonly QueryKeyPart[]
    ) => scoped("project-alerts", scope, projectId, ...filters),
    scadaRuntime: (scope: QueryScope, projectId: number) => scoped("project-scada-runtime", scope, projectId),
  },
  devices: {
    all: ["devices"] as const,
    list: (scope: QueryScope, ...filters: readonly QueryKeyPart[]) =>
      scoped("devices", scope, ...filters),
    detailRoot: ["device"] as const,
    detail: (scope: QueryScope, projectId: number, deviceId: number) =>
      scoped("device", scope, projectId, deviceId),
    sensorsRoot: ["device-sensors"] as const,
    sensors: (scope: QueryScope, projectId: number, deviceId: number) =>
      scoped("device-sensors", scope, projectId, deviceId),
    mqttConfigRoot: ["device-mqtt-config"] as const,
    mqttConfig: (scope: QueryScope, projectId: number, deviceId: number) =>
      scoped("device-mqtt-config", scope, projectId, deviceId),
  },
  energyMonitor: {
    overview: (scope: QueryScope, projectId: number, deviceId: number) =>
      scoped("energy-monitor-overview", scope, projectId, deviceId),
    powerSeries: (scope: QueryScope, projectId: number, deviceId: number, range: string) =>
      scoped("energy-monitor-power-series", scope, projectId, deviceId, range),
  },
  sensors: {
    all: ["sensors"] as const,
    list: (scope: QueryScope, ...filters: readonly QueryKeyPart[]) =>
      scoped("sensors", scope, ...filters),
    detailRoot: ["sensor"] as const,
    detail: (
      scope: QueryScope,
      projectId: number,
      deviceId: number,
      sensorId: number,
    ) => scoped("sensor", scope, projectId, deviceId, sensorId),
    historyRoot: ["sensor-history"] as const,
    history: (
      scope: QueryScope,
      projectId: number,
      deviceId: number,
      sensorId: number,
      ...filters: readonly QueryKeyPart[]
    ) =>
      scoped(
        "sensor-history",
        scope,
        projectId,
        deviceId,
        sensorId,
        ...filters,
      ),
  },
  actuators: {
    all: ["actuators"] as const,
    list: (scope: QueryScope, projectId: number, deviceId: number) =>
      scoped("actuators", scope, projectId, deviceId),
  },
  sensorModels: {
    all: ["sensor-models"] as const,
    list: (scope: QueryScope) => scoped("sensor-models", scope),
  },
  actuatorModels: {
    all: ["actuator-models"] as const,
    list: (scope: QueryScope) => scoped("actuator-models", scope),
  },
  alerts: {
    all: ["alerts"] as const,
    list: (scope: QueryScope, ...filters: readonly QueryKeyPart[]) =>
      scoped("alerts", scope, ...filters),
    adminRoot: ["admin-alerts"] as const,
    adminList: (scope: QueryScope, filters?: object) =>
      scoped("admin-alerts", scope, filters),
    adminDetailRoot: ["admin-alert"] as const,
    adminDetail: (alertId: number) => ["admin-alert", alertId] as const,
  },
  telemetry: {
    all: ["telemetry"] as const,
    latest: (scope: QueryScope) => scoped("telemetry", scope, "latest"),
    history: (scope: QueryScope, sensorId: number | undefined, range: string) =>
      scoped("telemetry", scope, "history", sensorId, range),
  },
  deviceTemplates: {
    all: ["device-templates"] as const,
    list: (...filters: readonly QueryKeyPart[]) =>
      ["device-templates", ...filters] as const,
  },
  auditLogs: ["audit-logs"] as const,
} as const;
