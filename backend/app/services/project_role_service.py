from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.permission import Role, RoleAssignment


PROJECT_ROLE_CODES = frozenset({"OWNER", "TECHNICIAN", "VIEWER"})


async def sync_project_role_assignment(
    db: AsyncSession, *, user_id: int, system_id: int, role_code: str, created_by: int | None
) -> RoleAssignment:
    if role_code not in PROJECT_ROLE_CODES:
        raise ValueError("Invalid project role")
    role = await db.scalar(select(Role).where(Role.code == role_code, Role.enabled.is_(True)))
    if role is None:
        raise ValueError("Role is missing or disabled")
    await db.execute(delete(RoleAssignment).where(
        RoleAssignment.user_id == user_id,
        RoleAssignment.scope_type == "AQUAPONICS_SYSTEM",
        RoleAssignment.scope_id == system_id,
        RoleAssignment.role_id != role.id,
    ))
    assignment = await db.scalar(select(RoleAssignment).where(
        RoleAssignment.user_id == user_id,
        RoleAssignment.role_id == role.id,
        RoleAssignment.scope_type == "AQUAPONICS_SYSTEM",
        RoleAssignment.scope_id == system_id,
    ))
    if assignment is None:
        assignment = RoleAssignment(user_id=user_id, role_id=role.id, scope_type="AQUAPONICS_SYSTEM",
                                    scope_id=system_id, created_by=created_by)
        db.add(assignment)
        await db.flush()
    return assignment


async def remove_project_role_assignments(db: AsyncSession, *, user_id: int, system_id: int) -> None:
    project_role_ids = select(Role.id).where(Role.code.in_(PROJECT_ROLE_CODES))
    await db.execute(delete(RoleAssignment).where(
        RoleAssignment.user_id == user_id,
        RoleAssignment.scope_type == "AQUAPONICS_SYSTEM",
        RoleAssignment.scope_id == system_id,
        RoleAssignment.role_id.in_(project_role_ids),
    ))
