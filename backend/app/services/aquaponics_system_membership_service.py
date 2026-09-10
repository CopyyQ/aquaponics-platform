from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import ProjectStatus, UserStatus
from app.models.project import Project
from app.models.project_member import ProjectMember
from app.models.user import User
from app.services.project_role_service import (
    remove_project_role_assignments,
    sync_project_role_assignment,
)

MEMBER_ROLE_CODES = frozenset({"TECHNICIAN", "VIEWER"})


class MembershipError(Exception):
    def __init__(self, code: str, message: str, status_code: int) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code


async def _active_user(db: AsyncSession, user_id: int) -> User:
    user = await db.scalar(select(User).where(User.id == user_id, User.is_deleted.is_(False)))
    if user is None:
        raise MembershipError("USER_NOT_FOUND", "Không tìm thấy người dùng", 404)
    if user.status != UserStatus.ACTIVE:
        raise MembershipError("USER_NOT_ACTIVE", "Tài khoản phải đang hoạt động", 422)
    return user


async def _system(db: AsyncSession, system_id: int, *, active: bool = False) -> Project:
    query = select(Project).where(Project.id == system_id, Project.is_deleted.is_(False))
    if active:
        query = query.where(Project.status == ProjectStatus.ACTIVE)
    system = await db.scalar(query)
    if system is None:
        raise MembershipError("AQUAPONICS_SYSTEM_NOT_FOUND", "Không tìm thấy Hệ thống Aquaponics", 404)
    return system


def _validate_member_role(role: str) -> None:
    if role not in MEMBER_ROLE_CODES:
        raise MembershipError("INVALID_SYSTEM_MEMBER_ROLE", "Vai trò thành viên chỉ có thể là TECHNICIAN hoặc VIEWER", 422)


async def assign_system_member(
    db: AsyncSession, *, system_id: int, user_id: int, role: str, created_by: int
) -> ProjectMember:
    _validate_member_role(role)
    system = await _system(db, system_id, active=True)
    await _active_user(db, user_id)
    if system.owner_user_id == user_id or await db.scalar(select(ProjectMember.id).where(
        ProjectMember.project_id == system_id, ProjectMember.user_id == user_id
    )):
        raise MembershipError("AQUAPONICS_SYSTEM_MEMBERSHIP_EXISTS", "Người dùng đã thuộc Hệ thống Aquaponics", 409)
    row = ProjectMember(project_id=system_id, user_id=user_id, role=role, created_by=created_by)
    db.add(row)
    await sync_project_role_assignment(db, user_id=user_id, system_id=system_id, role_code=role, created_by=created_by)
    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise MembershipError("AQUAPONICS_SYSTEM_MEMBERSHIP_EXISTS", "Người dùng đã thuộc Hệ thống Aquaponics", 409) from exc
    return row


async def update_system_member_role(
    db: AsyncSession, *, system_id: int, user_id: int, role: str, created_by: int
) -> ProjectMember:
    _validate_member_role(role)
    await _system(db, system_id)
    row = await db.scalar(select(ProjectMember).where(
        ProjectMember.project_id == system_id, ProjectMember.user_id == user_id
    ))
    if row is None:
        raise MembershipError("AQUAPONICS_SYSTEM_MEMBERSHIP_NOT_FOUND", "Không tìm thấy thành viên", 404)
    row.role = role
    await sync_project_role_assignment(db, user_id=user_id, system_id=system_id, role_code=role, created_by=created_by)
    await db.commit()
    return row


async def remove_system_member(db: AsyncSession, *, system_id: int, user_id: int) -> None:
    system = await _system(db, system_id)
    if system.owner_user_id == user_id:
        raise MembershipError("CANNOT_REMOVE_SYSTEM_OWNER", "Không thể gỡ chủ sở hữu Hệ thống Aquaponics", 409)
    row = await db.scalar(select(ProjectMember).where(
        ProjectMember.project_id == system_id, ProjectMember.user_id == user_id
    ))
    if row is None:
        raise MembershipError("AQUAPONICS_SYSTEM_MEMBERSHIP_NOT_FOUND", "Không tìm thấy thành viên", 404)
    await remove_project_role_assignments(db, user_id=user_id, system_id=system_id)
    await db.delete(row)
    await db.commit()
