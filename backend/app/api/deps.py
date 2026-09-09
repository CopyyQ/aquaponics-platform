from fastapi import Depends, HTTPException, status
from fastapi.security import (
    HTTPAuthorizationCredentials,
    HTTPBearer,
)
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.core.enums import UserStatus
from app.core.security import decode_access_token
from app.models.user import User
from app.services.permission_service import has_permission


bearer_scheme = HTTPBearer(auto_error=False)


class AccountAuthError(Exception):
    def __init__(self, code: str, detail: str) -> None:
        self.code = code
        self.detail = detail
        super().__init__(detail)


def _inactive_account_error(
    user: User,
) -> AccountAuthError:
    if user.status == UserStatus.DISABLED:
        return AccountAuthError(
            "ACCOUNT_DISABLED",
            "Tài khoản đã bị vô hiệu hóa.",
        )

    if user.status == UserStatus.LOCKED:
        return AccountAuthError(
            "ACCOUNT_LOCKED",
            "Tài khoản đang bị khóa.",
        )

    if (
        user.status == UserStatus.SOFT_DELETED
        or user.is_deleted
        or user.deleted_at is not None
    ):
        return AccountAuthError(
            "ACCOUNT_DELETED",
            "Tài khoản đã bị xóa.",
        )

    return AccountAuthError(
        "ACCOUNT_INACTIVE",
        "Tài khoản đã bị vô hiệu hóa hoặc khóa.",
    )


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(
        bearer_scheme
    ),
    db: AsyncSession = Depends(get_db),
) -> User:
    if credentials is None:
        raise AccountAuthError(
            "AUTHENTICATION_REQUIRED",
            "Chưa đăng nhập.",
        )

    try:
        payload = decode_access_token(
            credentials.credentials
        )

        user_id = int(payload["sub"])
        token_version = int(
            payload.get("token_version", -1)
        )
    except (
        ValueError,
        KeyError,
        TypeError,
    ) as exc:
        raise AccountAuthError(
            "INVALID_TOKEN",
            "Token không hợp lệ hoặc đã hết hạn.",
        ) from exc

    user = await db.scalar(
        select(User).where(
            User.id == user_id
        )
    )

    if user is None:
        raise AccountAuthError(
            "ACCOUNT_DELETED",
            "Tài khoản không còn tồn tại.",
        )

    if (
        user.status != UserStatus.ACTIVE
        or user.is_deleted
        or user.deleted_at is not None
    ):
        raise _inactive_account_error(user)

    if user.token_version != token_version:
        raise AccountAuthError(
            "TOKEN_REVOKED",
            "Phiên đăng nhập đã hết hiệu lực.",
        )

    return user


async def get_current_active_user(
    user: User = Depends(get_current_user),
) -> User:
    if (
        user.status != UserStatus.ACTIVE
        or user.is_deleted
        or user.deleted_at is not None
    ):
        raise _inactive_account_error(user)

    return user


async def get_current_operational_user(
    user: User = Depends(
        get_current_active_user
    ),
) -> User:
    if user.must_change_password:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "PASSWORD_CHANGE_REQUIRED",
                "detail": (
                    "Bạn phải thay đổi mật khẩu "
                    "trước khi tiếp tục."
                ),
            },
        )

    return user


# Dành cho endpoint đổi mật khẩu bắt buộc.
get_authenticated_user = get_current_active_user


def require_permission(permission_code: str):
    async def dependency(
        user: User = Depends(get_current_operational_user),
        db: AsyncSession = Depends(get_db),
    ) -> User:
        if not await has_permission(db, user, permission_code):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "code": "PERMISSION_REQUIRED",
                    "permission": permission_code,
                    "detail": "Tài khoản không có quyền thực hiện thao tác này.",
                },
            )
        return user

    return dependency
