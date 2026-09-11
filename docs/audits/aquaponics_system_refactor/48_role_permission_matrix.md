# Role/permission matrix

| Role | Policy |
|---|---|
| ADMIN | All seeded permissions, including global system scope and user administration |
| OWNER | All operational/catalog permissions except user administration; management is constrained by system ownership or manager membership |
| TECHNICIAN | Same operational permission set as OWNER; scope remains membership/ownership constrained |
| VIEWER | Read-only, telemetry, history, export and monitoring permissions |

Assignments are database rows and can be revoked without issuing a new JWT.
