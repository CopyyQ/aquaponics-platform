from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_roles
from app.db.session import get_db
from app.core.enums import UserRole
from app.models.audit import AuditLog
from app.models.user import User
from app.schemas.audit import AuditLogRead

router = APIRouter(prefix="/audit-logs", tags=["Audit logs"])


@router.get("", response_model=list[AuditLogRead])
async def list_audit_logs(
    action: str | None = None,
    entity_type: str | None = None,
    limit: int = Query(200, ge=1, le=1000),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_roles(UserRole.ADMIN)),
) -> list[dict]:
    query = select(AuditLog).order_by(AuditLog.created_at.desc()).limit(limit)
    if action:
        query = query.where(AuditLog.action == action)
    if entity_type:
        query = query.where(AuditLog.entity_type == entity_type)
    logs = list((await db.scalars(query)).all())
    actor_ids = {item.user_id for item in logs}
    actors = {item.id: item for item in (await db.scalars(select(User).where(User.id.in_(actor_ids)))).all()} if actor_ids else {}
    target_ids = {item.entity_id for item in logs if item.entity_type == "USER" and item.entity_id is not None}
    targets = {item.id: item for item in (await db.scalars(select(User).where(User.id.in_(target_ids)))).all()} if target_ids else {}
    result: list[dict] = []
    for item in logs:
        actor = actors.get(item.user_id)
        metadata = item.new_data or item.old_data or {}
        result.append({
            "id": item.id, "user_id": item.user_id, "action": item.action,
            "entity_type": item.entity_type, "entity_id": item.entity_id,
            "description": item.description, "old_data": item.old_data, "new_data": item.new_data,
            "created_at": item.created_at,
            "actor": {
                "id": item.user_id,
                "full_name": actor.full_name if actor else "Người dùng đã xóa",
                "username": actor.username if actor else "deleted-user",
            },
            "target": {
                "id": item.entity_id, "type": item.entity_type,
                "display_name": (
                    f"{targets[item.entity_id].full_name} (@{targets[item.entity_id].username})"
                    if item.entity_id in targets
                    else str(metadata.get("display_name") or item.description or f"#{item.entity_id}")
                ),
            },
        })
    return result
