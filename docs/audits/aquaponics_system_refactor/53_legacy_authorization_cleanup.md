# Legacy authorization cleanup

The registered API router uses `require_permission` for every canonical operation. Legacy router modules remain on disk for audit and contain 55 `require_admin` and 32 `system_role` references; they are not registered in the canonical application router.

