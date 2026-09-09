from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import _inactive_account_error, get_authenticated_user
from app.db.session import get_db
from app.core.security import create_access_token, hash_password, verify_password
from app.models.user import User
from app.schemas.auth import ChangePasswordRequest, LoginRequest, TokenResponse
from app.schemas.common import MessageResponse
from app.schemas.user import UserRead, UserSelfUpdate
from app.services.audit_service import write_audit
from app.services.permission_service import get_effective_permissions

router = APIRouter(prefix="/auth", tags=["Authentication"])


class SessionRead(BaseModel):
    user: UserRead
    permissions: list[str]


@router.post("/login", response_model=TokenResponse)
async def login(payload: LoginRequest, db: AsyncSession = Depends(get_db)) -> TokenResponse:
    user = await db.scalar(
        select(User).where(User.username == payload.username)
    )
    if user is not None and (user.status.value != "ACTIVE" or user.is_deleted or user.deleted_at is not None):
        raise _inactive_account_error(user)
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Tên đăng nhập hoặc mật khẩu không đúng")
    user.last_login_at = datetime.now(UTC)
    await write_audit(
        db, user_id=user.id, action="LOGIN", entity_type="USER", entity_id=user.id
    )
    await db.commit()
    return TokenResponse(
        access_token=create_access_token(
            str(user.id), {"role": user.system_role.value, "token_version": user.token_version}
        ),
        must_change_password=user.must_change_password,
    )


@router.get("/session", response_model=SessionRead)
async def session(user: User = Depends(get_authenticated_user), db: AsyncSession = Depends(get_db)) -> SessionRead:
    return SessionRead(user=UserRead.model_validate(user), permissions=sorted(await get_effective_permissions(db, user)))


@router.patch("/me", response_model=UserRead)
async def update_me(
    payload: UserSelfUpdate,
    user: User = Depends(get_authenticated_user),
    db: AsyncSession = Depends(get_db),
) -> User:
    old_data = {
        "full_name": user.full_name,
        "email": user.email,
        "phone_number": user.phone_number,
        "address": user.address,
    }
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(user, key, value)
    await write_audit(
        db, user_id=user.id, action="UPDATE_PROFILE", entity_type="USER",
        entity_id=user.id, old_data=old_data,
        new_data=payload.model_dump(exclude_unset=True, mode="json")
    )
    await db.commit()
    await db.refresh(user)
    return user


@router.post("/change-password", response_model=MessageResponse)
async def change_password(
    payload: ChangePasswordRequest,
    user: User = Depends(get_authenticated_user),
    db: AsyncSession = Depends(get_db),
) -> MessageResponse:
    if not verify_password(payload.current_password, user.password_hash):
        raise HTTPException(status_code=400, detail="Mật khẩu hiện tại không đúng")
    if verify_password(payload.new_password, user.password_hash):
        raise HTTPException(status_code=400, detail="Mật khẩu mới không được trùng mật khẩu hiện tại")
    user.password_hash = hash_password(payload.new_password)
    user.password_changed_at = datetime.now(UTC)
    user.must_change_password = False
    user.token_version += 1
    await write_audit(
        db,
        user_id=user.id,
        action="CHANGE_PASSWORD",
        entity_type="USER",
        entity_id=user.id,
    )
    await db.commit()
    return MessageResponse(message="Đổi mật khẩu thành công")


@router.post("/logout", response_model=MessageResponse)
async def logout(_: User = Depends(get_authenticated_user)) -> MessageResponse:
    return MessageResponse(message="Đăng xuất thành công. Frontend cần xóa access token.")
