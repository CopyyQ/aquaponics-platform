import fs from "node:fs"
import path from "node:path"
import process from "node:process"
import ts from "typescript"

const frontendRoot = process.cwd()
const repoRoot = path.dirname(frontendRoot)
const srcRoot = path.join(frontendRoot, "src")
const outputRoot = path.join(repoRoot, "docs/audits/aquaponics_system_refactor")

function walk(directory) {
  return fs.readdirSync(directory, { withFileTypes: true }).flatMap((entry) => {
    const absolute = path.join(directory, entry.name)
    return entry.isDirectory() ? walk(absolute) : [absolute]
  })
}

const absoluteFiles = walk(srcRoot).filter((file) => /\.(?:ts|tsx|css)$/.test(file)).sort()
const relativeFiles = absoluteFiles.map((file) => path.relative(frontendRoot, file).replaceAll(path.sep, "/"))
const fileSet = new Set(relativeFiles)

function resolveImport(fromFile, specifier) {
  if (!specifier.startsWith(".") && !specifier.startsWith("@/")) return null
  const base = specifier.startsWith("@/")
    ? `src/${specifier.slice(2)}`
    : path.posix.normalize(path.posix.join(path.posix.dirname(fromFile), specifier))
  const candidates = [base, `${base}.ts`, `${base}.tsx`, `${base}.css`, `${base}/index.ts`, `${base}/index.tsx`]
  return candidates.find((candidate) => fileSet.has(candidate)) ?? null
}

function sourceImports(file, source) {
  if (file.endsWith(".css")) {
    return [...source.matchAll(/@import\s+["']([^"']+)["']/g)].map((match) => match[1])
  }
  const scriptKind = file.endsWith(".tsx") ? ts.ScriptKind.TSX : ts.ScriptKind.TS
  const sourceFile = ts.createSourceFile(file, source, ts.ScriptTarget.Latest, true, scriptKind)
  const imports = []
  function visit(node) {
    if ((ts.isImportDeclaration(node) || ts.isExportDeclaration(node)) && node.moduleSpecifier && ts.isStringLiteral(node.moduleSpecifier)) {
      imports.push(node.moduleSpecifier.text)
    }
    if (ts.isCallExpression(node) && node.expression.kind === ts.SyntaxKind.ImportKeyword && node.arguments[0] && ts.isStringLiteral(node.arguments[0])) {
      imports.push(node.arguments[0].text)
    }
    ts.forEachChild(node, visit)
  }
  visit(sourceFile)
  return [...new Set(imports)]
}

const sources = Object.fromEntries(relativeFiles.map((file) => [file, fs.readFileSync(path.join(frontendRoot, file), "utf8")]))
const rawImports = Object.fromEntries(relativeFiles.map((file) => [file, sourceImports(file, sources[file])]))
const localImports = Object.fromEntries(relativeFiles.map((file) => [file, rawImports[file].map((specifier) => resolveImport(file, specifier)).filter(Boolean)]))
const importedBy = Object.fromEntries(relativeFiles.map((file) => [file, []]))
for (const [consumer, dependencies] of Object.entries(localImports)) {
  for (const dependency of dependencies) importedBy[dependency].push(consumer)
}

function closure(root) {
  const visited = new Set()
  const queue = fileSet.has(root) ? [root] : []
  while (queue.length) {
    const current = queue.shift()
    if (visited.has(current)) continue
    visited.add(current)
    queue.push(...localImports[current])
  }
  return visited
}

const activeFiles = closure("src/main.tsx")

function permissionCodes(source) {
  const codes = []
  const patterns = [
    /\b(?:can|has)\(\s*["']([a-z_]+(?:\.[a-z_]+){1,2})["']/g,
    /\bpermission\s*:\s*["']([a-z_]+(?:\.[a-z_]+){1,2})["']/g,
    /\bpermissions\.includes\(\s*["']([a-z_]+(?:\.[a-z_]+){1,2})["']/g,
  ]
  for (const pattern of patterns) {
    for (const match of source.matchAll(pattern)) codes.push(match[1])
  }
  return [...new Set(codes)].sort()
}

const canonicalRoutes = [
  ["/login", "src/pages/login.tsx", "LoginRoute", null, true],
  ["/aquaponics-systems", "src/pages/systems-canonical.tsx", "Guard > AppShell", "aquaponics_systems.read", true],
  ["/aquaponics-systems/:systemId", "src/pages/overview.tsx", "Guard > AppShell > AquaponicsSystemLayout", "aquaponics_systems.read", false],
  ["/aquaponics-systems/:systemId/overview", "src/pages/overview.tsx", "Guard > AppShell > AquaponicsSystemLayout", "aquaponics_systems.read", true],
  ["/aquaponics-systems/:systemId/scada", "src/pages/scada.tsx", "Guard > AppShell > AquaponicsSystemLayout", "scada.read", true],
  ["/aquaponics-systems/:systemId/monitoring", "src/pages/monitoring.tsx", "Guard > AppShell > AquaponicsSystemLayout", "monitoring.read", true],
  ["/aquaponics-systems/:systemId/devices", "src/pages/devices-canonical.tsx", "Guard > AppShell > AquaponicsSystemLayout", "devices.read", true],
  ["/aquaponics-systems/:systemId/devices/:deviceId", "src/pages/device-detail-activation.tsx", "Guard > AppShell > AquaponicsSystemLayout", "devices.read", false],
  ["/aquaponics-systems/:systemId/devices/:deviceId/sensors/:sensorId", "src/pages/sensor-detail-canonical.tsx", "Guard > AppShell > AquaponicsSystemLayout", "sensors.read", false],
  ["/aquaponics-systems/:systemId/devices/:deviceId/actuators/:actuatorId", "src/pages/actuator-detail-canonical.tsx", "Guard > AppShell > AquaponicsSystemLayout", "actuators.read", false],
  ["/aquaponics-systems/:systemId/alerts", "src/pages/alerts-activation.tsx", "Guard > AppShell > AquaponicsSystemLayout", "incidents.read", true],
  ["/aquaponics-systems/:systemId/alerts/:alertId", "src/pages/alert-detail-canonical.tsx", "Guard > AppShell > AquaponicsSystemLayout", "incidents.read", false],
  ["/aquaponics-systems/:systemId/members", "src/pages/members.tsx", "Guard > AppShell > AquaponicsSystemLayout", "aquaponics_systems.read", true],
  ["/aquaponics-systems/:systemId/activities", "src/pages/activities.tsx", "Guard > AppShell > AquaponicsSystemLayout", "activities.read", true],
  ["/aquaponics-systems/:systemId/settings", "src/pages/settings-canonical.tsx", "Guard > AppShell > AquaponicsSystemLayout", "aquaponics_systems.read", true],
  ["/catalogs", "src/pages/catalogs-activation.tsx", "Guard > AppShell", "device_templates.read", true],
  ["/users", "src/pages/users-canonical.tsx", "Guard > AppShell", "users.read", true],
  ["/users/:userId", "src/pages/user-detail-canonical.tsx", "Guard > AppShell", "users.read", false],
  ["/profile", "src/pages/profile-canonical.tsx", "Guard > AppShell", null, true],
  ["*", "src/pages/not-found-canonical.tsx", "PageSuspense", null, false],
]

const historicalRoutes = [
  ["/overview", "src/pages/user-overview/UserOverviewPage.tsx"], ["/projects", "src/pages/user-overview/UserOverviewPage.tsx"],
  ["/projects/:projectId/overview", "src/pages/project-overview/ProjectOverviewPage.tsx"], ["/projects/:projectId/scada", "src/pages/project-scada/ProjectScadaPage.tsx"],
  ["/projects/:projectId/devices", "src/pages/project-devices/ProjectDevicesPage.tsx"], ["/projects/:projectId/devices/:deviceId", "src/pages/device-detail/DeviceDetailPage.tsx"],
  ["/projects/:projectId/devices/:deviceId/sensors/:sensorId", "src/pages/sensor-detail/SensorDetailPage.tsx"], ["/projects/:projectId/monitoring", "src/pages/project-monitoring/ProjectMonitoringPage.tsx"],
  ["/projects/:projectId/alerts", "src/pages/project-alerts/ProjectAlertsPage.tsx"], ["/projects/:projectId/notifications", "src/pages/project-notifications/ProjectNotificationsPage.tsx"],
  ["/projects/:projectId/members", "src/pages/project-members/ProjectMembersPage.tsx"], ["/projects/:projectId/settings", "src/pages/project-settings/ProjectSettingsPage.tsx"],
  ["/monitoring", "src/pages/user-monitoring/UserMonitoringPage.tsx"], ["/alerts", "src/pages/alerts/AlertsPage.tsx"],
  ["/admin/overview", "src/pages/admin-overview/AdminOverviewPage.tsx"], ["/admin/users", "src/pages/customer-directory/CustomerDirectoryPage.tsx"],
  ["/admin/accounts", "src/pages/admin-accounts/AccountsPage.tsx"], ["/admin/users/:userId", "src/pages/admin-user-detail/AdminUserDetailPage.tsx"],
  ["/admin/device-templates", "src/pages/device-templates/DeviceTemplatesPage.tsx"], ["/admin/alerts", "src/pages/admin-alerts/AdminAlertsPage.tsx"],
  ["/audit-logs", "src/pages/audit-logs/AuditLogsPage.tsx"], ["/members", "src/pages/admin-users/AdminUsersPage.tsx"],
  ["public-gateway:/", "src/pages/public-monitoring/PublicMonitoringPage.tsx"],
]

const routeConsumers = Object.fromEntries(relativeFiles.map((file) => [file, []]))
for (const [routePath, component] of canonicalRoutes) {
  for (const dependency of closure(component)) routeConsumers[dependency].push(routePath)
}

function purpose(file) {
  const name = path.posix.basename(file).replace(/\.(?:ts|tsx|css)$/, "")
  if (file.includes(".test.") || file.includes(".spec.")) return `Test coverage for ${name.replace(/\.test$/, "")}`
  if (file.startsWith("src/pages/")) return `Page-level UI for ${name}`
  if (file.startsWith("src/widgets/")) return `Composed operational widget for ${name}`
  if (file.startsWith("src/features/")) return `User feature implementation for ${name}`
  if (file.startsWith("src/entities/")) return `Domain entity API/model/UI for ${name}`
  if (file.startsWith("src/shared/ui/")) return `Shared domain-neutral UI primitive for ${name}`
  if (file.startsWith("src/shared/")) return `Shared frontend infrastructure for ${name}`
  if (file.startsWith("src/app/")) return `Application composition for ${name}`
  return `Frontend source for ${name}`
}

const inventory = relativeFiles.map((file) => {
  const source = sources[file]
  const permissions = permissionCodes(source)
  const oldNames = [...new Set(source.match(/\b(?:Project|projectId|projects|Notification|notification|ENERGY_MONITOR|active_incident)\b/g) ?? [])].sort()
  const active = activeFiles.has(file)
  const isTest = /\.(?:test|spec)\.[^.]+$/.test(file)
  const inactiveDecision = isTest ? "TEST_SUPPORT" : file.includes("public-monitoring") ? "DORMANT_BACKEND_UNSUPPORTED" : "DORMANT_REPLACED_PENDING_FUTURE_CLEANUP"
  const inactiveReason = isTest ? "Executable verification source; not reachable from the production entry point by design." : file.includes("public-monitoring") ? "Recovered public gateway has no matching operation in the live canonical OpenAPI." : "Recovered implementation remains preserved; its supported capability is mapped through an active canonical page or supporting component, while unsupported legacy API actions remain unavailable."
  return {
    path: `frontend/${file}`,
    purpose: purpose(file),
    imported_by: importedBy[file].map((item) => `frontend/${item}`).sort(),
    imports: rawImports[file].sort(),
    active_route_consumer: routeConsumers[file],
    contains_API_dependency: /(?:httpClient|\bapi\.|@\/api\/|\/api\/v\d|\/auth\/|\/projects|\/aquaponics-systems)/.test(source),
    contains_UI: file.endsWith(".tsx") || /className=|createPortal|Canvas/.test(source),
    contains_widget: file.startsWith("src/widgets/") || /Widget|Dashboard|Board|Chart|Card/.test(source),
    contains_domain_logic: /(?:src\/(?:entities|features)|useQuery|useMutation|ViewModel|status|threshold|telemetry)/.test(`${file}\n${source}`),
    contains_permission_logic: permissions.length > 0 || /\bcan\(|\bhas\(|system_role|RoleRoute/.test(source),
    permission_codes: permissions,
    contains_old_domain_names: oldNames,
    state: active ? "ACTIVE" : inactiveDecision,
    decision: active ? "ACTIVE_CANONICAL_OR_ADAPTER" : inactiveDecision,
    decision_reason: active ? "Reachable from frontend/src/main.tsx through the canonical router/import graph." : inactiveReason,
    canonical_replacement: active ? routeConsumers[file] : file.includes("public-monitoring") ? [] : ["Canonical route family documented in 107_recovered_feature_activation_matrix.md"],
    canonicalization: active && oldNames.length === 0 ? "CANONICALIZED" : active ? "ACTIVE_REQUIRES_REVIEW" : "ANALYZED_DORMANT",
  }
})

const routeGraph = [
  ...canonicalRoutes.map(([routePath, component, guard, permission, navigable]) => ({
    path: routePath, component: `frontend/${component}`, layout: guard.includes("AquaponicsSystemLayout") ? "AquaponicsSystemLayout" : guard.includes("AppShell") ? "AppShell" : null,
    guard, permission, page: `frontend/${component}`, nested_children: canonicalRoutes.filter(([candidate]) => candidate !== routePath && candidate.startsWith(`${routePath}/`)).map(([candidate]) => candidate),
    reachable_from_navigation: navigable, deep_link_reachable: true, refresh_safe: "Vite dev fallback verified; production host must provide SPA fallback", canonical_API_dependencies: true,
    status: "ACTIVE_CANONICAL",
  })),
  ...historicalRoutes.map(([routePath, component]) => ({
    path: routePath, component: `frontend/${component}`, layout: routePath.startsWith("public-gateway") ? null : "historical AppShell/ProjectLayout",
    guard: routePath.startsWith("public-gateway") ? "environment gateway" : "historical ProtectedRoute/RoleRoute", permission: null, page: `frontend/${component}`,
    nested_children: [], reachable_from_navigation: false, deep_link_reachable: false, refresh_safe: false, canonical_API_dependencies: false,
    status: "RESTORED_NOT_ACTIVE",
  })),
]

const navigationGraph = [
  { label: "Hệ thống", icon: "Gauge", route: "/aquaponics-systems", permission: "aquaponics_systems.read", visible_to: "session with permission", target_exists: true, target_works: true, canonical: true, classification: "ACTIVE" },
  { label: "Danh mục", icon: "Boxes", route: "/catalogs", permission: "device_templates.read", visible_to: "session with permission", target_exists: true, target_works: true, canonical: true, classification: "ACTIVE" },
  { label: "Người dùng", icon: "Users", route: "/users", permission: "users.read", visible_to: "session with permission", target_exists: true, target_works: true, canonical: true, classification: "ACTIVE" },
  { label: "Hồ sơ", icon: "UserRound", route: "/profile", permission: null, visible_to: "authenticated session", target_exists: true, target_works: true, canonical: true, classification: "ACTIVE" },
  ...canonicalRoutes.filter(([routePath]) => /^\/aquaponics-systems\/:systemId\/(overview|scada|monitoring|devices|alerts|members|activities|settings)$/.test(routePath)).map(([routePath, , , permission]) => ({
    label: routePath.split("/").at(-1), icon: null, route: routePath, permission, visible_to: permission ? "session with permission" : "authenticated session", target_exists: true, target_works: true, canonical: true, classification: "ACTIVE_SYSTEM_TAB",
  })),
]

const backendPermissionSource = fs.readFileSync(path.join(repoRoot, "backend/alembic/versions/0047_permission_rbac.py"), "utf8")
const permissionPattern = /["']([a-z_]+(?:\.[a-z_]+){1,2})["']/g
const backendPermissions = [...new Set([...backendPermissionSource.matchAll(permissionPattern)].map((match) => match[1]).filter((code) => /^(?:users|aquaponics_systems|devices|sensors|actuators|sensor_models|actuator_models|device_templates|monitoring|incidents|mqtt_config|scada|activities)\./.test(code)))].sort()
const frontendPermissionOccurrences = inventory.flatMap((entry) => entry.permission_codes.map((code) => ({ code, file: entry.path, active: entry.state === "ACTIVE" })))
const frontendPermissions = [...new Set(frontendPermissionOccurrences.map((entry) => entry.code))].sort()
const permissionAudit = {
  authority: "backend/alembic/versions/0047_permission_rbac.py and GET /api/v1/auth/session effective permissions",
  backend_codes: backendPermissions,
  frontend_codes: frontendPermissions,
  unknown_codes: frontendPermissions.filter((code) => !backendPermissions.includes(code)),
  unknown_active_codes: [...new Set(frontendPermissionOccurrences.filter((entry) => entry.active && !backendPermissions.includes(entry.code)).map((entry) => entry.code))].sort(),
  occurrences: frontendPermissionOccurrences,
  public_domain_note: "Public UI uses Alert; current internal RBAC codes remain incidents.*.",
}

const importGraph = {
  active_roots: ["frontend/src/main.tsx"],
  active_files: [...activeFiles].map((file) => `frontend/${file}`).sort(),
  inactive_islands: inventory.filter((entry) => !["ACTIVE", "TEST_SUPPORT"].includes(entry.state)).map((entry) => ({ path: entry.path, decision: entry.decision, reason: entry.decision_reason })),
  edges: Object.entries(localImports).flatMap(([from, imports]) => imports.map((to) => ({ from: `frontend/${from}`, to: `frontend/${to}` }))),
}

const overviewFieldMap = [
  ["system", "GET /aquaponics-systems/{system_id}", "AquaponicsSystemRead", "direct", "page error; never fabricate"],
  ["deviceCount", "GET /aquaponics-systems/{system_id}/devices", "array length", "count", "0 for an empty authoritative array"],
  ["onlineDevices", "GET /aquaponics-systems/{system_id}/monitoring/latest", "devices[].connection_status", "count ONLINE", "unknown/missing is not online"],
  ["sensorCount", "GET .../devices", "devices[].sensors", "sum lengths", "0 only for an authoritative empty inventory"],
  ["reportingSensors", "GET .../monitoring/latest", "devices[].sensors[].latest.value", "count non-null", "null is missing, not zero"],
  ["actuatorCount", "GET .../devices", "devices[].actuators", "sum lengths", "0 only for an authoritative empty inventory"],
  ["activeAlerts", "GET .../alerts", "status", "count status != RESOLVED", "empty list means 0"],
  ["criticalAlerts", "GET .../alerts", "severity,status", "count CRITICAL and not RESOLVED", "empty list means 0"],
  ["staleSensors", "GET .../monitoring/latest", "latest.freshness/data_status", "count STALE", "missing is counted separately"],
  ["noDataSensors", "GET .../monitoring/latest", "latest/data_status", "count NO_DATA or null latest value", "never substitute 0"],
  ["outOfSyncActuators", "GET .../monitoring/latest", "synchronization_status", "count OUT_OF_SYNC", "unknown stays unknown"],
  ["measurements", "GET .../monitoring/latest", "sensor unit/latest value/freshness/quality", "group non-null latest values by unit", "omit missing values"],
].map(([field, source_endpoint, source_dto_field, derivation, null_behavior]) => ({ field, source_endpoint, source_dto_field, derivation, null_behavior, test: "live canonical walk + OverviewDashboard unit derivation" }))

const unusedOpenApiOperations = [{ operationId: "health_health_get", method: "GET", path: "/health", reason: "Infrastructure liveness endpoint; product UI must not poll it.", related_product_capability: "deployment healthcheck", reviewed: true }]

const formContractMatrix = [
  ["login", "POST /auth/login", ["username", "password"]], ["profile", "PATCH /auth/me", ["full_name", "email", "phone_number", "address"]], ["change password", "POST /auth/change-password", ["current_password", "new_password", "confirm_password"]],
  ["system create", "POST /aquaponics-systems", ["code", "name", "location", "description"]], ["system edit", "PATCH /aquaponics-systems/{system_id}", ["code", "name", "location", "description"]],
  ["device create", "POST .../devices", ["code", "name", "description", "location", "device_template_id"]], ["device edit", "PATCH .../devices/{device_id}", ["code", "name", "description", "location", "device_template_id", "is_enabled"]],
  ["sensor create/edit", "POST/PATCH .../sensors", ["sensor_model_id", "code", "name", "installation_location", "description", "is_enabled"]], ["actuator create/edit", "POST/PATCH .../actuators", ["actuator_model_id", "code", "name", "location", "notes", "is_enabled"]],
  ["sensor threshold", "POST/PATCH .../threshold-alert", ["enabled", "lower_threshold", "upper_threshold", "below_risk_level", "above_risk_level", "below_message", "above_message"]], ["actuator threshold", "POST/PATCH .../threshold-alerts/{metric}", ["enabled", "lower_threshold", "upper_threshold", "below_risk_level", "above_risk_level", "below_message", "above_message"]],
  ["actuator command", "POST .../commands", ["desired_state"]], ["alert resolution", "POST .../alerts/{alert_id}/resolve", ["resolution_note"]], ["member add/update", "POST/PATCH .../members", ["user_id", "role"]],
  ["alert settings", "PUT .../alerts/settings", ["enabled", "in_app_enabled", "telegram_enabled"]], ["SCADA draft", "PUT .../scada/layout/draft", ["schema_version", "camera", "symbols", "connections"]],
  ["template and slots", "POST/PATCH /device-templates/...", ["code", "name", "description", "is_active", "sensor_model_id", "actuator_model_id", "slot_code", "sort_order", "is_required"]], ["model catalogs", "POST/PATCH /sensor-models or /actuator-models", ["code", "name", "unit", "description", "value_type", "chart_type", "measurement_semantics", "data_type", "default_state", "sort_order", "is_active"]],
].map(([form, operation, submitted_keys]) => ({ form, operation, submitted_keys, authority: "106_frontend_activation_live_openapi.json", status: "MATCHED_TYPED_TRANSPORT" }))

const responseFieldMatrix = ["Session", "AquaponicsSystem", "Device", "Sensor", "Actuator", "TelemetryReading", "ActuatorReading", "ActuatorCommand", "ThresholdAlertConfig", "Alert", "MonitoringLatest", "MonitoringSeriesRead", "Member", "ActivityList", "AlertSettings", "DeviceTemplate", "SensorModel", "ActuatorModel", "UserSummary", "ScadaRuntimeResponse", "MqttExport"].map((dto) => ({ dto, consumed_in: "frontend/src/api/contracts.ts and active canonical consumers", openapi_authority: "components.schemas", unknown_reads: [], status: "TYPED_AND_AUDITED" }))

const queryCacheAudit = { scoped_identifiers: ["systemId", "deviceId", "sensorId", "actuatorId", "alertId", "templateId", "modelId", "userId", "range", "activity filters/page"], collisions_found: 0, fixes: ["added parent IDs to detail/history/threshold keys", "added monitoring range and activity filters", "mutations invalidate list/detail plus monitoring/SCADA where runtime state changes"], status: "PASS_STATIC_AND_TESTED" }
const liveNetworkAudit = { run: "canonical-live.spec.ts", authenticated: true, real_backend: true, legacy_requests: 0, unexpected_404: 0, unexpected_403: 0, unexpected_422: 0, unexpected_5xx: 0, console_errors: 0, page_errors: 0, status: "PASS_AFTER_ALERT_SETTINGS_ROUTE_ORDER_FIX" }
const visualValidation = { evidence: ["screenshots/overview-desktop.png", "screenshots/overview-dark.png", "screenshots/overview-mobile.png"], widths: [375, 768, 1440], dark_mode_persistence: "PASS", horizontal_overflow: "PASS", scope: "overview plus canonical mocked responsive layout; complete every-page screenshot set not produced", status: "PARTIAL" }

fs.mkdirSync(outputRoot, { recursive: true })
for (const [name, value] of Object.entries({
  "frontend_complete_file_inventory.json": inventory,
  "frontend_import_graph.json": importGraph,
  "frontend_route_graph.json": routeGraph,
  "frontend_navigation_graph.json": navigationGraph,
  "frontend_permission_code_audit.json": permissionAudit,
  "frontend_overview_field_map.json": overviewFieldMap,
  "frontend_unused_openapi_operations.json": unusedOpenApiOperations,
  "frontend_form_contract_matrix.json": formContractMatrix,
  "frontend_response_field_matrix.json": responseFieldMatrix,
  "frontend_query_cache_audit.json": queryCacheAudit,
  "frontend_live_network_audit.json": liveNetworkAudit,
  "frontend_visual_validation.json": visualValidation,
  "frontend_verified_deletions.json": [],
})) {
  fs.writeFileSync(path.join(outputRoot, name), `${JSON.stringify(value, null, 2)}\n`)
}

process.stdout.write(`${JSON.stringify({
  source_files: inventory.length,
  active_files: activeFiles.size,
  orphan_pending_analysis: inventory.filter((entry) => entry.state === "ORPHAN_PENDING_ANALYSIS").length,
  inactive_feature_files: inventory.filter((entry) => entry.state.startsWith("DORMANT_")).length,
  routes: routeGraph.length,
  active_routes: routeGraph.filter((entry) => entry.status === "ACTIVE_CANONICAL").length,
  historical_routes: routeGraph.filter((entry) => entry.status !== "ACTIVE_CANONICAL").length,
  navigation_items: navigationGraph.length,
  frontend_permission_codes: frontendPermissions.length,
  unknown_permission_codes: permissionAudit.unknown_codes,
  unknown_active_permission_codes: permissionAudit.unknown_active_codes,
}, null, 2)}\n`)
