from datetime import UTC, datetime

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import UserRole, UserStatus
from app.models.user import User
from app.services.audit_service import write_audit


ACTION_BY_STATUS = {
    UserStatus.DISABLED: "DISABLE_USER",
    UserStatus.LOCKED: "LOCK_USER",
    UserStatus.ACTIVE: "ACTIVATE_USER",
}


async def lock_user_for_lifecycle(db: AsyncSession, user_id: int) -> User:
    user = await db.scalar(select(User).where(User.id == user_id).with_for_update())
    if user is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy người dùng")
    return user


async def ensure_not_last_active_admin(db: AsyncSession, user: User) -> None:
    if (
        user.system_role != UserRole.ADMIN
        or user.status != UserStatus.ACTIVE
        or user.is_deleted
        or user.deleted_at is not None
    ):
        return
    active_admin_ids = list(
        (
            await db.scalars(
                select(User.id)
                .where(
                    User.system_role == UserRole.ADMIN,
                    User.status == UserStatus.ACTIVE,
                    User.is_deleted.is_(False),
                    User.deleted_at.is_(None),
                )
                .with_for_update()
            )
        ).all()
    )
    if len(active_admin_ids) <= 1:
        raise HTTPException(status_code=409, detail="Không thể vô hiệu hóa Admin active cuối cùng")


async def change_account_status(
    db: AsyncSession,
    *,
    user_id: int,
    target_status: UserStatus,
    actor: User,
    reason: str | None = None,
    action: str | None = None,
) -> User:
    user = await lock_user_for_lifecycle(db, user_id)
    if target_status != UserStatus.ACTIVE:
        await ensure_not_last_active_admin(db, user)

    old_status = user.status
    now = datetime.now(UTC)
    normalized_reason = reason.strip() if reason and reason.strip() else None

    if target_status == UserStatus.DISABLED:
        user.disabled_at = now
        user.disabled_by_user_id = actor.id
        user.disabled_reason = normalized_reason
    elif target_status == UserStatus.LOCKED:
        user.locked_at = now
        user.locked_by_user_id = actor.id
        user.locked_reason = normalized_reason
    elif target_status == UserStatus.SOFT_DELETED:
        user.is_deleted = True
        user.deleted_at = now
    elif target_status == UserStatus.ACTIVE:
        user.is_deleted = False
        user.deleted_at = None

    user.status = target_status
    user.token_version += 1
    audit_action = action or ACTION_BY_STATUS.get(target_status, "UPDATE_USER_STATUS")
    await write_audit(
        db,
        user_id=actor.id,
        action=audit_action,
        entity_type="USER",
        entity_id=user.id,
        old_data={"old_status": old_status.value},
        new_data={
            "old_status": old_status.value,
            "new_status": target_status.value,
            "reason": normalized_reason,
        },
    )
    await db.commit()
    await db.refresh(user)
    return user


async def force_logout_user(db: AsyncSession, *, user_id: int, actor: User, reason: str | None = None) -> User:
    user = await lock_user_for_lifecycle(db, user_id)
    user.token_version += 1
    await write_audit(
        db,
        user_id=actor.id,
        action="FORCE_LOGOUT_USER",
        entity_type="USER",
        entity_id=user.id,
        new_data={"reason": reason.strip() if reason and reason.strip() else None},
    )
    await db.commit()
    await db.refresh(user)
    return user
