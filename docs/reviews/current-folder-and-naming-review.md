# Current folder and naming review

| Current path | Classification | Keep/Rename/Move/Delete | Target path | Reason | Risk |
|---|---|---|---|---|---|
| `backend/app/api` | UI/application boundary | Keep | `backend/app/api` | Clear composition/HTTP adapter | Low |
| `backend/app/services` | Application layer | Keep temporarily | `backend/app/modules/*/service.py` incrementally | Working compatibility layer; big-bang move would break imports/tests | Medium |
| `backend/app/queries` | Database/application layer | Keep temporarily | `backend/app/modules/*/queries.py` incrementally | Responsibilities are named and routers already reuse them | Medium |
| `backend/app/models` | Database infrastructure | Keep temporarily | module-owned model registry incrementally | Alembic metadata and relationships depend on centralized registration | High |
| `backend/app/mqtt` | Infrastructure adapter | Keep | `backend/app/integrations/mqtt` in later compatible move | Runtime is correct; moving has no current user value | Medium |
| `backend/app/jobs` | Infrastructure/application adapter | Keep | `backend/app/jobs` | Clear responsibility | Low |
| `backend/app/core/database.py` | Legacy compatibility | Keep shim | `app/db/base.py`, `app/db/session.py` | Existing imports/migrations may consume shim | Medium |
| `backend/app/services/credential_service.py` | Legacy compatibility | Keep/audit | unchanged | DeviceCredential/HMAC consumers not fully proven absent | High |
| `frontend/src/shared` | UI/infrastructure layer | Keep | unchanged | Domain-neutral primitives with enforced boundaries | Low |
| `frontend/src/features` | UI feature layer | Keep | unchanged | User actions/domain charts are correctly placed | Low |
| `frontend/src/widgets` | UI composition layer | Keep | unchanged | Large read-only regions are correctly composed | Low |
| `review-output/` | Legacy review artifact | Keep pending archive | `docs/reviews/archive/` | Provenance/consumer audit incomplete; do not delete | Low |
| `implementation-output/` | Generated implementation report | Add | unchanged | Requested handoff artifact | Low |
| committed `__pycache__/` files | Generated artifact | Delete from source control when VCS is restored | none | Generated and environment-specific; repository currently lacks `.git` metadata | Low |

No broad rename was performed. Current names are mostly responsibility-specific, and compatibility/migration risk outweighs cosmetic consistency.
