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
  UserAquaponicsSystem,
  PublicId, AlertScenario, AlertScenarioInput,
} from "./contracts"

export const endpoints = {
  authLogin: "/auth/login", session: "/auth/session", authMe: "/auth/me", changePassword: "/auth/change-password", logout: "/auth/logout",
  systems: "/aquaponics-systems", system: (systemId: PublicId) => `/aquaponics-systems/${systemId}`,
  devices: (systemId: PublicId) => `/aquaponics-systems/${systemId}/devices`, device: (systemId: PublicId, deviceId: PublicId) => `${endpoints.devices(systemId)}/${deviceId}`,
  sensors: (systemId: PublicId, deviceId: PublicId) => `${endpoints.device(systemId, deviceId)}/sensors`, sensor: (systemId: PublicId, deviceId: PublicId, sensorId: PublicId) => `${endpoints.sensors(systemId, deviceId)}/${sensorId}`,
  sensorThreshold: (systemId: PublicId, deviceId: PublicId, sensorId: PublicId) => `${endpoints.sensor(systemId, deviceId, sensorId)}/threshold-alert`, sensorTelemetry: (systemId: PublicId, deviceId: PublicId, sensorId: PublicId) => `${endpoints.sensor(systemId, deviceId, sensorId)}/telemetry`,
  actuators: (systemId: PublicId, deviceId: PublicId) => `${endpoints.device(systemId, deviceId)}/actuators`, actuator: (systemId: PublicId, deviceId: PublicId, actuatorId: PublicId) => `${endpoints.actuators(systemId, deviceId)}/${actuatorId}`,
  actuatorReadings: (systemId: PublicId, deviceId: PublicId, actuatorId: PublicId) => `${endpoints.actuator(systemId, deviceId, actuatorId)}/readings`, actuatorCommands: (systemId: PublicId, deviceId: PublicId, actuatorId: PublicId) => `${endpoints.actuator(systemId, deviceId, actuatorId)}/commands`,
  actuatorThreshold: (systemId: PublicId, deviceId: PublicId, actuatorId: PublicId, metric: string) => `${endpoints.actuator(systemId, deviceId, actuatorId)}/threshold-alerts/${metric}`,
  sensorScenarios: (systemId: PublicId, deviceId: PublicId, sensorId: PublicId) => `${endpoints.sensor(systemId, deviceId, sensorId)}/alert-scenarios`,
  actuatorScenarios: (systemId: PublicId, deviceId: PublicId, actuatorId: PublicId) => `${endpoints.actuator(systemId, deviceId, actuatorId)}/alert-scenarios`,
  alerts: (systemId: PublicId) => `${endpoints.system(systemId)}/alerts`, alert: (systemId: PublicId, alertId: number) => `${endpoints.alerts(systemId)}/${alertId}`,
  monitoringLatest: (systemId: PublicId) => `${endpoints.system(systemId)}/monitoring/latest`, monitoringSeries: (systemId: PublicId) => `${endpoints.system(systemId)}/monitoring/series`, monitoringActuatorHistory: (systemId: PublicId, deviceId: PublicId) => `${endpoints.device(systemId, deviceId)}/monitoring/actuator-history`,
  members: (systemId: PublicId) => `${endpoints.system(systemId)}/members`, member: (systemId: PublicId, userId: PublicId) => `${endpoints.members(systemId)}/${userId}`, activities: (systemId: PublicId) => `${endpoints.system(systemId)}/activities`,
  scada: (systemId: PublicId) => `${endpoints.system(systemId)}/scada/runtime`, scadaDraft: (systemId: PublicId) => `${endpoints.system(systemId)}/scada/layout/draft`, scadaPublish: (systemId: PublicId) => `${endpoints.system(systemId)}/scada/layout/publish`,
  alertSettings: (systemId: PublicId) => `${endpoints.alerts(systemId)}/settings`, mqttExport: (systemId: PublicId) => `${endpoints.system(systemId)}/mqtt-config/export`,
  sensorModels: "/sensor-models", sensorModel: (id: number) => `/sensor-models/${id}`, actuatorModels: "/actuator-models", actuatorModel: (id: number) => `/actuator-models/${id}`,
  users: "/users", user: (id: PublicId) => `/users/${id}`, templates: "/device-templates", template: (id: number) => `/device-templates/${id}`,
  templateSensors: (id: number) => `${endpoints.template(id)}/sensors`, templateSensor: (id: number, mappingId: number) => `${endpoints.templateSensors(id)}/${mappingId}`,
  templateActuators: (id: number) => `${endpoints.template(id)}/actuators`, templateActuator: (id: number, mappingId: number) => `${endpoints.templateActuators(id)}/${mappingId}`,
  roles: "/roles",
  systemDisable: (id: PublicId) => `${endpoints.system(id)}/lifecycle/disable`, systemActivate: (id: PublicId) => `${endpoints.system(id)}/lifecycle/activate`,
  userPassword: (id: PublicId) => `${endpoints.user(id)}/password`, userForceLogout: (id: PublicId) => `${endpoints.user(id)}/force-logout`,
  userLifecycle: (id: PublicId, action: "activate" | "disable" | "lock" | "unlock" | "restore" | "soft-delete") => `${endpoints.user(id)}/${action}`,
  userSystems: (id: PublicId) => `${endpoints.user(id)}/aquaponics-systems`,
  systemOwner: (id: PublicId) => `${endpoints.system(id)}/owner`,
  deliverySettings: (id: PublicId) => `${endpoints.system(id)}/alert-delivery/settings`,
  deliveryRecipients: (id: PublicId) => `${endpoints.system(id)}/alert-delivery/recipients`,
  deliveryRecipient: (id: PublicId, recipientId: number) => `${endpoints.deliveryRecipients(id)}/${recipientId}`,
  deliveryRecipientTest: (id: PublicId, recipientId: number) => `${endpoints.deliveryRecipient(id, recipientId)}/test`,
  deliveryHistory: (id: PublicId) => `${endpoints.system(id)}/alert-delivery/history`,
  publicMonitoringSettings: (id: PublicId) => `${endpoints.system(id)}/public-monitoring/settings`,
  publicMonitoringLatest: (slug: string) => `/public/aquaponics-systems/${encodeURIComponent(slug)}/monitoring/latest`,
  publicMonitoringSeries: (slug: string) => `/public/aquaponics-systems/${encodeURIComponent(slug)}/monitoring/series`,
} as const

export const queryKeys = {
  systems: ["aquaponics-systems"] as const, system: (id: PublicId) => ["aquaponics-system", id] as const,
  devices: (systemId: PublicId) => ["aquaponics-system", systemId, "devices"] as const, device: (systemId: PublicId, id: PublicId) => ["aquaponics-system", systemId, "device", id] as const,
  sensor: (systemId: PublicId, deviceId: PublicId, id: PublicId) => ["aquaponics-system", systemId, "device", deviceId, "sensor", id] as const,
  sensorTelemetry: (systemId: PublicId, deviceId: PublicId, id: PublicId, start?: string, end?: string, limit?: number) => ["aquaponics-system", systemId, "device", deviceId, "sensor", id, "telemetry", { start, end, limit }] as const,
  sensorThreshold: (systemId: PublicId, deviceId: PublicId, id: PublicId) => ["aquaponics-system", systemId, "device", deviceId, "sensor", id, "threshold"] as const,
  actuator: (systemId: PublicId, deviceId: PublicId, id: PublicId) => ["aquaponics-system", systemId, "device", deviceId, "actuator", id] as const,
  actuatorReadings: (systemId: PublicId, deviceId: PublicId, id: PublicId, limit?: number) => ["aquaponics-system", systemId, "device", deviceId, "actuator", id, "readings", { limit }] as const,
  actuatorCommands: (systemId: PublicId, deviceId: PublicId, id: PublicId, limit?: number) => ["aquaponics-system", systemId, "device", deviceId, "actuator", id, "commands", { limit }] as const,
  actuatorThreshold: (systemId: PublicId, deviceId: PublicId, id: PublicId, metric: ActuatorThresholdMetric) => ["aquaponics-system", systemId, "device", deviceId, "actuator", id, "threshold", metric] as const,
  sensorScenarios: (systemId: PublicId, deviceId: PublicId, id: PublicId) => ["aquaponics-system", systemId, "device", deviceId, "sensor", id, "alert-scenarios"] as const,
  actuatorScenarios: (systemId: PublicId, deviceId: PublicId, id: PublicId) => ["aquaponics-system", systemId, "device", deviceId, "actuator", id, "alert-scenarios"] as const,
  monitoringLatest: (id: PublicId) => ["aquaponics-system", id, "monitoring", "latest"] as const, monitoringSeries: (id: PublicId, range: MonitoringRange) => ["aquaponics-system", id, "monitoring", "series", range] as const, monitoringActuatorHistory: (id: PublicId, deviceId: PublicId, range: MonitoringRange) => ["aquaponics-system", id, "device", deviceId, "monitoring", "actuator-history", range] as const,
  alerts: (id: PublicId) => ["aquaponics-system", id, "alerts"] as const, alert: (systemId: PublicId, id: number) => ["aquaponics-system", systemId, "alert", id] as const, members: (id: PublicId) => ["aquaponics-system", id, "members"] as const,
  activities: (id: PublicId, params?: { page?: number; page_size?: number; action?: string; entity_type?: string }) => ["aquaponics-system", id, "activities", params ?? {}] as const, scada: (id: PublicId) => ["aquaponics-system", id, "scada"] as const,
  alertSettings: (id: PublicId) => ["aquaponics-system", id, "alert-settings"] as const,
  sensorModels: ["sensor-models"] as const, sensorModel: (id: number) => ["sensor-model", id] as const,
  actuatorModels: ["actuator-models"] as const, actuatorModel: (id: number) => ["actuator-model", id] as const,
  templates: ["device-templates"] as const, template: (id: number) => ["device-template", id] as const,
  users: ["users"] as const, user: (id: PublicId) => ["user", id] as const, roles: ["roles"] as const,
  userSystems: (id: PublicId) => ["user", id, "aquaponics-systems"] as const,
  deliverySettings: (id: PublicId) => ["aquaponics-system", id, "alert-delivery", "settings"] as const,
  deliveryHistory: (id: PublicId) => ["aquaponics-system", id, "alert-delivery", "history"] as const,
  publicMonitoringSettings: (id: PublicId) => ["aquaponics-system", id, "public-monitoring", "settings"] as const,
} as const

export async function login(username: string, password: string): Promise<TokenResponse> { return (await api.post<TokenResponse>(endpoints.authLogin, { username, password })).data }
export async function loadSession(): Promise<Session> { return (await api.get<Session>(endpoints.session)).data }
export async function updateProfile(payload: UserSelfUpdate): Promise<Session["user"]> { return (await api.patch<Session["user"]>(endpoints.authMe, payload)).data }
export async function changePassword(payload: ChangePasswordRequest): Promise<MessageResponse> { return (await api.post<MessageResponse>(endpoints.changePassword, payload)).data }
export async function logout(): Promise<MessageResponse> { return (await api.post<MessageResponse>(endpoints.logout)).data }

export async function listSystems(): Promise<AquaponicsSystem[]> { return (await api.get<AquaponicsSystem[]>(endpoints.systems)).data }
export async function createSystem(payload: AquaponicsSystemCreate): Promise<AquaponicsSystem> { return (await api.post<AquaponicsSystem>(endpoints.systems, payload)).data }
export async function getSystem(id: PublicId): Promise<AquaponicsSystem> { return (await api.get<AquaponicsSystem>(endpoints.system(id))).data }
export async function updateSystem(id: PublicId, payload: AquaponicsSystemUpdate): Promise<AquaponicsSystem> { return (await api.patch<AquaponicsSystem>(endpoints.system(id), payload)).data }
export async function deleteSystem(id: PublicId): Promise<void> { await api.delete(endpoints.system(id)) }
export async function listDevices(systemId: PublicId): Promise<Device[]> { return (await api.get<Device[]>(endpoints.devices(systemId))).data }
export async function createDevice(systemId: PublicId, payload: DeviceInput): Promise<Device> { return (await api.post<Device>(endpoints.devices(systemId), payload)).data }
export async function getDevice(systemId: PublicId, id: PublicId): Promise<Device> { return (await api.get<Device>(endpoints.device(systemId, id))).data }
export async function updateDevice(systemId: PublicId, id: PublicId, payload: DeviceUpdate): Promise<Device> { return (await api.patch<Device>(endpoints.device(systemId, id), payload)).data }
export async function deleteDevice(systemId: PublicId, id: PublicId): Promise<void> { await api.delete(endpoints.device(systemId, id)) }

export async function listSensors(systemId: PublicId, deviceId: PublicId): Promise<Sensor[]> { return (await api.get<Sensor[]>(endpoints.sensors(systemId, deviceId))).data }
export async function createSensor(systemId: PublicId, deviceId: PublicId, payload: SensorInput): Promise<Sensor> { return (await api.post<Sensor>(endpoints.sensors(systemId, deviceId), payload)).data }
export async function getSensor(systemId: PublicId, deviceId: PublicId, id: PublicId): Promise<Sensor> { return (await api.get<Sensor>(endpoints.sensor(systemId, deviceId, id))).data }
export async function updateSensor(systemId: PublicId, deviceId: PublicId, id: PublicId, payload: SensorUpdate): Promise<Sensor> { return (await api.patch<Sensor>(endpoints.sensor(systemId, deviceId, id), payload)).data }
export async function deleteSensor(systemId: PublicId, deviceId: PublicId, id: PublicId): Promise<void> { await api.delete(endpoints.sensor(systemId, deviceId, id)) }
export async function getSensorThreshold(systemId: PublicId, deviceId: PublicId, id: PublicId): Promise<ThresholdAlertConfig | null> { return (await api.get<ThresholdAlertConfig | null>(endpoints.sensorThreshold(systemId, deviceId, id))).data }
export async function saveSensorThreshold(systemId: PublicId, deviceId: PublicId, id: PublicId, payload: ThresholdAlertConfigInput): Promise<ThresholdAlertConfig> { return (await api.post<ThresholdAlertConfig>(endpoints.sensorThreshold(systemId, deviceId, id), payload)).data }
export async function updateSensorThreshold(systemId: PublicId, deviceId: PublicId, id: PublicId, payload: ThresholdAlertConfigInput): Promise<ThresholdAlertConfig> { return (await api.patch<ThresholdAlertConfig>(endpoints.sensorThreshold(systemId, deviceId, id), payload)).data }
export async function deleteSensorThreshold(systemId: PublicId, deviceId: PublicId, id: PublicId): Promise<void> { await api.delete(endpoints.sensorThreshold(systemId, deviceId, id)) }
export async function listSensorScenarios(systemId: PublicId, deviceId: PublicId, id: PublicId): Promise<AlertScenario[]> { return (await api.get<AlertScenario[]>(endpoints.sensorScenarios(systemId, deviceId, id))).data }
export async function createSensorScenario(systemId: PublicId, deviceId: PublicId, id: PublicId, payload: AlertScenarioInput): Promise<AlertScenario> { return (await api.post<AlertScenario>(endpoints.sensorScenarios(systemId, deviceId, id), payload)).data }
export async function updateSensorScenario(systemId: PublicId, deviceId: PublicId, id: PublicId, scenarioId: PublicId, payload: Partial<AlertScenarioInput>): Promise<AlertScenario> { return (await api.patch<AlertScenario>(`${endpoints.sensorScenarios(systemId, deviceId, id)}/${scenarioId}`, payload)).data }
export async function deleteSensorScenario(systemId: PublicId, deviceId: PublicId, id: PublicId, scenarioId: PublicId): Promise<void> { await api.delete(`${endpoints.sensorScenarios(systemId, deviceId, id)}/${scenarioId}`) }
export async function getSensorTelemetry(systemId: PublicId, deviceId: PublicId, id: PublicId, params?: { start?: string; end?: string; limit?: number }): Promise<TelemetryReading[]> { return (await api.get<TelemetryReading[]>(endpoints.sensorTelemetry(systemId, deviceId, id), { params })).data }

export async function listActuators(systemId: PublicId, deviceId: PublicId): Promise<Actuator[]> { return (await api.get<Actuator[]>(endpoints.actuators(systemId, deviceId))).data }
export async function createActuator(systemId: PublicId, deviceId: PublicId, payload: ActuatorInput): Promise<Actuator> { return (await api.post<Actuator>(endpoints.actuators(systemId, deviceId), payload)).data }
export async function getActuator(systemId: PublicId, deviceId: PublicId, id: PublicId): Promise<Actuator> { return (await api.get<Actuator>(endpoints.actuator(systemId, deviceId, id))).data }
export async function updateActuator(systemId: PublicId, deviceId: PublicId, id: PublicId, payload: ActuatorUpdate): Promise<Actuator> { return (await api.patch<Actuator>(endpoints.actuator(systemId, deviceId, id), payload)).data }
export async function deleteActuator(systemId: PublicId, deviceId: PublicId, id: PublicId): Promise<void> { await api.delete(endpoints.actuator(systemId, deviceId, id)) }
export async function listActuatorReadings(systemId: PublicId, deviceId: PublicId, id: PublicId, limit?: number): Promise<ActuatorReading[]> { return (await api.get<ActuatorReading[]>(endpoints.actuatorReadings(systemId, deviceId, id), { params: { limit } })).data }
export async function listActuatorCommands(systemId: PublicId, deviceId: PublicId, id: PublicId, limit?: number): Promise<ActuatorCommand[]> { return (await api.get<ActuatorCommand[]>(endpoints.actuatorCommands(systemId, deviceId, id), { params: { limit } })).data }
export async function createCommand(systemId: PublicId, deviceId: PublicId, id: PublicId, payload: ActuatorCommandCreate): Promise<ActuatorCommand> { return (await api.post<ActuatorCommand>(endpoints.actuatorCommands(systemId, deviceId, id), payload)).data }
export async function getActuatorThreshold(systemId: PublicId, deviceId: PublicId, id: PublicId, metric: ActuatorThresholdMetric): Promise<ThresholdAlertConfig | null> { return (await api.get<ThresholdAlertConfig | null>(endpoints.actuatorThreshold(systemId, deviceId, id, metric))).data }
export async function saveActuatorThreshold(systemId: PublicId, deviceId: PublicId, id: PublicId, metric: ActuatorThresholdMetric, payload: ThresholdAlertConfigInput): Promise<ThresholdAlertConfig> { return (await api.post<ThresholdAlertConfig>(endpoints.actuatorThreshold(systemId, deviceId, id, metric), payload)).data }
export async function updateActuatorThreshold(systemId: PublicId, deviceId: PublicId, id: PublicId, metric: ActuatorThresholdMetric, payload: ThresholdAlertConfigInput): Promise<ThresholdAlertConfig> { return (await api.patch<ThresholdAlertConfig>(endpoints.actuatorThreshold(systemId, deviceId, id, metric), payload)).data }
export async function deleteActuatorThreshold(systemId: PublicId, deviceId: PublicId, id: PublicId, metric: ActuatorThresholdMetric): Promise<void> { await api.delete(endpoints.actuatorThreshold(systemId, deviceId, id, metric)) }
export async function listActuatorScenarios(systemId: PublicId, deviceId: PublicId, id: PublicId): Promise<AlertScenario[]> { return (await api.get<AlertScenario[]>(endpoints.actuatorScenarios(systemId, deviceId, id))).data }
export async function createActuatorScenario(systemId: PublicId, deviceId: PublicId, id: PublicId, payload: AlertScenarioInput): Promise<AlertScenario> { return (await api.post<AlertScenario>(endpoints.actuatorScenarios(systemId, deviceId, id), payload)).data }
export async function updateActuatorScenario(systemId: PublicId, deviceId: PublicId, id: PublicId, scenarioId: PublicId, payload: Partial<AlertScenarioInput>): Promise<AlertScenario> { return (await api.patch<AlertScenario>(`${endpoints.actuatorScenarios(systemId, deviceId, id)}/${scenarioId}`, payload)).data }
export async function deleteActuatorScenario(systemId: PublicId, deviceId: PublicId, id: PublicId, scenarioId: PublicId): Promise<void> { await api.delete(`${endpoints.actuatorScenarios(systemId, deviceId, id)}/${scenarioId}`) }

export async function listAlerts(systemId: PublicId, status?: string): Promise<Alert[]> { return (await api.get<Alert[]>(endpoints.alerts(systemId), { params: { status } })).data }
export async function getAlert(systemId: PublicId, id: number): Promise<Alert> { return (await api.get<Alert>(endpoints.alert(systemId, id))).data }
export async function acknowledgeAlert(systemId: PublicId, id: number): Promise<Alert> { return (await api.post<Alert>(`${endpoints.alert(systemId, id)}/acknowledge`)).data }
export async function resolveAlert(systemId: PublicId, id: number, payload: AlertResolutionRequest): Promise<Alert> { return (await api.post<Alert>(`${endpoints.alert(systemId, id)}/resolve`, payload)).data }
export async function getMonitoringLatest(systemId: PublicId): Promise<MonitoringLatest> { return (await api.get<MonitoringLatest>(endpoints.monitoringLatest(systemId))).data }
export async function getMonitoringSeries(systemId: PublicId, range: MonitoringRange): Promise<MonitoringSeriesRead> { return (await api.get<MonitoringSeriesRead>(endpoints.monitoringSeries(systemId), { params: { range } })).data }
export async function getMonitoringActuatorHistory(systemId: PublicId, deviceId: PublicId, range: MonitoringRange): Promise<MonitoringActuatorHistoryRead> { return (await api.get<MonitoringActuatorHistoryRead>(endpoints.monitoringActuatorHistory(systemId, deviceId), { params: { range } })).data }
export async function listMembers(systemId: PublicId): Promise<Member[]> { return (await api.get<Member[]>(endpoints.members(systemId))).data }
export async function addMember(systemId: PublicId, payload: MemberCreate): Promise<Member> { return (await api.post<Member>(endpoints.members(systemId), payload)).data }
export async function updateMember(systemId: PublicId, userId: PublicId, payload: MemberUpdate): Promise<Member> { return (await api.patch<Member>(endpoints.member(systemId, userId), payload)).data }
export async function removeMember(systemId: PublicId, userId: PublicId): Promise<void> { await api.delete(endpoints.member(systemId, userId)) }
export async function listActivities(systemId: PublicId, params?: { page?: number; page_size?: number; action?: string; entity_type?: string }): Promise<ActivityList> { return (await api.get<ActivityList>(endpoints.activities(systemId), { params })).data }
export async function getScadaRuntime(systemId: PublicId): Promise<ScadaRuntimeResponse> { return (await api.get<ScadaRuntimeResponse>(endpoints.scada(systemId))).data }
export async function saveScadaDraft(systemId: PublicId, layout: ScadaLayout): Promise<ScadaLayoutMutationResponse> { return (await api.put<ScadaLayoutMutationResponse>(endpoints.scadaDraft(systemId), layout)).data }
export async function publishScada(systemId: PublicId): Promise<ScadaLayoutMutationResponse> { return (await api.post<ScadaLayoutMutationResponse>(endpoints.scadaPublish(systemId))).data }
export async function getAlertSettings(systemId: PublicId): Promise<AlertSettings> { return (await api.get<AlertSettings>(endpoints.alertSettings(systemId))).data }
export async function updateAlertSettings(systemId: PublicId, payload: AlertSettingsUpdate): Promise<AlertSettings> { return (await api.put<AlertSettings>(endpoints.alertSettings(systemId), payload)).data }
export async function exportMqttConfig(systemId: PublicId): Promise<MqttExport> { return (await api.get<MqttExport>(endpoints.mqttExport(systemId))).data }

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
export async function getUser(id: PublicId): Promise<UserSummary> { return (await api.get<UserSummary>(endpoints.user(id))).data }
export async function listRoles(): Promise<RoleSummary[]> { return (await api.get<RoleSummary[]>(endpoints.roles)).data }
export async function createManagedUser(payload: ManagedUserCreate): Promise<UserSummary> { return (await api.post<UserSummary>(endpoints.users, payload)).data }
export async function updateManagedUser(id: PublicId, payload: ManagedUserUpdate): Promise<UserSummary> { return (await api.patch<UserSummary>(endpoints.user(id), payload)).data }
export async function setManagedUserPassword(id: PublicId, payload: ManagedPasswordUpdate): Promise<MessageResponse> { return (await api.post<MessageResponse>(endpoints.userPassword(id), payload)).data }
export async function userLifecycle(id: PublicId, action: "activate" | "disable" | "lock" | "unlock" | "restore" | "soft-delete", payload?: AccountLifecycleRequest): Promise<MessageResponse> { return (await api.post<MessageResponse>(endpoints.userLifecycle(id, action), payload ?? {})).data }
export async function forceLogoutUser(id: PublicId): Promise<MessageResponse> { return (await api.post<MessageResponse>(endpoints.userForceLogout(id))).data }
export async function listUserAquaponicsSystems(id: PublicId): Promise<UserAquaponicsSystem[]> { return (await api.get<UserAquaponicsSystem[]>(endpoints.userSystems(id))).data }
export async function createUserAquaponicsSystem(userId: PublicId, name: string): Promise<UserAquaponicsSystem> { return (await api.post<UserAquaponicsSystem>(endpoints.userSystems(userId), { name })).data }
export async function transferAquaponicsSystemOwner(systemId: PublicId, userId: PublicId): Promise<AquaponicsSystem> { return (await api.put<AquaponicsSystem>(endpoints.systemOwner(systemId), { user_id: userId })).data }
export async function disableSystem(id: PublicId, payload: SystemLifecycleRequest): Promise<AquaponicsSystem> { return (await api.post<AquaponicsSystem>(endpoints.systemDisable(id), payload)).data }
export async function activateSystem(id: PublicId): Promise<AquaponicsSystem> { return (await api.post<AquaponicsSystem>(endpoints.systemActivate(id))).data }
export async function getAlertDeliverySettings(id: PublicId): Promise<AlertDeliverySettings> { return (await api.get<AlertDeliverySettings>(endpoints.deliverySettings(id))).data }
export async function updateAlertDeliverySettings(id: PublicId, payload: AlertDeliverySettings): Promise<AlertDeliverySettings> { return (await api.put<AlertDeliverySettings>(endpoints.deliverySettings(id), payload)).data }
export async function addAlertDeliveryRecipient(id: PublicId, payload: AlertDeliveryRecipientInput): Promise<AlertDeliveryRecipient> { return (await api.post<AlertDeliveryRecipient>(endpoints.deliveryRecipients(id), payload)).data }
export async function updateAlertDeliveryRecipient(id: PublicId, recipientId: number, payload: AlertDeliveryRecipientUpdate): Promise<AlertDeliveryRecipient> { return (await api.patch<AlertDeliveryRecipient>(endpoints.deliveryRecipient(id, recipientId), payload)).data }
export async function deleteAlertDeliveryRecipient(id: PublicId, recipientId: number): Promise<void> { await api.delete(endpoints.deliveryRecipient(id, recipientId)) }
export async function testAlertDeliveryRecipient(id: PublicId, recipientId: number): Promise<AlertDeliveryTestResult> { return (await api.post<AlertDeliveryTestResult>(endpoints.deliveryRecipientTest(id, recipientId))).data }
export async function getAlertDeliveryHistory(id: PublicId): Promise<AlertDeliveryHistoryItem[]> { return (await api.get<AlertDeliveryHistoryItem[]>(endpoints.deliveryHistory(id))).data }
export async function getPublicMonitoringSettings(id: PublicId): Promise<PublicMonitoringSettings> { return (await api.get<PublicMonitoringSettings>(endpoints.publicMonitoringSettings(id))).data }
export async function updatePublicMonitoringSettings(id: PublicId, enabled: boolean): Promise<PublicMonitoringSettings> { return (await api.put<PublicMonitoringSettings>(endpoints.publicMonitoringSettings(id), { enabled })).data }
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
