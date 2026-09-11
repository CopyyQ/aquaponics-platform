# Hard-coded values inventory

`project_notification_service.py` contains `BUSINESS_ALERT_RULES`, risk labels,
display labels and model-name fallbacks. It states the catalogue does not
evaluate conditions, but it remains a legacy notification-content source.
`notification_outbox_service.py` contains presentation labels and legacy
`feedback_role` threshold formatting. `project_notifications.py` contains
default risk policy values.

No Bot token literal, endpoint containing a literal token, or production chat
ID literal was found in tracked backend, frontend, scripts or docs. Local
environment files were excluded from reporting.
