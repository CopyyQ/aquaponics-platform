# Recipient resolution

Recipients come only from enabled `project_notification_recipients` rows for
the incident Project. The worker sends to every enabled recipient. The schema
prevents duplicate chat IDs inside one Project but has no user/verification or
soft-delete relation. No global chat-ID fallback was found in the outbox path.
