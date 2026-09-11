# Current authorization inventory

The application authenticates bearer tokens in `app.api.deps.get_current_user`, validates account status and token version, and applies operational password-change gating. Before revision 0047, business authorization was a mixture of `system_role` checks, `require_roles`, `require_admin`, and ownership checks in `access_service`.

Revision 0047 introduces the canonical `roles`, `permissions`, and `role_permissions` tables and a nullable transitional `users.role_id` foreign key. Existing `system_role` values are backfilled into the four system roles. `PermissionService` reads effective permissions from the database on every request; the compatibility fallback only applies to newly-created pre-migration users until they are backfilled.

Resource scope remains separate: `require_project_access` checks AquaponicsSystem ownership or membership, while `require_permission` checks the operation. Global scope is represented by the explicit `aquaponics_systems.read_all` and `aquaponics_systems.manage_all` permissions. Membership roles are retained for per-system management decisions.

The canonical `/api/v1/aquaponics-systems` routes and sensor-model routes use permission dependencies. Legacy `/admin` routers are not included in the public API router while their migration is audited; `/admin` is therefore no longer an authorization boundary for canonical operations.
