# Current database inventory

- Database: `aquaponics`; PostgreSQL 16.14; Compose service `postgres`; Alembic `0035`; head before rehearsal `0044`.
- Docker volume was retained. No database drop or volume reset was performed.
- Rows before migration: projects 4, devices 14, sensors 71, actuators 12, telemetry readings 1,519,746, notification outbox 331, notification deliveries 753, operational incidents 115.
- Legacy rows: actuator feedback bindings 22, feedback definitions 12, AlertRule 19, SensorAlert 5,263.
