# Risks and conflicts

1. Multiple direct Telegram paths bypass outbox idempotency and policy.
2. Legacy business-rule catalogue remains a notification content dependency.
3. Formatter reads legacy feedback fields.
4. Project notification history inner-joins AlertRule, so rule-less canonical
   incidents may be invisible there.
5. Policy skip diagnostics conflate independent causes.
