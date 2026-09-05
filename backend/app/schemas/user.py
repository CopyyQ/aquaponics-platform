from datetime import datetime

import re

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator, model_validator

from app.core.enums import UserRole, UserStatus


class UserBase(BaseModel):
    username: str = Field(min_length=3, max_length=100)
    full_name: str = Field(min_length=2, max_length=255)
    email: EmailStr
    phone_number: str = Field(min_length=8, max_length=30)
    address: str = ""
    system_role: UserRole = UserRole.VIEWER


class UserCreate(UserBase):
    temporary_password: str = Field(min_length=8, max_length=128)


USERNAME_PATTERN = re.compile(r"^[A-Za-z0-9._-]+$")
PHONE_PATTERN = re.compile(r"^\+?[0-9]{8,15}$")


class AdminUserCreate(BaseModel):
    username: str = Field(min_length=3, max_length=100)
    full_name: str = Field(min_length=2, max_length=255)
    email: EmailStr
    phone_number: str = Field(min_length=8, max_length=30)
    address: str = Field(default="", max_length=2000)
    system_role: UserRole
    status: UserStatus = UserStatus.ACTIVE
    password: str = Field(min_length=8, max_length=128)
    confirm_password: str = Field(min_length=8, max_length=128)
    must_change_password: bool = True

    @field_validator("username", "full_name", "phone_number", "address", mode="before")
    @classmethod
    def trim_strings(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value

    @field_validator("email", mode="before")
    @classmethod
    def normalize_email(cls, value: object) -> object:
        return value.strip().lower() if isinstance(value, str) else value

    @field_validator("username")
    @classmethod
    def validate_username(cls, value: str) -> str:
        if not USERNAME_PATTERN.fullmatch(value):
            raise ValueError("Tên đăng nhập chỉ gồm chữ, số, dấu chấm, gạch dưới hoặc gạch ngang")
        return value

    @field_validator("phone_number")
    @classmethod
    def validate_phone_number(cls, value: str) -> str:
        if not PHONE_PATTERN.fullmatch(value):
            raise ValueError("Số điện thoại chỉ gồm 8–15 chữ số và có thể bắt đầu bằng dấu +")
        return value

    @model_validator(mode="after")
    def validate_account(self) -> "AdminUserCreate":
        if self.password != self.confirm_password:
            raise ValueError("Mật khẩu xác nhận không trùng khớp")
        if self.status == UserStatus.SOFT_DELETED:
            raise ValueError("Không thể tạo mới tài khoản ở trạng thái đã xóa")
        return self


class UserUpdate(BaseModel):
    full_name: str | None = Field(default=None, min_length=2, max_length=255)
    email: EmailStr | None = None
    phone_number: str | None = Field(default=None, min_length=8, max_length=30)
    address: str | None = None
    status: UserStatus | None = None
    system_role: UserRole | None = None


class AccountLifecycleRequest(BaseModel):
    reason: str | None = Field(default=None, max_length=1000)


class UserSelfUpdate(BaseModel):
    full_name: str | None = Field(default=None, min_length=2, max_length=255)
    email: EmailStr | None = None
    phone_number: str | None = Field(default=None, min_length=8, max_length=30)
    address: str | None = None


class UserRead(UserBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    status: UserStatus
    must_change_password: bool
    last_login_at: datetime | None
    created_at: datetime
    updated_at: datetime
    token_version: int
    is_deleted: bool
    deleted_at: datetime | None
    disabled_at: datetime | None
    disabled_by_user_id: int | None
    disabled_reason: str | None
    locked_at: datetime | None
    locked_by_user_id: int | None
    locked_reason: str | None


class ResetPasswordRequest(BaseModel):
    temporary_password: str = Field(min_length=8, max_length=128)
    confirm_password: str = Field(min_length=8, max_length=128)
    invalidate_sessions: bool = True

    @property
    def passwords_match(self) -> bool:
        return self.temporary_password == self.confirm_password


class AdminSetPasswordRequest(BaseModel):
    new_password: str = Field(min_length=8, max_length=128)
    confirm_password: str = Field(min_length=8, max_length=128)
    invalidate_sessions: bool = True
    must_change_password: bool = False

    @model_validator(mode="after")
    def passwords_match(self) -> "AdminSetPasswordRequest":
        if self.new_password != self.confirm_password:
            raise ValueError("Mật khẩu xác nhận không trùng khớp")
        return self


class AdminSetPasswordResponse(BaseModel):
    success: bool = True
    message: str
    sessions_invalidated: bool
    must_change_password: bool


class AdminUserDetail(UserRead):
    project_count: int = 0
    device_count: int = 0
    sensor_count: int = 0
    open_alert_count: int = 0
    online_device_count: int = 0
    offline_device_count: int = 0
    last_telemetry_at: datetime | None = None


class AssignOwnerRequest(BaseModel):
    user_id: int
