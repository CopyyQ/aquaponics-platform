# Retry and idempotency

Outbox and delivery have distinct idempotency keys. Delivery records prevent
repeat sends for the same incident/event/recipient, and worker checks existing
sent delivery records defensively. Risks: direct send paths bypass these keys;
`POLICY_DISABLED` is too broad to diagnose policy decisions.
