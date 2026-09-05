from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_admin
from app.db.session import get_session
from app.models.project import Project
from app.models.user import User
from app.schemas.project import ProjectDisableRequest, ProjectRead
from app.services import project_lifecycle_service

router = APIRouter(prefix="/projects", tags=["Project lifecycle"])


@router.post("/{project_id}/disable", response_model=ProjectRead)
async def disable_project(
    project_id: int,
    payload: ProjectDisableRequest,
    db: AsyncSession = Depends(get_session),
    actor: User = Depends(require_admin),
) -> Project:
    return await project_lifecycle_service.disable_project(
        db, project_id=project_id, reason=payload.reason, actor=actor
    )


@router.post("/{project_id}/activate", response_model=ProjectRead)
async def activate_project(
    project_id: int,
    db: AsyncSession = Depends(get_session),
    actor: User = Depends(require_admin),
) -> Project:
    return await project_lifecycle_service.activate_project(db, project_id=project_id, actor=actor)
