# Safe canonical database refactor

The retained development database was inspected at revision 0035, backed up, restored into `aquaponics_canonical_rehearsal`, and upgraded through 0045. The rehearsal preserved all measured history and split three mixed devices into sensor and actuator identities. No destructive operation was run against the development database.

Rehearsal gates passed: restore, Alembic upgrade, canonical topology, foreign-key checks, and the PostgreSQL-backed test suite (75 passed).
