# Permission security validation

Validated properties: effective permissions are read from SQL joins, disabled roles grant nothing, role-permission revocation takes effect without JWT rotation, canonical mutations require explicit permission dependencies, and nested resources enforce parent scope. Full PostgreSQL-backed acceptance and frontend gates remain prerequisites for declaring production readiness.
