from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from app.models.project_member import ProjectMember
from app.models.user import User


async def list_project_member_rows(
    db: AsyncSession, *, project_id: int, keyword: str, page: int, page_size: int
):
    creator = aliased(User)
    query = (
        select(ProjectMember, User, creator.full_name)
        .join(User, User.id == ProjectMember.user_id)
        .outerjoin(creator, creator.id == ProjectMember.created_by)
        .where(ProjectMember.project_id == project_id, User.is_deleted.is_(False))
    )
    if keyword:
        pattern = f"%{keyword}%"
        query = query.where(
            or_(
                User.full_name.ilike(pattern),
                User.username.ilike(pattern),
                User.email.ilike(pattern),
                User.phone_number.ilike(pattern),
            )
        )
    total = int(await db.scalar(select(func.count()).select_from(query.subquery())) or 0)
    rows = (
        await db.execute(
            query.order_by(User.full_name).offset((page - 1) * page_size).limit(page_size)
        )
    ).all()
    return rows, total
