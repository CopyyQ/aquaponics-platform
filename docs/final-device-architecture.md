# Final device architecture

`devices.device_type` is the runtime authority. Its only values are
`SENSOR_DEVICE` and `ACTUATOR_DEVICE`. A DeviceTemplate has the same type and
the provisioning API copies that type onto the Device.

A sensor may be created only on a `SENSOR_DEVICE`; an actuator may be created
only on an `ACTUATOR_DEVICE`. Existing controllers containing both components
are retained with `is_legacy_mixed=true`. They are never split automatically
and new mixed devices are rejected by the API and database trigger.

Actuator electrical data is direct runtime data:

- `actuators` holds the latest voltage/current snapshot, timestamps and
  directional threshold configuration.
- `actuator_readings` holds immutable voltage/current history.
- MQTT status messages can include `voltage_v`, `current_a` and `recorded_at`
  per actuator. The server assigns `received_at`.

The legacy feedback bindings and sensor telemetry are retained while migration
`0041` copies their values into `actuator_readings`. It uses mutually-nearest
voltage/current samples within five seconds, stores an idempotent provenance
key and leaves unmatched samples as one-sided readings. No migration deletes
legacy telemetry.

Configuration exports are read-only. They describe direct actuator electrical
fields and use numeric `command_id` values, matching `actuator_commands.id`.

Before production upgrade, create and verify a `pg_dump -Fc` backup. The
refactor backup created during this change is outside the repository at
`/tmp/aquaponics-pre-device-architecture-refactor-20260907T020901Z.dump`.
