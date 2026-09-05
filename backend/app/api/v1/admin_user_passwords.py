from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_admin
from app.db.session import get_session
from app.models.user import User
from app.schemas.common import MessageResponse
from app.schemas.user import AdminSetPasswordRequest, AdminSetPasswordResponse, ResetPasswordRequest
from app.services.password_service import admin_reset_user_password, admin_set_user_password
from app.services.user_service import get_user, get_user_including_deleted

router = APIRouter(prefix="/admin/users", tags=["Admin user passwords"])


@router.post("/{user_id}/set-password", response_model=AdminSetPasswordResponse)
async def set_password(
    user_id: int,
    payload: AdminSetPasswordRequest,
    db: AsyncSession = Depends(get_session),
    actor: User = Depends(require_admin),
) -> AdminSetPasswordResponse:
    user = await get_user_including_deleted(db, user_id)
    return await admin_set_user_password(db, user=user, payload=payload, actor=actor)


@router.post("/{user_id}/reset-password", response_model=MessageResponse)
async def reset_password(
    user_id: int,
    payload: ResetPasswordRequest,
    db: AsyncSession = Depends(get_session),
    actor: User = Depends(require_admin),
) -> MessageResponse:
    await admin_reset_user_password(
        db, user=await get_user(db, user_id), payload=payload, actor=actor
    )
    return MessageResponse(message="Đã đặt mật khẩu tạm thời và thu hồi phiên đăng nhập")
