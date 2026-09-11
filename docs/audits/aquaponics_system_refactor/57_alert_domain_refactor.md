# Alert domain refactor

Alerts are exposed under `/aquaponics-systems/{system_id}/alerts` with list, detail, acknowledge and resolve operations. Delivery settings are nested under `/alerts/settings`; IN_APP and TELEGRAM remain delivery channels.

