from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_operational_user, require_admin
from app.db.session import get_db
from app.models.user import User
from app.schemas.scada import ScadaLayout, ScadaLayoutMutationResponse, ScadaRuntimeResponse
from app.services.access_service import require_project_access
from app.services.scada_runtime_service import (
    ScadaDraftNotFoundError,
    ScadaLayoutValidationError,
    get_scada_runtime,
    publish_scada_draft,
    save_scada_draft,
)

router = APIRouter(prefix="/projects", tags=["Project SCADA"])


@router.get("/{project_id}/scada/runtime", response_model=ScadaRuntimeResponse)
async def project_scada_runtime(
    project_id: int,
    db: AsyncSession = Depends(get_db),
    actor: User = Depends(get_current_operational_user),
) -> ScadaRuntimeResponse:
    project = await require_project_access(db, project_id, actor)
    return await get_scada_runtime(db, project)


@router.put("/{project_id}/scada/layout/draft", response_model=ScadaLayoutMutationResponse)
async def save_project_scada_draft(
    project_id: int,
    payload: ScadaLayout,
    db: AsyncSession = Depends(get_db),
    actor: User = Depends(require_admin),
) -> ScadaLayoutMutationResponse:
    project = await require_project_access(db, project_id, actor, manage=True)
    try:
        return await save_scada_draft(db, project, actor, payload)
    except ScadaLayoutValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"code": "INVALID_SCADA_LAYOUT", "detail": str(exc)},
        ) from exc


@router.post("/{project_id}/scada/layout/publish", response_model=ScadaLayoutMutationResponse)
async def publish_project_scada_draft(
    project_id: int,
    db: AsyncSession = Depends(get_db),
    actor: User = Depends(require_admin),
) -> ScadaLayoutMutationResponse:
    project = await require_project_access(db, project_id, actor, manage=True)
    try:
        return await publish_scada_draft(db, project, actor)
    except ScadaDraftNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "SCADA_DRAFT_NOT_FOUND", "detail": str(exc)},
        ) from exc
    except ScadaLayoutValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"code": "INVALID_SCADA_LAYOUT", "detail": str(exc)},
        ) from exc
