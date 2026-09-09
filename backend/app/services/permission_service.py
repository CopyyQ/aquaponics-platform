from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.permission import Permission, Role, RolePermission
from app.models.user import User


async def get_effective_permissions(db: AsyncSession, user: User) -> set[str]:
    role_id = user.role_id
    if role_id is None:
        return set()
    rows = await db.scalars(
        select(Permission.code)
        .join(RolePermission, RolePermission.permission_id == Permission.id)
        .join(Role, Role.id == RolePermission.role_id)
        .where(RolePermission.role_id == role_id, Role.enabled.is_(True))
    )
    return set(rows.all())


async def has_permission(db: AsyncSession, user: User, permission_code: str) -> bool:
    return permission_code in await get_effective_permissions(db, user)
