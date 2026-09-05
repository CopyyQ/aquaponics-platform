from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import UserRole, UserStatus
from app.models.project_member import ProjectMember
from app.models.user import User
from app.queries.project_member_queries import list_project_member_rows
from app.schemas.project import ProjectMemberListResponse, ProjectMemberRead
from app.services.access_service import require_project_access
from app.services.project_activity_service import dispatch_project_activity, record_project_activity


async def list_project_members(
    db: AsyncSession,
    *,
    project_id: int,
    actor: User,
    keyword: str,
    page: int,
    page_size: int,
) -> ProjectMemberListResponse:
    await require_project_access(db, project_id, actor)
    rows, total = await list_project_member_rows(
        db,
        project_id=project_id,
        keyword=keyword.strip(),
        page=page,
        page_size=page_size,
    )
    return ProjectMemberListResponse(
        items=[
            ProjectMemberRead(
                id=member.id,
                user_id=user.id,
                full_name=user.full_name,
                username=user.username,
                email=user.email,
                phone_number=user.phone_number,
                role=member.role,
                status=user.status.value,
                created_at=member.created_at,
                created_by=member.created_by,
                created_by_name=creator_name,
            )
            for member, user, creator_name in rows
        ],
        total=total,
        page=page,
        page_size=page_size,
    )


async def add_project_viewer(
    db: AsyncSession, *, project_id: int, user_id: int, actor: User
) -> ProjectMemberRead:
    project = await require_project_access(db, project_id, actor, manage=True)
    user = await db.scalar(
        select(User).where(
            User.id == user_id,
            User.system_role == UserRole.VIEWER,
            User.status == UserStatus.ACTIVE,
            User.is_deleted.is_(False),
        )
    )
    if user is None:
        raise HTTPException(status_code=400, detail="Chỉ được thêm Viewer đang hoạt động")
    if user.id == project.owner_user_id:
        raise HTTPException(status_code=400, detail="Owner không thể là Viewer của dự án")
    duplicate = await db.scalar(
        select(ProjectMember.id).where(
            ProjectMember.project_id == project_id, ProjectMember.user_id == user.id
        )
    )
    if duplicate:
        raise HTTPException(status_code=409, detail="Viewer đã là thành viên dự án")
    member = ProjectMember(project_id=project_id, user_id=user.id, created_by=actor.id)
    db.add(member)
    await db.flush()
    activity = await record_project_activity(db, project_id=project_id, actor=actor, action="MEMBER_ADDED", entity_type="MEMBER", entity_id=user.id, entity_name=user.full_name, changes={"role": {"before": None, "after": UserRole.VIEWER.value}})
    await db.commit()
    await db.refresh(member)
    await dispatch_project_activity(db, activity_id=activity.id)
    return ProjectMemberRead(
        id=member.id,
        user_id=user.id,
        full_name=user.full_name,
        username=user.username,
        email=user.email,
        phone_number=user.phone_number,
        role=member.role,
        status=user.status.value,
        created_at=member.created_at,
        created_by=actor.id,
        created_by_name=actor.full_name,
    )


async def remove_project_viewer(
    db: AsyncSession, *, project_id: int, user_id: int, actor: User
) -> None:
    await require_project_access(db, project_id, actor, manage=True)
    member = await db.scalar(
        select(ProjectMember).where(
            ProjectMember.project_id == project_id,
            ProjectMember.user_id == user_id,
            ProjectMember.role == UserRole.VIEWER.value,
        )
    )
    if member is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy thành viên dự án")
    member_user = await db.get(User, user_id)
    activity = await record_project_activity(db, project_id=project_id, actor=actor, action="MEMBER_REMOVED", entity_type="MEMBER", entity_id=user_id, entity_name=member_user.full_name if member_user else f"User #{user_id}", changes={"role": {"before": member.role, "after": None}})
    await db.delete(member)
    await db.commit()
    await dispatch_project_activity(db, activity_id=activity.id)
