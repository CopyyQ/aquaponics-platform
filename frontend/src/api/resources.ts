import { api } from "./client"
import type {
  Actuator, ActuatorCommand, ActuatorCommandCreate, ActuatorInput, ActuatorModel, ActuatorModelInput, ActuatorModelUpdate, ActuatorReading, ActuatorUpdate,
  ActivityList, Alert, AlertResolutionRequest, AlertSettings, AlertSettingsUpdate, AquaponicsSystem, AquaponicsSystemCreate, AquaponicsSystemUpdate,
  ChangePasswordRequest, Device, DeviceInput, DeviceTemplate, DeviceTemplateInput, DeviceTemplateUpdate, DeviceUpdate, Member, MemberCreate, MemberUpdate,
  MessageResponse, MonitoringActuatorHistoryRead, MonitoringLatest, MonitoringRange, MonitoringSeriesRead, MqttExport, ScadaLayout, ScadaLayoutMutationResponse, ScadaRuntimeResponse, Sensor, SensorInput, SensorModel, SensorModelInput,
  ActuatorThresholdMetric,
  SensorModelUpdate, SensorUpdate, Session, TelemetryReading, TemplateActuatorSlot, TemplateActuatorSlotInput, TemplateActuatorSlotUpdate, TemplateSensorSlot,
  TemplateSensorSlotInput, TemplateSensorSlotUpdate, ThresholdAlertConfig, ThresholdAlertConfigInput, TokenResponse, UserSelfUpdate, UserSummary,
  RoleSummary, ManagedUserCreate, ManagedUserUpdate, ManagedPasswordUpdate, AccountLifecycleRequest, SystemLifecycleRequest,
  AlertDeliverySettings, AlertDeliveryRecipient, AlertDeliveryRecipientInput, AlertDeliveryRecipientUpdate, AlertDeliveryTestResult, AlertDeliveryHistoryItem, PublicMonitoringSettings,
} from "./contracts"

export const endpoints = {
  authLogin: "/auth/login", session: "/auth/session", authMe: "/auth/me", changePassword: "/auth/change-password", logout: "/auth/logout",
  systems: "/aquaponics-systems", system: (systemId: number) => `/aquaponics-systems/${systemId}`,
  devices: (systemId: number) => `/aquaponics-systems/${systemId}/devices`, device: (systemId: number, deviceId: number) => `${endpoints.devices(systemId)}/${deviceId}`,
  sensors: (systemId: number, deviceId: number) => `${endpoints.device(systemId, deviceId)}/sensors`, sensor: (systemId: number, deviceId: number, sensorId: number) => `${endpoints.sensors(systemId, deviceId)}/${sensorId}`,
  sensorThreshold: (systemId: number, deviceId: number, sensorId: number) => `${endpoints.sensor(systemId, deviceId, sensorId)}/threshold-alert`, sensorTelemetry: (systemId: number, deviceId: number, sensorId: number) => `${endpoints.sensor(systemId, deviceId, sensorId)}/telemetry`,
  actuators: (systemId: number, deviceId: number) => `${endpoints.device(systemId, deviceId)}/actuators`, actuator: (systemId: number, deviceId: number, actuatorId: number) => `${endpoints.actuators(systemId, deviceId)}/${actuatorId}`,
  actuatorReadings: (systemId: number, deviceId: number, actuatorId: number) => `${endpoints.actuator(systemId, deviceId, actuatorId)}/readings`, actuatorCommands: (systemId: number, deviceId: number, actuatorId: number) => `${endpoints.actuator(systemId, deviceId, actuatorId)}/commands`,
  actuatorThreshold: (systemId: number, deviceId: number, actuatorId: number, metric: string) => `${endpoints.actuator(systemId, deviceId, actuatorId)}/threshold-alerts/${metric}`,
  alerts: (systemId: number) => `${endpoints.system(systemId)}/alerts`, alert: (systemId: number, alertId: number) => `${endpoints.alerts(systemId)}/${alertId}`,
  monitoringLatest: (systemId: number) => `${endpoints.system(systemId)}/monitoring/latest`, monitoringSeries: (systemId: number) => `${endpoints.system(systemId)}/monitoring/series`, monitoringActuatorHistory: (systemId: number, deviceId: number) => `${endpoints.device(systemId, deviceId)}/monitoring/actuator-history`,
  members: (systemId: number) => `${endpoints.system(systemId)}/members`, member: (systemId: number, userId: number) => `${endpoints.members(systemId)}/${userId}`, activities: (systemId: number) => `${endpoints.system(systemId)}/activities`,
  scada: (systemId: number) => `${endpoints.system(systemId)}/scada/runtime`, scadaDraft: (systemId: number) => `${endpoints.system(systemId)}/scada/layout/draft`, scadaPublish: (systemId: number) => `${endpoints.system(systemId)}/scada/layout/publish`,
  alertSettings: (systemId: number) => `${endpoints.alerts(systemId)}/settings`, mqttExport: (systemId: number) => `${endpoints.system(systemId)}/mqtt-config/export`,
  sensorModels: "/sensor-models", sensorModel: (id: number) => `/sensor-models/${id}`, actuatorModels: "/actuator-models", actuatorModel: (id: number) => `/actuator-models/${id}`,
  users: "/users", user: (id: number) => `/users/${id}`, templates: "/device-templates", template: (id: number) => `/device-templates/${id}`,
  templateSensors: (id: number) => `${endpoints.template(id)}/sensors`, templateSensor: (id: number, mappingId: number) => `${endpoints.templateSensors(id)}/${mappingId}`,
  templateActuators: (id: number) => `${endpoints.template(id)}/actuators`, templateActuator: (id: number, mappingId: number) => `${endpoints.templateActuators(id)}/${mappingId}`,
  roles: "/roles",
  systemDisable: (id: number) => `${endpoints.system(id)}/lifecycle/disable`, systemActivate: (id: number) => `${endpoints.system(id)}/lifecycle/activate`,
  userPassword: (id: number) => `${endpoints.user(id)}/password`, userForceLogout: (id: number) => `${endpoints.user(id)}/force-logout`,
  userLifecycle: (id: number, action: "activate" | "disable" | "lock" | "unlock" | "restore" | "soft-delete") => `${endpoints.user(id)}/${action}`,
  deliverySettings: (id: number) => `${endpoints.system(id)}/alert-delivery/settings`,
  deliveryRecipients: (id: number) => `${endpoints.system(id)}/alert-delivery/recipients`,
  deliveryRecipient: (id: number, recipientId: number) => `${endpoints.deliveryRecipients(id)}/${recipientId}`,
  deliveryRecipientTest: (id: number, recipientId: number) => `${endpoints.deliveryRecipient(id, recipientId)}/test`,
  deliveryHistory: (id: number) => `${endpoints.system(id)}/alert-delivery/history`,
  publicMonitoringSettings: (id: number) => `${endpoints.system(id)}/public-monitoring/settings`,
  publicMonitoringLatest: (slug: string) => `/public/aquaponics-systems/${encodeURIComponent(slug)}/monitoring/latest`,
  publicMonitoringSeries: (slug: string) => `/public/aquaponics-systems/${encodeURIComponent(slug)}/monitoring/series`,
} as const

export const queryKeys = {
  systems: ["aquaponics-systems"] as const, system: (id: number) => ["aquaponics-system", id] as const,
  devices: (systemId: number) => ["aquaponics-system", systemId, "devices"] as const, device: (systemId: number, id: number) => ["aquaponics-system", systemId, "device", id] as const,
  sensor: (systemId: number, deviceId: number, id: number) => ["aquaponics-system", systemId, "device", deviceId, "sensor", id] as const,
  sensorTelemetry: (systemId: number, deviceId: number, id: number, start?: string, end?: string, limit?: number) => ["aquaponics-system", systemId, "device", deviceId, "sensor", id, "telemetry", { start, end, limit }] as const,
  sensorThreshold: (systemId: number, deviceId: number, id: number) => ["aquaponics-system", systemId, "device", deviceId, "sensor", id, "threshold"] as const,
  actuator: (systemId: number, deviceId: number, id: number) => ["aquaponics-system", systemId, "device", deviceId, "actuator", id] as const,
  actuatorReadings: (systemId: number, deviceId: number, id: number, limit?: number) => ["aquaponics-system", systemId, "device", deviceId, "actuator", id, "readings", { limit }] as const,
  actuatorCommands: (systemId: number, deviceId: number, id: number, limit?: number) => ["aquaponics-system", systemId, "device", deviceId, "actuator", id, "commands", { limit }] as const,
  actuatorThreshold: (systemId: number, deviceId: number, id: number, metric: ActuatorThresholdMetric) => ["aquaponics-system", systemId, "device", deviceId, "actuator", id, "threshold", metric] as const,
  monitoringLatest: (id: number) => ["aquaponics-system", id, "monitoring", "latest"] as const, monitoringSeries: (id: number, range: MonitoringRange) => ["aquaponics-system", id, "monitoring", "series", range] as const, monitoringActuatorHistory: (id: number, deviceId: number, range: MonitoringRange) => ["aquaponics-system", id, "device", deviceId, "monitoring", "actuator-history", range] as const,
  alerts: (id: number) => ["aquaponics-system", id, "alerts"] as const, alert: (systemId: number, id: number) => ["aquaponics-system", systemId, "alert", id] as const, members: (id: number) => ["aquaponics-system", id, "members"] as const,
  activities: (id: number, params?: { page?: number; page_size?: number; action?: string; entity_type?: string }) => ["aquaponics-system", id, "activities", params ?? {}] as const, scada: (id: number) => ["aquaponics-system", id, "scada"] as const,
  alertSettings: (id: number) => ["aquaponics-system", id, "alert-settings"] as const,
  sensorModels: ["sensor-models"] as const, sensorModel: (id: number) => ["sensor-model", id] as const,
  actuatorModels: ["actuator-models"] as const, actuatorModel: (id: number) => ["actuator-model", id] as const,
  templates: ["device-templates"] as const, template: (id: number) => ["device-template", id] as const,
  users: ["users"] as const, user: (id: number) => ["user", id] as const, roles: ["roles"] as const,
  deliverySettings: (id: number) => ["aquaponics-system", id, "alert-delivery", "settings"] as const,
  deliveryHistory: (id: number) => ["aquaponics-system", id, "alert-delivery", "history"] as const,
  publicMonitoringSettings: (id: number) => ["aquaponics-system", id, "public-monitoring", "settings"] as const,
} as const

export async function login(username: string, password: string): Promise<TokenResponse> { return (await api.post<TokenResponse>(endpoints.authLogin, { username, password })).data }
export async function loadSession(): Promise<Session> { return (await api.get<Session>(endpoints.session)).data }
export async function updateProfile(payload: UserSelfUpdate): Promise<Session["user"]> { return (await api.patch<Session["user"]>(endpoints.authMe, payload)).data }
export async function changePassword(payload: ChangePasswordRequest): Promise<MessageResponse> { return (await api.post<MessageResponse>(endpoints.changePassword, payload)).data }
export async function logout(): Promise<MessageResponse> { return (await api.post<MessageResponse>(endpoints.logout)).data }

export async function listSystems(): Promise<AquaponicsSystem[]> { return (await api.get<AquaponicsSystem[]>(endpoints.systems)).data }
export async function createSystem(payload: AquaponicsSystemCreate): Promise<AquaponicsSystem> { return (await api.post<AquaponicsSystem>(endpoints.systems, payload)).data }
export async function getSystem(id: number): Promise<AquaponicsSystem> { return (await api.get<AquaponicsSystem>(endpoints.system(id))).data }
export async function updateSystem(id: number, payload: AquaponicsSystemUpdate): Promise<AquaponicsSystem> { return (await api.patch<AquaponicsSystem>(endpoints.system(id), payload)).data }
export async function deleteSystem(id: number): Promise<void> { await api.delete(endpoints.system(id)) }
export async function listDevices(systemId: number): Promise<Device[]> { return (await api.get<Device[]>(endpoints.devices(systemId))).data }
export async function createDevice(systemId: number, payload: DeviceInput): Promise<Device> { return (await api.post<Device>(endpoints.devices(systemId), payload)).data }
export async function getDevice(systemId: number, id: number): Promise<Device> { return (await api.get<Device>(endpoints.device(systemId, id))).data }
export async function updateDevice(systemId: number, id: number, payload: DeviceUpdate): Promise<Device> { return (await api.patch<Device>(endpoints.device(systemId, id), payload)).data }
export async function deleteDevice(systemId: number, id: number): Promise<void> { await api.delete(endpoints.device(systemId, id)) }

export async function listSensors(systemId: number, deviceId: number): Promise<Sensor[]> { return (await api.get<Sensor[]>(endpoints.sensors(systemId, deviceId))).data }
export async function createSensor(systemId: number, deviceId: number, payload: SensorInput): Promise<Sensor> { return (await api.post<Sensor>(endpoints.sensors(systemId, deviceId), payload)).data }
export async function getSensor(systemId: number, deviceId: number, id: number): Promise<Sensor> { return (await api.get<Sensor>(endpoints.sensor(systemId, deviceId, id))).data }
export async function updateSensor(systemId: number, deviceId: number, id: number, payload: SensorUpdate): Promise<Sensor> { return (await api.patch<Sensor>(endpoints.sensor(systemId, deviceId, id), payload)).data }
export async function deleteSensor(systemId: number, deviceId: number, id: number): Promise<void> { await api.delete(endpoints.sensor(systemId, deviceId, id)) }
export async function getSensorThreshold(systemId: number, deviceId: number, id: number): Promise<ThresholdAlertConfig | null> { return (await api.get<ThresholdAlertConfig | null>(endpoints.sensorThreshold(systemId, deviceId, id))).data }
export async function saveSensorThreshold(systemId: number, deviceId: number, id: number, payload: ThresholdAlertConfigInput): Promise<ThresholdAlertConfig> { return (await api.post<ThresholdAlertConfig>(endpoints.sensorThreshold(systemId, deviceId, id), payload)).data }
export async function updateSensorThreshold(systemId: number, deviceId: number, id: number, payload: ThresholdAlertConfigInput): Promise<ThresholdAlertConfig> { return (await api.patch<ThresholdAlertConfig>(endpoints.sensorThreshold(systemId, deviceId, id), payload)).data }
export async function deleteSensorThreshold(systemId: number, deviceId: number, id: number): Promise<void> { await api.delete(endpoints.sensorThreshold(systemId, deviceId, id)) }
export async function getSensorTelemetry(systemId: number, deviceId: number, id: number, params?: { start?: string; end?: string; limit?: number }): Promise<TelemetryReading[]> { return (await api.get<TelemetryReading[]>(endpoints.sensorTelemetry(systemId, deviceId, id), { params })).data }

export async function listActuators(systemId: number, deviceId: number): Promise<Actuator[]> { return (await api.get<Actuator[]>(endpoints.actuators(systemId, deviceId))).data }
export async function createActuator(systemId: number, deviceId: number, payload: ActuatorInput): Promise<Actuator> { return (await api.post<Actuator>(endpoints.actuators(systemId, deviceId), payload)).data }
export async function getActuator(systemId: number, deviceId: number, id: number): Promise<Actuator> { return (await api.get<Actuator>(endpoints.actuator(systemId, deviceId, id))).data }
export async function updateActuator(systemId: number, deviceId: number, id: number, payload: ActuatorUpdate): Promise<Actuator> { return (await api.patch<Actuator>(endpoints.actuator(systemId, deviceId, id), payload)).data }
export async function deleteActuator(systemId: number, deviceId: number, id: number): Promise<void> { await api.delete(endpoints.actuator(systemId, deviceId, id)) }
export async function listActuatorReadings(systemId: number, deviceId: number, id: number, limit?: number): Promise<ActuatorReading[]> { return (await api.get<ActuatorReading[]>(endpoints.actuatorReadings(systemId, deviceId, id), { params: { limit } })).data }
export async function listActuatorCommands(systemId: number, deviceId: number, id: number, limit?: number): Promise<ActuatorCommand[]> { return (await api.get<ActuatorCommand[]>(endpoints.actuatorCommands(systemId, deviceId, id), { params: { limit } })).data }
export async function createCommand(systemId: number, deviceId: number, id: number, payload: ActuatorCommandCreate): Promise<ActuatorCommand> { return (await api.post<ActuatorCommand>(endpoints.actuatorCommands(systemId, deviceId, id), payload)).data }
export async function getActuatorThreshold(systemId: number, deviceId: number, id: number, metric: ActuatorThresholdMetric): Promise<ThresholdAlertConfig | null> { return (await api.get<ThresholdAlertConfig | null>(endpoints.actuatorThreshold(systemId, deviceId, id, metric))).data }
export async function saveActuatorThreshold(systemId: number, deviceId: number, id: number, metric: ActuatorThresholdMetric, payload: ThresholdAlertConfigInput): Promise<ThresholdAlertConfig> { return (await api.post<ThresholdAlertConfig>(endpoints.actuatorThreshold(systemId, deviceId, id, metric), payload)).data }
export async function updateActuatorThreshold(systemId: number, deviceId: number, id: number, metric: ActuatorThresholdMetric, payload: ThresholdAlertConfigInput): Promise<ThresholdAlertConfig> { return (await api.patch<ThresholdAlertConfig>(endpoints.actuatorThreshold(systemId, deviceId, id, metric), payload)).data }
export async function deleteActuatorThreshold(systemId: number, deviceId: number, id: number, metric: ActuatorThresholdMetric): Promise<void> { await api.delete(endpoints.actuatorThreshold(systemId, deviceId, id, metric)) }

export async function listAlerts(systemId: number, status?: string): Promise<Alert[]> { return (await api.get<Alert[]>(endpoints.alerts(systemId), { params: { status } })).data }
export async function getAlert(systemId: number, id: number): Promise<Alert> { return (await api.get<Alert>(endpoints.alert(systemId, id))).data }
export async function acknowledgeAlert(systemId: number, id: number): Promise<Alert> { return (await api.post<Alert>(`${endpoints.alert(systemId, id)}/acknowledge`)).data }
export async function resolveAlert(systemId: number, id: number, payload: AlertResolutionRequest): Promise<Alert> { return (await api.post<Alert>(`${endpoints.alert(systemId, id)}/resolve`, payload)).data }
export async function getMonitoringLatest(systemId: number): Promise<MonitoringLatest> { return (await api.get<MonitoringLatest>(endpoints.monitoringLatest(systemId))).data }
export async function getMonitoringSeries(systemId: number, range: MonitoringRange): Promise<MonitoringSeriesRead> { return (await api.get<MonitoringSeriesRead>(endpoints.monitoringSeries(systemId), { params: { range } })).data }
export async function getMonitoringActuatorHistory(systemId: number, deviceId: number, range: MonitoringRange): Promise<MonitoringActuatorHistoryRead> { return (await api.get<MonitoringActuatorHistoryRead>(endpoints.monitoringActuatorHistory(systemId, deviceId), { params: { range } })).data }
export async function listMembers(systemId: number): Promise<Member[]> { return (await api.get<Member[]>(endpoints.members(systemId))).data }
export async function addMember(systemId: number, payload: MemberCreate): Promise<Member> { return (await api.post<Member>(endpoints.members(systemId), payload)).data }
export async function updateMember(systemId: number, userId: number, payload: MemberUpdate): Promise<Member> { return (await api.patch<Member>(endpoints.member(systemId, userId), payload)).data }
export async function removeMember(systemId: number, userId: number): Promise<void> { await api.delete(endpoints.member(systemId, userId)) }
export async function listActivities(systemId: number, params?: { page?: number; page_size?: number; action?: string; entity_type?: string }): Promise<ActivityList> { return (await api.get<ActivityList>(endpoints.activities(systemId), { params })).data }
export async function getScadaRuntime(systemId: number): Promise<ScadaRuntimeResponse> { return (await api.get<ScadaRuntimeResponse>(endpoints.scada(systemId))).data }
export async function saveScadaDraft(systemId: number, layout: ScadaLayout): Promise<ScadaLayoutMutationResponse> { return (await api.put<ScadaLayoutMutationResponse>(endpoints.scadaDraft(systemId), layout)).data }
export async function publishScada(systemId: number): Promise<ScadaLayoutMutationResponse> { return (await api.post<ScadaLayoutMutationResponse>(endpoints.scadaPublish(systemId))).data }
export async function getAlertSettings(systemId: number): Promise<AlertSettings> { return (await api.get<AlertSettings>(endpoints.alertSettings(systemId))).data }
export async function updateAlertSettings(systemId: number, payload: AlertSettingsUpdate): Promise<AlertSettings> { return (await api.put<AlertSettings>(endpoints.alertSettings(systemId), payload)).data }
export async function exportMqttConfig(systemId: number): Promise<MqttExport> { return (await api.get<MqttExport>(endpoints.mqttExport(systemId))).data }

export async function listSensorModels(): Promise<SensorModel[]> { return (await api.get<SensorModel[]>(endpoints.sensorModels)).data }
export async function createSensorModel(payload: SensorModelInput): Promise<SensorModel> { return (await api.post<SensorModel>(endpoints.sensorModels, payload)).data }
export async function getSensorModel(id: number): Promise<SensorModel> { return (await api.get<SensorModel>(endpoints.sensorModel(id))).data }
export async function updateSensorModel(id: number, payload: SensorModelUpdate): Promise<SensorModel> { return (await api.patch<SensorModel>(endpoints.sensorModel(id), payload)).data }
export async function deleteSensorModel(id: number): Promise<void> { await api.delete(endpoints.sensorModel(id)) }
export async function listActuatorModels(): Promise<ActuatorModel[]> { return (await api.get<ActuatorModel[]>(endpoints.actuatorModels)).data }
export async function createActuatorModel(payload: ActuatorModelInput): Promise<ActuatorModel> { return (await api.post<ActuatorModel>(endpoints.actuatorModels, payload)).data }
export async function getActuatorModel(id: number): Promise<ActuatorModel> { return (await api.get<ActuatorModel>(endpoints.actuatorModel(id))).data }
export async function updateActuatorModel(id: number, payload: ActuatorModelUpdate): Promise<ActuatorModel> { return (await api.patch<ActuatorModel>(endpoints.actuatorModel(id), payload)).data }
export async function deleteActuatorModel(id: number): Promise<void> { await api.delete(endpoints.actuatorModel(id)) }
export async function listUsers(): Promise<UserSummary[]> { return (await api.get<UserSummary[]>(endpoints.users)).data }
export async function getUser(id: number): Promise<UserSummary> { return (await api.get<UserSummary>(endpoints.user(id))).data }
export async function listRoles(): Promise<RoleSummary[]> { return (await api.get<RoleSummary[]>(endpoints.roles)).data }
export async function createManagedUser(payload: ManagedUserCreate): Promise<UserSummary> { return (await api.post<UserSummary>(endpoints.users, payload)).data }
export async function updateManagedUser(id: number, payload: ManagedUserUpdate): Promise<UserSummary> { return (await api.patch<UserSummary>(endpoints.user(id), payload)).data }
export async function setManagedUserPassword(id: number, payload: ManagedPasswordUpdate): Promise<MessageResponse> { return (await api.post<MessageResponse>(endpoints.userPassword(id), payload)).data }
export async function userLifecycle(id: number, action: "activate" | "disable" | "lock" | "unlock" | "restore" | "soft-delete", payload?: AccountLifecycleRequest): Promise<MessageResponse> { return (await api.post<MessageResponse>(endpoints.userLifecycle(id, action), payload ?? {})).data }
export async function forceLogoutUser(id: number): Promise<MessageResponse> { return (await api.post<MessageResponse>(endpoints.userForceLogout(id))).data }
export async function disableSystem(id: number, payload: SystemLifecycleRequest): Promise<AquaponicsSystem> { return (await api.post<AquaponicsSystem>(endpoints.systemDisable(id), payload)).data }
export async function activateSystem(id: number): Promise<AquaponicsSystem> { return (await api.post<AquaponicsSystem>(endpoints.systemActivate(id))).data }
export async function getAlertDeliverySettings(id: number): Promise<AlertDeliverySettings> { return (await api.get<AlertDeliverySettings>(endpoints.deliverySettings(id))).data }
export async function updateAlertDeliverySettings(id: number, payload: AlertDeliverySettings): Promise<AlertDeliverySettings> { return (await api.put<AlertDeliverySettings>(endpoints.deliverySettings(id), payload)).data }
export async function addAlertDeliveryRecipient(id: number, payload: AlertDeliveryRecipientInput): Promise<AlertDeliveryRecipient> { return (await api.post<AlertDeliveryRecipient>(endpoints.deliveryRecipients(id), payload)).data }
export async function updateAlertDeliveryRecipient(id: number, recipientId: number, payload: AlertDeliveryRecipientUpdate): Promise<AlertDeliveryRecipient> { return (await api.patch<AlertDeliveryRecipient>(endpoints.deliveryRecipient(id, recipientId), payload)).data }
export async function deleteAlertDeliveryRecipient(id: number, recipientId: number): Promise<void> { await api.delete(endpoints.deliveryRecipient(id, recipientId)) }
export async function testAlertDeliveryRecipient(id: number, recipientId: number): Promise<AlertDeliveryTestResult> { return (await api.post<AlertDeliveryTestResult>(endpoints.deliveryRecipientTest(id, recipientId))).data }
export async function getAlertDeliveryHistory(id: number): Promise<AlertDeliveryHistoryItem[]> { return (await api.get<AlertDeliveryHistoryItem[]>(endpoints.deliveryHistory(id))).data }
export async function getPublicMonitoringSettings(id: number): Promise<PublicMonitoringSettings> { return (await api.get<PublicMonitoringSettings>(endpoints.publicMonitoringSettings(id))).data }
export async function updatePublicMonitoringSettings(id: number, enabled: boolean): Promise<PublicMonitoringSettings> { return (await api.put<PublicMonitoringSettings>(endpoints.publicMonitoringSettings(id), { enabled })).data }
export async function getPublicMonitoringLatest(slug: string): Promise<MonitoringLatest> { return (await api.get<MonitoringLatest>(endpoints.publicMonitoringLatest(slug))).data }
export async function getPublicMonitoringSeries(slug: string, range: MonitoringRange): Promise<MonitoringSeriesRead> { return (await api.get<MonitoringSeriesRead>(endpoints.publicMonitoringSeries(slug), { params: { range } })).data }
export async function listDeviceTemplates(): Promise<DeviceTemplate[]> { return (await api.get<DeviceTemplate[]>(endpoints.templates)).data }
export async function createDeviceTemplate(payload: DeviceTemplateInput): Promise<DeviceTemplate> { return (await api.post<DeviceTemplate>(endpoints.templates, payload)).data }
export async function getDeviceTemplate(id: number): Promise<DeviceTemplate> { return (await api.get<DeviceTemplate>(endpoints.template(id))).data }
export async function updateDeviceTemplate(id: number, payload: DeviceTemplateUpdate): Promise<DeviceTemplate> { return (await api.patch<DeviceTemplate>(endpoints.template(id), payload)).data }
export async function deleteDeviceTemplate(id: number): Promise<void> { await api.delete(endpoints.template(id)) }
export async function listTemplateSensors(id: number): Promise<TemplateSensorSlot[]> { return (await api.get<TemplateSensorSlot[]>(endpoints.templateSensors(id))).data }
export async function addTemplateSensor(id: number, payload: TemplateSensorSlotInput): Promise<TemplateSensorSlot> { return (await api.post<TemplateSensorSlot>(endpoints.templateSensors(id), payload)).data }
export async function getTemplateSensor(id: number, mappingId: number): Promise<TemplateSensorSlot> { return (await api.get<TemplateSensorSlot>(endpoints.templateSensor(id, mappingId))).data }
export async function updateTemplateSensor(id: number, mappingId: number, payload: TemplateSensorSlotUpdate): Promise<TemplateSensorSlot> { return (await api.patch<TemplateSensorSlot>(endpoints.templateSensor(id, mappingId), payload)).data }
export async function deleteTemplateSensor(id: number, mappingId: number): Promise<void> { await api.delete(endpoints.templateSensor(id, mappingId)) }
export async function listTemplateActuators(id: number): Promise<TemplateActuatorSlot[]> { return (await api.get<TemplateActuatorSlot[]>(endpoints.templateActuators(id))).data }
export async function addTemplateActuator(id: number, payload: TemplateActuatorSlotInput): Promise<TemplateActuatorSlot> { return (await api.post<TemplateActuatorSlot>(endpoints.templateActuators(id), payload)).data }
export async function getTemplateActuator(id: number, mappingId: number): Promise<TemplateActuatorSlot> { return (await api.get<TemplateActuatorSlot>(endpoints.templateActuator(id, mappingId))).data }
export async function updateTemplateActuator(id: number, mappingId: number, payload: TemplateActuatorSlotUpdate): Promise<TemplateActuatorSlot> { return (await api.patch<TemplateActuatorSlot>(endpoints.templateActuator(id, mappingId), payload)).data }
export async function deleteTemplateActuator(id: number, mappingId: number): Promise<void> { await api.delete(endpoints.templateActuator(id, mappingId)) }
