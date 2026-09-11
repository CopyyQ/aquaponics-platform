# Permission migration 0047

Migration `0047_permission_rbac` creates the three canonical tables, adds `users.role_id`, seeds idempotent role and permission catalogs, maps existing `system_role` values, and assigns initial role permissions. It is forward-only; rollback uses the verified database backup and restore rehearsal. Development revision remains unchanged until the complete rehearsal and acceptance gate passes.
