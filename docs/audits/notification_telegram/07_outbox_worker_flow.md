# Outbox worker flow

Eligible `PENDING`/`RETRYING` rows are selected by available time with
`FOR UPDATE SKIP LOCKED`. Per-recipient deliveries use
`incident:event:recipient` identity. Failed Telegram attempts retry with an
exponential delay, capped at five attempts. A transaction commits after a
batch, so the worker is observable through outbox and delivery statuses.
