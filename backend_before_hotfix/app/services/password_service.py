from datetime import UTC, datetime

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import UserStatus
from app.core.security import hash_password
from app.models.user import User
from app.schemas.user import AdminSetPasswordRequest, AdminSetPasswordResponse, ResetPasswordRequest
from app.services.audit_service import write_audit


async def admin_set_user_password(
    db: AsyncSession, *, user: User, payload: AdminSetPasswordRequest, actor: User
) -> AdminSetPasswordResponse:
    if user.is_deleted or user.deleted_at is not None or user.status == UserStatus.SOFT_DELETED:
        raise HTTPException(status_code=409, detail="Hãy khôi phục tài khoản trước khi đặt lại mật khẩu")
    user.password_hash = hash_password(payload.new_password)
    user.password_changed_at = datetime.now(UTC)
    user.must_change_password = payload.must_change_password
    if payload.invalidate_sessions:
        user.token_version += 1
    await write_audit(
        db,
        user_id=actor.id,
        action="ADMIN_SET_USER_PASSWORD",
        entity_type="USER",
        entity_id=user.id,
        new_data={
            "target_user_id": user.id,
            "sessions_invalidated": payload.invalidate_sessions,
            "must_change_password": payload.must_change_password,
        },
    )
    await db.commit()
    return AdminSetPasswordResponse(
        message="Đã cập nhật mật khẩu.",
        sessions_invalidated=payload.invalidate_sessions,
        must_change_password=payload.must_change_password,
    )


async def admin_reset_user_password(
    db: AsyncSession, *, user: User, payload: ResetPasswordRequest, actor: User
) -> None:
    if not payload.passwords_match:
        raise HTTPException(status_code=422, detail="Mật khẩu xác nhận không trùng khớp")
    user.password_hash = hash_password(payload.temporary_password)
    user.must_change_password = True
    user.password_changed_at = datetime.now(UTC)
    user.token_version += 1
    await write_audit(
        db, user_id=actor.id, action="RESET_PASSWORD", entity_type="USER", entity_id=user.id
    )
    await db.commit()
