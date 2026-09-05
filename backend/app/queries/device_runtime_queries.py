from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.device import Device
from app.models.project import Project
from app.models.user import User


async def get_device_runtime_context(
    db: AsyncSession, device_code: str
) -> tuple[Device, Project, User] | None:
    row = (
        await db.execute(
            select(Device, Project, User)
            .join(Project, Project.id == Device.project_id)
            .join(User, User.id == Project.owner_user_id)
            .where(
                Device.code == device_code,
                Device.is_deleted.is_(False),
                Device.deleted_at.is_(None),
            )
        )
    ).first()
    return tuple(row) if row is not None else None
