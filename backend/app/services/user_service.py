from datetime import UTC, datetime

from fastapi import HTTPException
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import UserRole, UserStatus
from app.core.security import hash_password
from app.models.user import User
from app.schemas.user import AdminUserCreate, UserCreate, UserUpdate
from app.services.audit_service import write_audit


async def create_user(db: AsyncSession, payload: UserCreate, actor: User) -> User:
    if actor.system_role == UserRole.OWNER and payload.system_role != UserRole.VIEWER:
        raise HTTPException(status_code=403, detail="Owner chỉ được tạo Viewer")

    duplicate = await db.scalar(
        select(User.id).where(
            or_(
                User.username == payload.username,
                User.email == payload.email,
                User.phone_number == payload.phone_number,
            )
        )
    )
    if duplicate:
        raise HTTPException(status_code=409, detail="Username, email hoặc số điện thoại đã tồn tại")

    user = User(
        username=payload.username,
        password_hash=hash_password(payload.temporary_password),
        full_name=payload.full_name,
        email=str(payload.email),
        phone_number=payload.phone_number,
        address=payload.address,
        system_role=payload.system_role,
        status=UserStatus.ACTIVE,
        must_change_password=True,
        created_by=actor.id,
    )
    db.add(user)
    try:
        await db.flush()
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(status_code=409, detail="Tên đăng nhập, email hoặc số điện thoại đã tồn tại") from exc
    await write_audit(
        db,
        user_id=actor.id,
        action="CREATE_USER",
        entity_type="USER",
        entity_id=user.id,
        new_data={"username": user.username, "system_role": user.system_role.value},
    )
    await db.commit()
    await db.refresh(user)
    return user


async def create_admin_user(db: AsyncSession, payload: AdminUserCreate, actor: User) -> User:
    duplicate_fields = (
        ("Tên đăng nhập", func.lower(User.username) == payload.username.lower()),
        ("Email", func.lower(User.email) == str(payload.email).lower()),
        ("Số điện thoại", User.phone_number == payload.phone_number),
    )
    for label, condition in duplicate_fields:
        if await db.scalar(select(User.id).where(condition)):
            raise HTTPException(status_code=409, detail=f"{label} đã tồn tại")

    user = User(
        username=payload.username,
        password_hash=hash_password(payload.password),
        full_name=payload.full_name,
        email=str(payload.email).lower(),
        phone_number=payload.phone_number,
        address=payload.address,
        system_role=payload.system_role,
        status=payload.status,
        must_change_password=payload.must_change_password,
        password_changed_at=datetime.now(UTC),
        created_by=actor.id,
    )
    db.add(user)
    try:
        await db.flush()
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(status_code=409, detail="Tên đăng nhập, email hoặc số điện thoại đã tồn tại") from exc
    await write_audit(
        db,
        user_id=actor.id,
        action="CREATE_USER",
        entity_type="USER",
        entity_id=user.id,
        new_data={
            "target_user_id": user.id,
            "display_name": user.full_name,
            "system_role": user.system_role.value,
        },
    )
    await db.commit()
    await db.refresh(user)
    return user


async def update_user(db: AsyncSession, user: User, payload: UserUpdate, actor: User) -> User:
    if actor.system_role == UserRole.OWNER and user.system_role != UserRole.VIEWER:
        raise HTTPException(status_code=403, detail="Owner chỉ quản lý Viewer")
    old_data = {
        "full_name": user.full_name,
        "email": user.email,
        "phone_number": user.phone_number,
        "status": user.status.value,
    }
    changes = payload.model_dump(exclude_unset=True)
    if "status" in changes and changes["status"] != user.status:
        raise HTTPException(
            status_code=422,
            detail="Hãy sử dụng API vòng đời tài khoản để thay đổi trạng thái",
        )
    if changes.get("status") == user.status:
        changes.pop("status")
    role_changed = "system_role" in changes and changes["system_role"] != user.system_role
    if not role_changed:
        changes.pop("system_role", None)
    if actor.system_role == UserRole.OWNER and changes.get("system_role", UserRole.VIEWER) != UserRole.VIEWER:
        raise HTTPException(status_code=403, detail="Owner không được thay đổi vai trò Viewer")
    removes_active_admin = user.system_role == UserRole.ADMIN and user.status == UserStatus.ACTIVE and (
        changes.get("system_role", UserRole.ADMIN) != UserRole.ADMIN
        or changes.get("status", UserStatus.ACTIVE) != UserStatus.ACTIVE
    )
    if removes_active_admin:
        active_admins = int(await db.scalar(select(func.count(User.id)).where(
            User.system_role == UserRole.ADMIN, User.status == UserStatus.ACTIVE,
            User.is_deleted.is_(False), User.deleted_at.is_(None),
        )) or 0)
        if active_admins <= 1:
            raise HTTPException(status_code=409, detail="Không thể thay đổi Admin active cuối cùng")
    for key, value in changes.items():
        setattr(user, key, value)
    if "status" in changes or role_changed:
        user.token_version += 1
    await write_audit(
        db,
        user_id=actor.id,
        action="UPDATE_USER",
        entity_type="USER",
        entity_id=user.id,
        old_data=old_data,
        new_data=payload.model_dump(exclude_unset=True, mode="json"),
    )
    await db.commit()
    await db.refresh(user)
    return user


async def soft_delete_user(db: AsyncSession, user: User, actor: User) -> None:
    if actor.id == user.id:
        raise HTTPException(status_code=400, detail="Không thể xóa chính tài khoản đang đăng nhập")
    if actor.system_role == UserRole.OWNER and user.system_role != UserRole.VIEWER:
        raise HTTPException(status_code=403, detail="Owner chỉ quản lý Viewer")
    user.is_deleted = True
    user.deleted_at = datetime.now(UTC)
    user.status = UserStatus.SOFT_DELETED
    user.token_version += 1
    await write_audit(db, user_id=actor.id, action="DELETE_USER", entity_type="USER", entity_id=user.id)
    await db.commit()
async def get_user(db: AsyncSession, user_id: int) -> User:
    user = await db.scalar(select(User).where(User.id == user_id))
    if user is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy người dùng")
    return user


async def get_user_including_deleted(db: AsyncSession, user_id: int) -> User:
    user = await db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy người dùng")
    return user

