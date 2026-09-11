import type { QueryClient, QueryKey } from "@tanstack/react-query";

import { queryKeys, type QueryScope } from "@/shared/api/query-keys";

async function invalidate(client: QueryClient, keys: readonly QueryKey[]) {
  const unique = new Map(
    keys.map((queryKey) => [JSON.stringify(queryKey), queryKey]),
  );
  await Promise.all(
    [...unique.values()].map((queryKey) =>
      client.invalidateQueries({ queryKey, refetchType: "active" }),
    ),
  );
}

export const invalidateQueries = {
  users: (client: QueryClient, scope: QueryScope, userId?: number) =>
    invalidate(client, [
      queryKeys.users.all,
      userId === undefined
        ? queryKeys.users.detailRoot
        : queryKeys.users.detail(scope, userId),
      userId === undefined
        ? queryKeys.users.projectsRoot
        : queryKeys.users.projects(scope, userId),
      queryKeys.adminOverview.all,
      queryKeys.adminMonitoringProjects.all,
      queryKeys.alerts.adminRoot,
      queryKeys.users.members,
    ]),

  projects: (
    client: QueryClient,
    scope: QueryScope,
    projectId: number,
    ownerUserId?: number,
  ) =>
    invalidate(client, [
      queryKeys.projects.all,
      queryKeys.projects.detail(scope, projectId),
      ownerUserId === undefined
        ? queryKeys.users.projectsRoot
        : queryKeys.users.projects(scope, ownerUserId),
      queryKeys.projects.devices(scope, projectId),
      queryKeys.projects.monitoring(scope, projectId),
      queryKeys.projects.telemetry(scope, projectId),
      queryKeys.adminOverview.all,
      queryKeys.adminMonitoringProjects.all,
      queryKeys.alerts.adminRoot,
    ]),

  devices: (
    client: QueryClient,
    scope: QueryScope,
    projectId: number,
    deviceId?: number,
    ownerUserId?: number,
  ) =>
    invalidate(client, [
      queryKeys.projects.devices(scope, projectId),
      deviceId === undefined
        ? queryKeys.devices.detailRoot
        : queryKeys.devices.detail(scope, projectId, deviceId),
      deviceId === undefined
        ? queryKeys.devices.sensorsRoot
        : queryKeys.devices.sensors(scope, projectId, deviceId),
      deviceId === undefined
        ? queryKeys.devices.mqttConfigRoot
        : queryKeys.devices.mqttConfig(scope, projectId, deviceId),
      queryKeys.actuators.all,
      queryKeys.projects.detail(scope, projectId),
      queryKeys.projects.monitoring(scope, projectId),
      queryKeys.projects.telemetry(scope, projectId),
      ownerUserId === undefined
        ? queryKeys.users.projectsRoot
        : queryKeys.users.projects(scope, ownerUserId),
      queryKeys.adminOverview.all,
      queryKeys.adminMonitoringProjects.all,
      queryKeys.alerts.adminRoot,
      queryKeys.alerts.all,
    ]),

  sensors: (
    client: QueryClient,
    scope: QueryScope,
    projectId: number | undefined,
    deviceId: number,
    sensorId?: number,
  ) =>
    invalidate(client, [
      projectId === undefined
        ? queryKeys.devices.sensorsRoot
        : queryKeys.devices.sensors(scope, projectId, deviceId),
      sensorId === undefined || projectId === undefined
        ? queryKeys.sensors.detailRoot
        : queryKeys.sensors.detail(scope, projectId, deviceId, sensorId),
      sensorId === undefined || projectId === undefined
        ? queryKeys.sensors.historyRoot
        : queryKeys.sensors.history(scope, projectId, deviceId, sensorId),
      queryKeys.sensors.all,
      queryKeys.telemetry.all,
      ...(projectId === undefined
        ? [
            queryKeys.projects.devicesRoot,
            queryKeys.projects.monitoringRoot,
            queryKeys.projects.telemetryRoot,
          ]
        : [
            queryKeys.projects.devices(scope, projectId),
            queryKeys.projects.monitoring(scope, projectId),
            queryKeys.projects.telemetry(scope, projectId),
          ]),
      queryKeys.adminOverview.all,
      queryKeys.adminMonitoringProjects.all,
      queryKeys.alerts.adminRoot,
      queryKeys.alerts.all,
    ]),

  projectMembers: (
    client: QueryClient,
    scope: QueryScope,
    projectId: number,
    userId?: number,
  ) =>
    invalidate(client, [
      queryKeys.projects.members(scope, projectId),
      queryKeys.projects.detail(scope, projectId),
      userId === undefined
        ? queryKeys.users.projectsRoot
        : queryKeys.users.projects(scope, userId),
      userId === undefined
        ? queryKeys.users.detailRoot
        : queryKeys.users.detail(scope, userId),
    ]),

  alerts: (
    client: QueryClient,
    scope: QueryScope,
    projectId?: number,
    alertId?: number,
  ) =>
    invalidate(client, [
      queryKeys.alerts.all,
      queryKeys.alerts.adminRoot,
      alertId === undefined
        ? queryKeys.alerts.adminDetailRoot
        : queryKeys.alerts.adminDetail(alertId),
      ...(projectId === undefined
        ? [
            queryKeys.projects.alertsRoot,
            queryKeys.projects.detailRoot,
            queryKeys.projects.monitoringRoot,
          ]
        : [
            queryKeys.projects.alerts(scope, projectId),
            queryKeys.projects.detail(scope, projectId),
            queryKeys.projects.monitoring(scope, projectId),
          ]),
      queryKeys.adminOverview.all,
      queryKeys.adminMonitoringProjects.all,
    ]),

  deviceTemplates: (client: QueryClient) =>
    invalidate(client, [queryKeys.deviceTemplates.all]),
  actuatorModels: (client: QueryClient, scope?: QueryScope) =>
    invalidate(client, [
      queryKeys.actuatorModels.all,
      ...(scope ? [queryKeys.actuatorModels.list(scope)] : []),
    ]),
};
