# Migration remediation plan

## Verified failure

Revision `0001` imports current metadata and calls `create_all`; therefore a fresh historical replay creates later objects early and conflicts at `0016`. Applied revisions `0001–0016` must remain unchanged.

## Existing database path

Audit live `0016` read-only, back up, then run `alembic upgrade head`. Revision `0017` refuses duplicate `(device_id, code)`, removes only the global actuator unique and redundant telemetry indexes, adds power metadata/catalog and retains all runtime data.

## Fresh database path

Create an empty database named `aquaponics_fresh_*` or `aquaponics_codex_*`, set `DATABASE_URL`, then run `python scripts/bootstrap_fresh_database.py`. The script refuses any other name or non-empty database, creates current versioned baseline metadata, seeds power catalog rows and stamps `0017`.

## Strategy evaluation

- Historical repair: rejected because deployed revisions would change.
- Parallel Alembic branch: rejected because multiple heads make normal upgrades unsafe.
- Reconciliation then stamp to a new line: viable later but needs an approved production snapshot.
- Guarded bootstrap snapshot + stamp: selected for fresh installs now; existing databases retain their full history.

Production history consolidation remains owner-approved follow-up work. Never stamp a retained database without schema-equivalence proof.
