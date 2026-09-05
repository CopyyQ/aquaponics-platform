from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_operational_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.project_activity import ProjectActivityActor, ProjectActivityEntity, ProjectActivityListResponse, ProjectActivityRead
from app.services.access_service import require_project_access
from app.services.project_activity_service import ACTION_LABELS, list_project_activities

router = APIRouter(prefix="/projects", tags=["Project activities"])


@router.get("/{project_id}/activities", response_model=ProjectActivityListResponse)
async def project_activities(
    project_id: int,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=100),
    action: str | None = None,
    entity_type: str | None = None,
    db: AsyncSession = Depends(get_db),
    actor: User = Depends(get_current_operational_user),
) -> ProjectActivityListResponse:
    await require_project_access(db, project_id, actor)
    items, total = await list_project_activities(db, project_id=project_id, page=page, page_size=page_size, action=action, entity_type=entity_type)
    actor_ids = {item.user_id for item in items}
    actors = {item.id: item for item in (await db.scalars(select(User).where(User.id.in_(actor_ids)))).all()} if actor_ids else {}
    return ProjectActivityListResponse(
        items=[
            ProjectActivityRead(
                id=item.id,
                action=item.action,
                actor=ProjectActivityActor(id=item.user_id, name=actors[item.user_id].full_name if item.user_id in actors else f"User #{item.user_id}"),
                entity=ProjectActivityEntity(type=item.entity_type, id=item.entity_id, name=str((item.new_data or {}).get("display_name") or f"#{item.entity_id}")),
                summary=item.description or ACTION_LABELS.get(item.action, item.action),
                created_at=item.created_at,
            )
            for item in items
        ],
        total=total,
        page=page,
        page_size=page_size,
    )
