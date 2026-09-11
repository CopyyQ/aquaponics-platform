from datetime import datetime, timezone

from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.permission import Permission, Role, RoleAssignment, RolePermission, UserPermissionOverride
from app.models.project import Project
from app.models.user import User


def _scope_filter(model: type[RoleAssignment] | type[UserPermissionOverride], system_id: int | None):
    global_scope = and_(model.scope_type == "GLOBAL", model.scope_id.is_(None))
    if system_id is None:
        return global_scope
    return or_(global_scope, and_(model.scope_type == "AQUAPONICS_SYSTEM", model.scope_id == system_id))


async def get_effective_permissions(db: AsyncSession, user: User, system_id: int | None = None) -> set[str]:
    role_ids: set[int] = {user.role_id} if user.role_id is not None else set()
    assignment_ids = await db.scalars(
        select(RoleAssignment.role_id).join(Role, Role.id == RoleAssignment.role_id).where(
            RoleAssignment.user_id == user.id,
            _scope_filter(RoleAssignment, system_id),
            or_(RoleAssignment.expires_at.is_(None), RoleAssignment.expires_at > datetime.now(timezone.utc)),
            Role.enabled.is_(True),
        )
    )
    role_ids.update(assignment_ids.all())
    if system_id is not None:
        owner_role_id = await db.scalar(
            select(Role.id).join(Project, Project.owner_user_id == user.id).where(
                Project.id == system_id, Project.is_deleted.is_(False),
                Role.code == "OWNER", Role.enabled.is_(True),
            )
        )
        if owner_role_id is not None:
            role_ids.add(owner_role_id)
    role_permissions: set[str] = set()
    if role_ids:
        rows = await db.scalars(
        select(Permission.code)
        .join(RolePermission, RolePermission.permission_id == Permission.id)
        .join(Role, Role.id == RolePermission.role_id)
        .where(RolePermission.role_id.in_(role_ids), Role.enabled.is_(True), Permission.enabled.is_(True))
        )
        role_permissions = set(rows.all())
    overrides = (await db.execute(
        select(Permission.code, UserPermissionOverride.effect)
        .join(Permission, Permission.id == UserPermissionOverride.permission_id)
        .where(UserPermissionOverride.user_id == user.id, _scope_filter(UserPermissionOverride, system_id), Permission.enabled.is_(True))
    )).all()
    allows = {code for code, effect in overrides if effect == "ALLOW"}
    denies = {code for code, effect in overrides if effect == "DENY"}
    return (role_permissions | allows) - denies


async def has_permission(db: AsyncSession, user: User, permission_code: str, system_id: int | None = None) -> bool:
    return permission_code in await get_effective_permissions(db, user, system_id)
