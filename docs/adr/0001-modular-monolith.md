# ADR 0001: Modular monolith

Status: Accepted

## Context
Domains share tenant authorization, transactions and PostgreSQL migrations.
## Decision
Use one modular monolith with multiple runtime processes and explicit boundaries.
## Consequences
One release/database; architecture checks prevent coupling.
## Rejected alternatives
Microservices, generic event bus, per-domain databases.
## Follow-up work
Move compatibility packages incrementally only when it reduces proven coupling.
