# RBAC validation snapshot

| Gate | Result |
|---|---|
| Development database | revision `0045` (unchanged) |
| Fresh disposable rehearsal | `aquaponics_codex_rbac_final`, revision `0047` |
| Roles / permissions / assignments | 4 / 67 / 199 |
| Users without role_id | 0 |
| PostgreSQL-backed canonical suite | 29 passed, 0 failed |
| Backend compile and architecture checker | passed |
| Frontend typecheck | passed |
| Frontend Vitest | 91 passed |
| Docker services | healthy; dev image remains isolated from rehearsal migration |

The canonical router has zero `require_admin` dependencies and zero direct
`system_role` authorization branches. Legacy API modules have been removed
from the source tree; a small number of service-layer role semantics remain
for the account and membership domain and require a final permission audit.

The retained PostgreSQL-backed suite is the production validation gate for
the canonical route set. Development migration remains deferred until the
service-layer permission audit and final backup/reconciliation are complete.
