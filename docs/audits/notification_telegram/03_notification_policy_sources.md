# Notification policy sources

The worker combines `ProjectNotificationSettings` with
`ProjectNotificationRiskPolicy`. If no per-risk row exists it falls back to
legacy setting booleans. Policy checks Telegram enabled, risk enabled and event
enabled; recipient resolution selects all enabled rows for the incident Project.

Current skip reasons include `POLICY_DISABLED`,
`SUPPRESSED_BY_DEVICE_OFFLINE`, `DUPLICATE_OPEN_EVENT`, and
`DUPLICATE_INCIDENT_EVENT`. `POLICY_DISABLED` combines several decisions, so it
does not distinguish disabled Telegram, risk, event, or absent recipient.
