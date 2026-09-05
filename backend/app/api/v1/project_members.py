from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_operational_user
from app.db.session import get_session
from app.models.user import User
from app.schemas.project import ProjectMemberCreate, ProjectMemberListResponse, ProjectMemberRead
from app.services import project_member_service

router = APIRouter(prefix="/projects", tags=["Project members"])


@router.get("/{project_id}/members", response_model=ProjectMemberListResponse)
async def list_project_members(
    project_id: int,
    q: str = Query(default="", max_length=255),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_session),
    actor: User = Depends(get_current_operational_user),
) -> ProjectMemberListResponse:
    return await project_member_service.list_project_members(
        db,
        project_id=project_id,
        actor=actor,
        keyword=q,
        page=page,
        page_size=page_size,
    )


@router.post("/{project_id}/members", response_model=ProjectMemberRead, status_code=201)
async def add_project_member(
    project_id: int,
    payload: ProjectMemberCreate,
    db: AsyncSession = Depends(get_session),
    actor: User = Depends(get_current_operational_user),
) -> ProjectMemberRead:
    return await project_member_service.add_project_viewer(
        db, project_id=project_id, user_id=payload.user_id, actor=actor
    )


@router.delete("/{project_id}/members/{user_id}", status_code=204)
async def remove_project_member(
    project_id: int,
    user_id: int,
    db: AsyncSession = Depends(get_session),
    actor: User = Depends(get_current_operational_user),
) -> Response:
    await project_member_service.remove_project_viewer(
        db, project_id=project_id, user_id=user_id, actor=actor
    )
    return Response(status_code=204)
