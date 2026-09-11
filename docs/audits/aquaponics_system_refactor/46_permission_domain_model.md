# Permission domain model

`User.role_id` points to one enabled `Role`. A role has many permissions through the unique `RolePermission(role_id, permission_id)` association. Permission codes are stable `resource.action` strings and are the only values used by API dependencies. Authentication, operation authorization, and AquaponicsSystem scope are evaluated independently.

System roles are `ADMIN`, `OWNER`, `TECHNICIAN`, and `VIEWER`. ADMIN receives platform and resource permissions; OWNER and TECHNICIAN receive non-user operational permissions; VIEWER receives read, telemetry, history, export, and other read-only permissions.
