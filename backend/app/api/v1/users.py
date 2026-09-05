from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_roles
from app.db.session import get_db
from app.core.enums import UserRole, UserStatus
from app.core.security import hash_password
from app.models.user import User
from app.schemas.common import MessageResponse
from app.schemas.user import (
    AssignOwnerRequest,
    ResetPasswordRequest,
    UserCreate,
    UserRead,
    UserUpdate,
)
from app.services.audit_service import write_audit
from app.services.account_lifecycle_service import change_account_status
from app.services.user_service import create_user, update_user

router = APIRouter(prefix="/members", tags=["Members"])
Actor = Depends(require_roles(UserRole.ADMIN))


async def get_user_or_404(db: AsyncSession, user_id: int, include_deleted: bool = False) -> User:
    query = select(User).where(User.id == user_id)
    if not include_deleted:
        query = query.where(User.is_deleted.is_(False))
    user = await db.scalar(query)
    if user is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy người dùng")
    return user


@router.get("", response_model=list[UserRead])
async def list_members(
    include_deleted: bool = Query(False),
    db: AsyncSession = Depends(get_db),
    actor: User = Actor,
) -> list[User]:
    query = select(User).order_by(User.created_at.desc())
    if not include_deleted:
        query = query.where(User.is_deleted.is_(False))
    return list((await db.scalars(query)).all())


@router.post("", response_model=UserRead, status_code=201)
async def create_member(
    payload: UserCreate,
    db: AsyncSession = Depends(get_db),
    actor: User = Actor,
) -> User:
    return await create_user(db, payload, actor)


@router.get("/{user_id}", response_model=UserRead)
async def get_member(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    actor: User = Actor,
) -> User:
    user = await get_user_or_404(db, user_id)
    return user


@router.patch("/{user_id}", response_model=UserRead)
async def patch_member(
    user_id: int,
    payload: UserUpdate,
    db: AsyncSession = Depends(get_db),
    actor: User = Actor,
) -> User:
    user = await get_user_or_404(db, user_id)
    return await update_user(db, user, payload, actor)


@router.post("/{user_id}/disable", response_model=MessageResponse)
async def disable_member(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    actor: User = Actor,
) -> MessageResponse:
    user = await get_user_or_404(db, user_id)
    if actor.id == user.id:
        raise HTTPException(status_code=400, detail="Không thể vô hiệu hóa chính mình")
    await change_account_status(
        db,
        user_id=user.id,
        target_status=UserStatus.DISABLED,
        actor=actor,
        action="DISABLE_USER",
    )
    return MessageResponse(message="Đã vô hiệu hóa tài khoản")


@router.post("/{user_id}/enable", response_model=MessageResponse)
async def enable_member(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    actor: User = Actor,
) -> MessageResponse:
    user = await get_user_or_404(db, user_id)
    await change_account_status(
        db,
        user_id=user.id,
        target_status=UserStatus.ACTIVE,
        actor=actor,
        action="ACTIVATE_USER",
    )
    return MessageResponse(message="Đã kích hoạt tài khoản")


@router.delete("/{user_id}", status_code=204)
async def delete_member(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    actor: User = Actor,
) -> Response:
    await get_user_or_404(db, user_id)
    await change_account_status(
        db,
        user_id=user_id,
        target_status=UserStatus.SOFT_DELETED,
        actor=actor,
        action="SOFT_DELETE_USER",
    )
    return Response(status_code=204)


@router.post("/{user_id}/restore", response_model=MessageResponse)
async def restore_member(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    actor: User = Depends(require_roles(UserRole.ADMIN)),
) -> MessageResponse:
    await get_user_or_404(db, user_id, include_deleted=True)
    await change_account_status(
        db,
        user_id=user_id,
        target_status=UserStatus.ACTIVE,
        actor=actor,
        action="RESTORE_USER",
    )
    return MessageResponse(message="Đã khôi phục và kích hoạt tài khoản")


@router.post("/{user_id}/reset-password", response_model=MessageResponse)
async def reset_password(
    user_id: int,
    payload: ResetPasswordRequest,
    db: AsyncSession = Depends(get_db),
    actor: User = Depends(require_roles(UserRole.ADMIN)),
) -> MessageResponse:
    user = await get_user_or_404(db, user_id)
    if not payload.passwords_match:
        raise HTTPException(status_code=422, detail="Mật khẩu xác nhận không trùng khớp")
    user.password_hash = hash_password(payload.temporary_password)
    user.must_change_password = True
    if payload.invalidate_sessions:
        user.token_version += 1
    await write_audit(db, user_id=actor.id, action="RESET_PASSWORD", entity_type="USER", entity_id=user.id)
    await db.commit()
    return MessageResponse(message="Đã đặt mật khẩu tạm thời")


@router.post("/assign-owner", response_model=MessageResponse)
async def assign_owner(
    payload: AssignOwnerRequest,
    db: AsyncSession = Depends(get_db),
    actor: User = Depends(require_roles(UserRole.ADMIN)),
) -> MessageResponse:
    new_owner = await get_user_or_404(db, payload.user_id)
    if new_owner.status != UserStatus.ACTIVE:
        raise HTTPException(status_code=400, detail="Người dùng phải đang hoạt động")
    new_owner.system_role = UserRole.OWNER
    new_owner.token_version += 1
    await write_audit(
        db,
        user_id=actor.id,
        action="ASSIGN_OWNER",
        entity_type="USER",
        entity_id=new_owner.id,
    )
    await db.commit()
    return MessageResponse(message="Đã cấp vai trò Owner")
