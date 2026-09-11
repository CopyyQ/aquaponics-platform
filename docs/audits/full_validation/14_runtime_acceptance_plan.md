# Runtime acceptance plan

Run API, ingest, incident, policy, recipient, worker and concurrency tests against the isolated database; then validate schema equivalence and fixture preservation. Only after all pass is `alembic upgrade head` on runtime eligible.
