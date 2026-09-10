import secrets

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import ProjectStatus, UserStatus
from app.models.project import Project
from app.models.user import User
from app.services.audit_service import write_audit

CODE_GENERATION_ATTEMPTS = 8


class AquaponicsSystemCreationError(Exception):
    def __init__(self, code: str, message: str, status_code: int) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code


async def generate_aquaponics_system_code(db: AsyncSession) -> str:
    for _ in range(CODE_GENERATION_ATTEMPTS):
        code = f"AQS-{secrets.token_hex(6).upper()}"
        if await db.scalar(select(Project.id).where(Project.code == code)) is None:
            return code
    raise AquaponicsSystemCreationError(
        "AQUAPONICS_SYSTEM_CODE_GENERATION_FAILED",
        "Không thể tạo mã Hệ thống Aquaponics duy nhất",
        503,
    )


async def create_aquaponics_system(
    db: AsyncSession, *, name: str, owner_user_id: int, actor_id: int
) -> Project:
    owner = await db.scalar(select(User).where(User.id == owner_user_id, User.is_deleted.is_(False)))
    if owner is None:
        raise AquaponicsSystemCreationError("OWNER_NOT_FOUND", "Không tìm thấy chủ hệ thống", 404)
    if owner.status != UserStatus.ACTIVE:
        raise AquaponicsSystemCreationError("OWNER_NOT_ACTIVE", "Chủ hệ thống phải đang hoạt động", 422)

    item: Project | None = None
    for _ in range(CODE_GENERATION_ATTEMPTS):
        candidate = Project(
            owner_user_id=owner_user_id,
            code=await generate_aquaponics_system_code(db),
            name=name.strip(),
            status=ProjectStatus.ACTIVE,
        )
        try:
            async with db.begin_nested():
                db.add(candidate)
                await db.flush()
            item = candidate
            break
        except IntegrityError:
            continue
    if item is None:
        raise AquaponicsSystemCreationError(
            "AQUAPONICS_SYSTEM_CODE_GENERATION_FAILED",
            "Không thể tạo mã Hệ thống Aquaponics duy nhất",
            503,
        )
    await write_audit(
        db,
        user_id=actor_id,
        project_id=item.id,
        action="CREATE_AQUAPONICS_SYSTEM",
        entity_type="AQUAPONICS_SYSTEM",
        entity_id=item.id,
        new_data={"code": item.code, "name": item.name, "owner_user_id": owner_user_id},
    )
    await db.commit()
    await db.refresh(item)
    return item
