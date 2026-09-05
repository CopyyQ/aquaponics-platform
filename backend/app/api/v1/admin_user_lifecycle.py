from fastapi import APIRouter, Body, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_admin
from app.core.enums import UserStatus
from app.db.session import get_session
from app.models.user import User
from app.schemas.common import MessageResponse
from app.schemas.user import AccountLifecycleRequest
from app.services.account_lifecycle_service import change_account_status, force_logout_user

router = APIRouter(prefix="/admin/users", tags=["Admin user lifecycle"])


async def transition(
    db: AsyncSession,
    *,
    user_id: int,
    status: UserStatus,
    action: str,
    message: str,
    actor: User,
    payload: AccountLifecycleRequest | None,
) -> MessageResponse:
    await change_account_status(
        db,
        user_id=user_id,
        target_status=status,
        actor=actor,
        reason=payload.reason if payload else None,
        action=action,
    )
    return MessageResponse(message=message)


@router.post("/{user_id}/force-logout", response_model=MessageResponse)
async def force_logout(
    user_id: int,
    payload: AccountLifecycleRequest | None = Body(default=None),
    db: AsyncSession = Depends(get_session),
    actor: User = Depends(require_admin),
) -> MessageResponse:
    await force_logout_user(db, user_id=user_id, actor=actor, reason=payload.reason if payload else None)
    return MessageResponse(message="Đã thu hồi toàn bộ phiên đăng nhập")


def lifecycle_endpoint(path: str, status: UserStatus, action: str, message: str):
    async def endpoint(
        user_id: int,
        payload: AccountLifecycleRequest | None = Body(default=None),
        db: AsyncSession = Depends(get_session),
        actor: User = Depends(require_admin),
    ) -> MessageResponse:
        return await transition(
            db,
            user_id=user_id,
            status=status,
            action=action,
            message=message,
            actor=actor,
            payload=payload,
        )

    router.add_api_route(path, endpoint, methods=["POST"], response_model=MessageResponse)


lifecycle_endpoint("/{user_id}/activate", UserStatus.ACTIVE, "ACTIVATE_USER", "Đã kích hoạt tài khoản; người dùng phải đăng nhập lại")
lifecycle_endpoint("/{user_id}/disable", UserStatus.DISABLED, "DISABLE_USER", "Đã vô hiệu hóa tài khoản và thu hồi phiên đăng nhập")
lifecycle_endpoint("/{user_id}/lock", UserStatus.LOCKED, "LOCK_USER", "Đã khóa tài khoản và thu hồi phiên đăng nhập")
lifecycle_endpoint("/{user_id}/unlock", UserStatus.ACTIVE, "UNLOCK_USER", "Đã mở khóa tài khoản; người dùng phải đăng nhập lại")
lifecycle_endpoint("/{user_id}/restore", UserStatus.ACTIVE, "RESTORE_USER", "Đã khôi phục và kích hoạt tài khoản; người dùng phải đăng nhập lại")


@router.delete("/{user_id}", response_model=MessageResponse)
async def delete_user(
    user_id: int,
    payload: AccountLifecycleRequest | None = Body(default=None),
    db: AsyncSession = Depends(get_session),
    actor: User = Depends(require_admin),
) -> MessageResponse:
    return await transition(
        db,
        user_id=user_id,
        status=UserStatus.SOFT_DELETED,
        action="SOFT_DELETE_USER",
        message="Đã xóa mềm tài khoản; dữ liệu Project được giữ nguyên",
        actor=actor,
        payload=payload,
    )
