# Legacy notification paths

`project_notification_service.py` uses legacy AlertRule, SensorAlert and
feedback context. `project_activity_service.py` sends activity messages
directly. Recipient test API sends direct test content. These are intentional
or legacy bypasses of the operational outbox and must be separately classified
before consolidation.
