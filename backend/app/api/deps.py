from collections.abc import Awaitable, Callable
from typing import Any

from fastapi import Depends, HTTPException, status
from fastapi.security import (
    HTTPAuthorizationCredentials,
    HTTPBearer,
)
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.core.enums import UserRole, UserStatus
from app.core.security import decode_access_token
from app.models.user import User


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


def normalize_role(
    value: UserRole | str | Any | None,
) -> str:
    """
    Chuẩn hóa các dạng:
    - UserRole.ADMIN
    - "ADMIN"
    - "UserRole.ADMIN"
    thành "ADMIN".
    """
    if value is None:
        return ""

    if isinstance(value, UserRole):
        return value.name.strip().upper()

    normalized = str(value).strip().upper()

    if "." in normalized:
        normalized = normalized.rsplit(".", 1)[-1]

    return normalized


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


def require_roles(
    *roles: UserRole | str,
) -> Callable[..., Awaitable[User]]:
    allowed_roles = {
        normalize_role(role)
        for role in roles
        if normalize_role(role)
    }

    if not allowed_roles:
        raise ValueError(
            "require_roles phải nhận ít nhất một vai trò."
        )

    async def dependency(
        user: User = Depends(
            get_current_operational_user
        ),
    ) -> User:
        current_role = normalize_role(
            user.system_role
        )

        if current_role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "code": "INSUFFICIENT_ROLE",
                    "detail": (
                        "Tài khoản không có quyền "
                        "thực hiện thao tác này."
                    ),
                    "current_role": current_role,
                    "required_roles": sorted(
                        allowed_roles
                    ),
                },
            )

        return user

    return dependency


async def require_admin(
    user: User = Depends(
        get_current_operational_user
    ),
) -> User:
    role = (
        user.system_role.value
        if isinstance(user.system_role, UserRole)
        else str(user.system_role).split(".")[-1]
    ).upper()

    if role != UserRole.ADMIN.value.upper():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "ADMIN_REQUIRED",
                "detail": (
                    "Chỉ Quản trị viên mới có "
                    "quyền thực hiện thao tác này."
                ),
                "current_role": role,
            },
        )

    return user
