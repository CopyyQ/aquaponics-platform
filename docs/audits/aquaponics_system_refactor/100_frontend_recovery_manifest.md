# Frontend recovery manifest

Recovery source: local Git `HEAD` `91528d492c5905644038ae7c0810e406f03470cb`, independently matching `/tmp/aquaponics-original-reference`.

The staged/unstaged deletion inventory was restored in place after the forensic gate. No frontend file was deleted during recovery. The current canonical API layer remains under `frontend/src/api/` and the active application imports it directly.

| Path/group | Purpose | UI | API | Recovery action | Final status |
| --- | --- | ---: | ---: | --- | --- |
| `frontend/src/app/layouts/app-shell.tsx` | Responsive sidebar, header, theme/profile controls | Yes | No | Restore and adapt to session permissions | ADAPTED |
| `frontend/src/app/layouts/aquaponics-system-layout.tsx` | System identity, breadcrumb and nested navigation | Yes | Yes | New canonical system layout | RESTORED/ADAPTED |
| `frontend/src/app/router/canonical-router.tsx` | Lazy routing, guard and Suspense | Yes | No | New permission/session router | ADAPTED |
| `frontend/src/shared/ui/*` | Domain-neutral UI primitives | Yes | No | Preserve recovered primitives | RESTORED |
| `frontend/src/shared/charts/time-series/*` | Presentation chart infrastructure | Yes | No | Preserve recovered chart infrastructure | RESTORED |
| `frontend/src/entities/*` | Original domain UI/model infrastructure | Yes | Legacy adapters present | Preserve for audit/reference; active route uses canonical resources | PRESERVED |
| `frontend/src/features/*` | Forms, dialogs and operational feature UI | Yes | Legacy adapters present | Preserve mature UI; canonical vertical slices are active | PRESERVED |
| `frontend/src/widgets/canonical-overview/*` | Overview view model and KPI/attention cards | Yes | No | Compose from batch canonical reads | ADAPTED |
| `frontend/src/widgets/canonical-monitoring/*` | Latest/series cards and SVG time-series chart | Yes | No | Compose from canonical monitoring APIs | ADAPTED |
| `frontend/src/widgets/canonical-scada/*` | Typed orthographic 2.5D SCADA and HTML list fallback | Yes | No | Rebuild against typed canonical runtime DTO | ADAPTED |
| `frontend/src/api/client.ts` | One canonical Axios transport | No | Yes | Preserve and use as sole active transport | PRESERVE_CURRENT_API |
| `frontend/src/api/contracts.ts` | Live OpenAPI-aligned DTOs | No | Yes | Correct `confirm_password`, SCADA/MQTT and threshold types | ADAPTED |
| `frontend/src/api/resources.ts` | Canonical operation wrappers and query keys | No | Yes | Active FE call layer | PRESERVE_CURRENT_API |
| `frontend/src/pages/overview.tsx` | System health, devices, reporting and alerts | Yes | No | New canonical page/view model | ADAPTED |
| `frontend/src/pages/monitoring.tsx` | Range selection, latest data and charts | Yes | No | New canonical monitoring page | ADAPTED |
| `frontend/src/pages/devices.tsx` / `device-detail-canonical.tsx` | Mixed Device inventory and detail | Yes | No | Restore/adapt mature device experience | ADAPTED |
| `frontend/src/pages/sensor-detail.tsx` | Telemetry and null-safe threshold configuration | Yes | No | Canonical Sensor detail | ADAPTED |
| `frontend/src/pages/actuator-detail.tsx` | Commands, history, readings and thresholds | Yes | No | Canonical Actuator detail | ADAPTED |
| `frontend/src/pages/scada.tsx` | Runtime scene, details, issues, draft/publish | Yes | No | Canonical SCADA page | ADAPTED |
| `frontend/src/pages/alerts.tsx` | Sensor/Actuator alert lifecycle | Yes | No | Canonical Alert page | ADAPTED |
| `frontend/src/pages/members.tsx` / `activities.tsx` / `settings.tsx` | System operations | Yes | No | Canonical pages | ADAPTED |
| `frontend/src/pages/catalogs-canonical.tsx` | Template/model catalog management | Yes | No | Canonical catalog page | ADAPTED |
| `frontend/src/pages/profile.tsx` | Profile and password change | Yes | No | Preserve current API UI; add confirmation field | ADAPTED |

Final deletions: none. The recovered original paths remain available, and active runtime calls do not use their legacy endpoint definitions.
