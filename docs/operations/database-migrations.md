# Database migrations

Back up and audit before upgrades. Existing databases at `0016` use `alembic upgrade head` to apply `0017`. Fresh databases use the guarded `python scripts/bootstrap_fresh_database.py` procedure documented in the remediation plan.

Never use current metadata inside a revision, destructive volume/database commands, or tests pointed at `aquaponics`. Compare fresh/upgraded schemas with `scripts/check_schema_equivalence.py` before approving baseline consolidation.
