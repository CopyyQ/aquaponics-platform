# MQTT single export

Exactly one HTTP export operation is registered: `/aquaponics-systems/{system_id}/mqtt-config/export`. It is system wide and serializes every device with both sensor and actuator mappings without mutating the database.

